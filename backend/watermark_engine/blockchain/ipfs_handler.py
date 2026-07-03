"""
IPFS Handler Module
==================

IPFS (InterPlanetary File System) storage for watermarked content
and C2PA manifests.

This module provides:
- Content-addressed storage for watermarked images
- C2PA manifest storage and retrieval
- Pinning service integration for persistence
- Gateway configuration for content access

Features:
---------
- Multiple IPFS gateway support
- Automatic pinning to ensure persistence
- Content verification using CIDs
- Async operations for performance

Implementation note (Phase 8):
-------------------------------
This module talks directly to a self-hosted Kubo (``ipfs/kubo``) node's
HTTP RPC API using ``httpx`` -- see this repo's ``docker-compose.yml``,
which already defines an ``ipfs`` service (Kubo) with its RPC API bound
to host port 17750 (container port 5001) and the public gateway on
17751 (container port 8080).

We deliberately do NOT use the ``ipfshttpclient`` package that appears
in ``requirements.txt``. That library is unmaintained (last meaningful
release predates Kubo's current RPC surface) and has multiple reported
incompatibilities with current Kubo API versions. Kubo's RPC API is a
plain HTTP API (multipart POST for input, query-string args for
everything else), so there is no real benefit to a wrapper library here
-- ``httpx`` (already a pinned dependency used elsewhere in this
codebase) is sufficient on its own. ``ipfshttpclient`` is not imported
anywhere in this codebase; see ``requirements.txt`` / ``pyproject.toml``
for the corresponding removal.

Endpoints used (all are Kubo RPC ``/api/v0/*`` calls, all POST per the
Kubo HTTP RPC spec -- Kubo's RPC API does not follow REST GET/POST
conventions, every call is a POST regardless of whether it mutates
state):

- ``POST /api/v0/add``      -- multipart file upload; returns
  ``{"Name", "Hash", "Size"}`` where ``Hash`` is the resulting CID.
- ``POST /api/v0/pin/add``  -- ``?arg=<cid>``; pins content so it
  survives garbage collection. Returns ``{"Pins": [<cid>, ...]}``.
- ``POST /api/v0/cat``      -- ``?arg=<cid>``; streams the raw bytes
  for that CID. Returns HTTP 500 with a JSON error body
  (``{"Message", "Code", "Type"}``) if the path is malformed, and
  otherwise blocks until the DHT either finds the content or the
  request's ``timeout=`` budget is exceeded -- a syntactically valid
  CID that was never pinned/provided by any reachable peer will hang
  indefinitely without a timeout. This module always sets Kubo's own
  ``timeout=`` query parameter *and* an httpx client-side timeout, so a
  CID that cannot be resolved fails within a bounded window rather than
  hanging, and is surfaced as ``FileNotFoundError`` either way.

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default budget (seconds) for a single Kubo RPC round trip. Applied both
# as Kubo's own server-side `timeout=` query parameter (so Kubo aborts its
# DHT search cleanly and returns a JSON error) and as the httpx client-side
# timeout (so a network-level hang -- e.g. the daemon wedged -- is also
# bounded). Retrieval of unresolvable content is a *routine* outcome (a
# bad/foreign CID, not a bug), so this stays modest rather than matching
# typical DHT provider-record TTLs.
DEFAULT_RPC_TIMEOUT_SECONDS = 15.0


@dataclass
class IPFSStorageResult:
    """Result of IPFS storage operation."""

    success: bool
    cid: str | None
    size_bytes: int
    gateway_url: str | None
    pinned: bool
    error: str | None = None


class IPFSHandler:
    """
    IPFS storage handler for content and manifest storage.

    This class manages storing and retrieving watermarked content
    and C2PA manifests on IPFS.

    Attributes:
        gateway_url: IPFS gateway URL
        api_key: API key for authenticated access

    Example:
        >>> handler = IPFSHandler("https://ipfs.infura.io:5001")
        >>> result = await handler.store_content(image_bytes)
    """

    # Popular IPFS gateways
    PUBLIC_GATEWAYS = [
        "https://ipfs.io/ipfs/",
        "https://gateway.pinata.cloud/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/",
        "https://dweb.link/ipfs/",
    ]

    def __init__(
        self,
        gateway_url: str,
        api_key: str | None = None,
        api_secret: str | None = None,
        *,
        timeout_seconds: float = DEFAULT_RPC_TIMEOUT_SECONDS,
    ) -> None:
        """
        Initialize IPFS Handler.

        Args:
            gateway_url: IPFS RPC API base URL (e.g.
                ``http://localhost:17750`` for this repo's self-hosted
                Kubo node, reachable via ``IPFS_API_URL`` inside the
                docker-compose network as ``http://ipfs:5001``). Despite
                the parameter name (kept for backward compatibility with
                this class's existing public signature), this is the
                RPC *API* endpoint that ``/api/v0/*`` calls are made
                against -- not the read-only content gateway. Use
                ``get_public_url()`` for read-only gateway links.
            api_key: Optional API key for authenticated services (kept
                for compatibility with hosted-gateway deployments; the
                self-hosted Kubo node used by default in this repo does
                not require one).
            api_secret: Optional API secret for authenticated services
                (same caveat as ``api_key``).
            timeout_seconds: Per-request timeout budget, applied both to
                Kubo's own ``timeout=`` query parameter and as the
                httpx client timeout, so RPC calls against CIDs that
                cannot be resolved fail predictably instead of hanging.
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout_seconds = timeout_seconds

        logger.info(f"IPFSHandler initialized with gateway: {gateway_url}")

    @classmethod
    def from_env(cls) -> "IPFSHandler":
        """
        Construct an ``IPFSHandler`` from this repo's standard
        environment variables.

        Reads ``IPFS_API_URL`` (matching the variable name already set
        for the ``backend``/``worker`` services in ``docker-compose.yml``,
        e.g. ``http://ipfs:5001`` inside the compose network), falling
        back to ``http://localhost:17750`` (this repo's documented host
        port mapping for the Kubo RPC API) when unset -- suitable for
        running the backend outside of Docker against the same
        docker-compose-managed Kubo node.

        Returns:
            A configured ``IPFSHandler`` instance.
        """
        api_url = os.getenv("IPFS_API_URL", "http://localhost:17750")
        return cls(gateway_url=api_url)

    def _auth_headers(self) -> dict[str, str]:
        """Build auth headers for hosted gateways that require them.

        The self-hosted Kubo RPC API used by default in this repo does
        not require authentication; this only has an effect against
        third-party hosted gateways/pinning services that accept an API
        key/secret pair.
        """
        if self.api_key and self.api_secret:
            return {"Authorization": f"Basic {self.api_key}:{self.api_secret}"}
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key}"}
        return {}

    async def _rpc_add(
        self, content: bytes, filename: str, pin: bool
    ) -> IPFSStorageResult:
        """Shared implementation for storing raw bytes on IPFS.

        POSTs ``content`` to Kubo's ``/api/v0/add``, optionally pins the
        result via ``/api/v0/pin/add``, and returns an
        ``IPFSStorageResult`` describing the outcome. Used by both
        ``store_watermarked_image`` and ``store_c2pa_manifest`` since
        Kubo has no notion of "content type" -- both are just bytes to
        the ``add`` endpoint.
        """
        add_url = f"{self.gateway_url}/api/v0/add"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    add_url,
                    files={"file": (filename, content)},
                    headers=self._auth_headers(),
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except httpx.HTTPError as exc:
            logger.error(f"IPFS add failed for {filename}: {exc}")
            return IPFSStorageResult(
                success=False,
                cid=None,
                size_bytes=len(content),
                gateway_url=None,
                pinned=False,
                error=str(exc),
            )

        cid = payload["Hash"]
        pinned = False

        if pin:
            pinned = await self._pin(cid)

        logger.info(
            f"Stored {filename} on IPFS: cid={cid} size={len(content)} pinned={pinned}"
        )

        return IPFSStorageResult(
            success=True,
            cid=cid,
            size_bytes=len(content),
            gateway_url=self.get_public_url(cid),
            pinned=pinned,
            error=None,
        )

    async def _pin(self, cid: str) -> bool:
        """Pin ``cid`` via ``/api/v0/pin/add``.

        Returns ``True`` on success, ``False`` on failure (pinning
        failure does not invalidate the stored content -- it just means
        it may be garbage-collected sooner -- so callers treat this as
        a soft signal rather than raising).
        """
        pin_url = f"{self.gateway_url}/api/v0/pin/add"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    pin_url,
                    params={"arg": cid},
                    headers=self._auth_headers(),
                )
                response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning(f"IPFS pin failed for cid={cid}: {exc}")
            return False

    async def store_watermarked_image(
        self,
        image_bytes: bytes,
        filename: str | None = None,
        pin: bool = True,
    ) -> IPFSStorageResult:
        """
        Store watermarked image on IPFS.

        Args:
            image_bytes: Raw image bytes
            filename: Optional filename for metadata
            pin: Whether to pin the content for persistence

        Returns:
            IPFSStorageResult with CID and metadata

        Example:
            >>> result = await ipfs.store_watermarked_image(
            ...     image_bytes=b"...",
            ...     filename="watermarked.png",
            ...     pin=True
            ... )
            >>> print(f"CID: {result.cid}")
        """
        logger.info(f"Storing image: {len(image_bytes)} bytes")
        return await self._rpc_add(
            image_bytes, filename or "watermarked_image", pin
        )

    async def store_c2pa_manifest(
        self,
        manifest: dict[str, Any],
        pin: bool = True,
    ) -> IPFSStorageResult:
        """
        Store C2PA manifest on IPFS.

        Args:
            manifest: C2PA manifest dictionary
            pin: Whether to pin the content

        Returns:
            IPFSStorageResult with CID

        Example:
            >>> result = await ipfs.store_c2pa_manifest(manifest)
        """
        logger.info("Storing C2PA manifest on IPFS")
        import json

        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        return await self._rpc_add(manifest_bytes, "c2pa_manifest.json", pin)

    async def retrieve_content(self, cid: str) -> bytes:
        """
        Retrieve content from IPFS by CID.

        Args:
            cid: Content Identifier (CID) of the content

        Returns:
            Raw content bytes

        Raises:
            FileNotFoundError: If CID not found (includes both Kubo
                reporting the path as invalid/unresolvable and the
                request budget being exceeded while searching the DHT
                for a syntactically valid but unreachable/never-stored
                CID).
        """
        logger.info(f"Retrieving content: {cid}")
        cat_url = f"{self.gateway_url}/api/v0/cat"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    cat_url,
                    params={
                        "arg": cid,
                        # Server-side budget: makes Kubo itself abort the
                        # DHT search and answer with a clean JSON error
                        # instead of holding the connection open.
                        "timeout": f"{int(self.timeout_seconds)}s",
                    },
                )
        except httpx.TimeoutException as exc:
            # Client-side backstop in case the server-side timeout=
            # param above didn't apply (e.g. connection-level hang).
            logger.warning(f"IPFS retrieval timed out for cid={cid}: {exc}")
            raise FileNotFoundError(
                f"Content not found for CID {cid} (timed out after "
                f"{self.timeout_seconds}s)"
            ) from exc

        if response.status_code != 200:
            logger.warning(
                f"IPFS retrieval failed for cid={cid}: "
                f"status={response.status_code} body={response.text[:200]}"
            )
            raise FileNotFoundError(f"Content not found for CID {cid}")

        return response.content

    async def verify_content(self, cid: str, expected_hash: str) -> bool:
        """
        Verify content integrity against expected hash.

        Args:
            cid: Content Identifier
            expected_hash: Expected SHA-256 hash, either as a bare hex
                digest or in this codebase's ``"sha256:<hexdigest>"``
                convention (see
                ``watermark_engine.c2pa.manifest_builder``'s hashing
                helper). Both forms are accepted; comparison is
                case-insensitive.

        Returns:
            True if the content stored at ``cid`` hashes to
            ``expected_hash``. Returns False (rather than raising) if
            the CID cannot be retrieved at all, since "content we can't
            even fetch" is a verification failure, not an error in the
            verification process itself.
        """
        logger.info(f"Verifying content: {cid}")

        try:
            content = await self.retrieve_content(cid)
        except FileNotFoundError:
            logger.warning(f"Verification failed: cid={cid} not retrievable")
            return False

        actual_hash = hashlib.sha256(content).hexdigest()
        normalized_expected = expected_hash.removeprefix("sha256:").lower()

        matches = actual_hash.lower() == normalized_expected
        if not matches:
            logger.warning(
                f"Verification mismatch for cid={cid}: "
                f"expected={normalized_expected} actual={actual_hash}"
            )

        return matches

    def get_public_url(self, cid: str, gateway_index: int = 0) -> str:
        """
        Get public URL for content.

        Args:
            cid: Content Identifier
            gateway_index: Index of public gateway to use

        Returns:
            Public URL for accessing content
        """
        gateway = self.PUBLIC_GATEWAYS[gateway_index % len(self.PUBLIC_GATEWAYS)]
        return f"{gateway}{cid}"
