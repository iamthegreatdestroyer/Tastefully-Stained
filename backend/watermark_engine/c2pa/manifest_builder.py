"""
C2PA Manifest Builder Module
============================

Create C2PA-compliant content credentials manifests.

This module implements the C2PA Version 2.0 specification for
creating signed manifests that establish content provenance.

Implementation note (Phase 6):
-------------------------------
This module is a thin domain wrapper around the official ``c2pa-python``
binding (https://github.com/contentauth/c2pa-python), which itself wraps
the Rust reference implementation (``c2pa-rs``). We do NOT hand-roll CBOR
serialization, JUMBF box construction, or COSE/X.509 signing here -- that
work is delegated entirely to the native library. This module's job is to
translate between this codebase's existing public dataclasses
(``C2PAManifest``, ``Assertion`` subtypes) and the ``c2pa-python``
``Builder``/``Signer`` API.

``c2pa-python``'s ``Builder.sign()`` performs manifest creation, signing,
and JUMBF embedding as a single atomic operation (there is no supported
public API to obtain an unsigned, not-yet-embedded manifest object from
the native SDK). To preserve this module's existing three-step public
contract (``create_manifest`` -> ``sign_manifest`` -> ``embed_manifest``),
``create_manifest`` stages a manifest definition (assertions, ingredients,
title, etc.) on a ``C2PAManifest`` instance without calling into the
native library; the actual native ``Builder``/``Signer``/sign() call
happens in ``embed_manifest``, which is the method that has both the
staged manifest AND the content bytes it must be bound to (C2PA manifests
are hash-bound to the exact asset bytes they are embedded in, so signing
must happen at embed time, not before). ``sign_manifest`` marks the
manifest as ready-to-embed and validates that signing credentials are
configured; it does not produce a standalone signed-but-unembedded
manifest because the underlying SDK has no such artifact.

Development-only signing certificate:
--------------------------------------
By default (no explicit paths passed to ``ManifestBuilder.__init__`` and
no ``C2PA_SIGNING_KEY_PATH`` / ``C2PA_CERTIFICATE_PATH`` env vars set),
this module reads a locally-generated, self-signed development
certificate chain from ``backend/certs/dev/``. That chain (see
``backend/certs/dev/README`` and the generation command in this repo's
tooling) is a throwaway dev CA + leaf certificate created purely so this
code can produce *real, structurally valid, cryptographically verifiable*
C2PA manifests during development and testing.

THIS DEV CERTIFICATE IS NOT TRUSTED BY ANY REAL C2PA VERIFIER. Manifests
signed with it will show "signingCredential.untrusted" (or fail entirely)
when checked against public verifiers such as Adobe's Content Credentials
Verify (https://contentcredentials.org/verify), because our dev CA is not
in any real trust list. Obtaining a production-grade, C2PA-recognized
signing certificate is a separate business/legal enrollment process
(see https://c2pa.org/specifications/specifications/2.2/index.html and
the C2PA Conformance Program) and is explicitly out of scope for this
engineering phase. Do not use this certificate in production, and do not
commit the generated private key -- ``backend/certs/`` is gitignored via
the repo's existing ``*.pem`` / ``*.key`` patterns.

C2PA Manifest Structure:
------------------------
- claim_generator: Identifies the creating software
- title: Content title
- format: MIME type
- instance_id: Unique identifier
- assertions: Array of provenance assertions
- signature_info: Digital signature data

Example:
--------
    >>> from watermark_engine.c2pa import ManifestBuilder
    >>>
    >>> builder = ManifestBuilder(
    ...     certificate_path="./certs/dev/fullchain.pem",
    ...     private_key_path="./certs/dev/leaf.key"
    ... )
    >>>
    >>> manifest = builder.create_manifest(
    ...     content_bytes=image_bytes,
    ...     title="Watermarked Image",
    ...     assertions=[
    ...         CreatorAssertion(name="Artist Name"),
    ...         WatermarkAssertion(
    ...             watermark_hash="sha256:...",
    ...             strategy="hybrid",
    ...             strength=0.5,
    ...         ),
    ...     ]
    ... )
    >>> manifest = builder.sign_manifest(manifest)
    >>> signed_bytes = builder.embed_manifest(image_bytes, manifest)

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import c2pa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default dev-certificate locations
# ---------------------------------------------------------------------------
# These are only used when neither an explicit constructor argument nor the
# C2PA_SIGNING_KEY_PATH / C2PA_CERTIFICATE_PATH environment variables (see
# .env.example) are set. They point at the throwaway dev chain generated by
# this repo's dev-cert tooling -- see backend/certs/dev/README.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DEV_CERT_DIR = _REPO_ROOT / "backend" / "certs" / "dev"
_DEFAULT_CERTIFICATE_PATH = _DEFAULT_DEV_CERT_DIR / "fullchain.pem"
_DEFAULT_PRIVATE_KEY_PATH = _DEFAULT_DEV_CERT_DIR / "leaf.key"


class AssertionType(str, Enum):
    """C2PA assertion types."""

    CREATOR = "c2pa.creator"
    ACTIONS = "c2pa.actions"
    INGREDIENT = "c2pa.ingredient"
    WATERMARK = "tastefully-stained.watermark"
    METADATA = "stds.exif"
    CUSTOM = "custom"


@dataclass
class Assertion:
    """
    Base class for C2PA assertions.

    Assertions are claims about the content's creation or modification.
    """

    label: str
    assertion_type: AssertionType
    data: dict[str, Any]
    is_redactable: bool = False


@dataclass
class CreatorAssertion(Assertion):
    """Creator identity assertion."""

    def __init__(self, name: str, identifier: str | None = None):
        super().__init__(
            label="c2pa.creator",
            assertion_type=AssertionType.CREATOR,
            data={
                "@type": "Person",
                "name": name,
                "identifier": identifier or ""
            }
        )


@dataclass
class WatermarkAssertion(Assertion):
    """Watermark embedding assertion."""

    def __init__(
        self,
        watermark_hash: str,
        strategy: str,
        strength: float
    ):
        super().__init__(
            label="tastefully-stained.watermark",
            assertion_type=AssertionType.WATERMARK,
            data={
                "watermark_hash": watermark_hash,
                "strategy": strategy,
                "strength": strength,
                "algorithm_version": "1.0.0"
            }
        )


@dataclass
class ActionsAssertion(Assertion):
    """
    Actions assertion (``c2pa.actions``).

    The C2PA spec requires every manifest to carry an actions assertion
    whose *first* listed action is ``c2pa.created`` (new content) or
    ``c2pa.opened`` (edit of pre-existing content) -- the native SDK
    rejects manifests that omit this with
    ``assertion.action.malformed: first action must be created or
    opened``. ``ManifestBuilder.create_manifest`` auto-injects a default
    ``ActionsAssertion(action="c2pa.created")`` when the caller doesn't
    supply one, so most callers never need to construct this directly;
    it's exposed for callers that want to record a specific action (e.g.
    ``c2pa.watermarked``) or a full custom actions list.
    """

    def __init__(
        self,
        action: str = "c2pa.created",
        digital_source_type: str = (
            "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation"
        ),
        software_agent: str | None = None,
        when: str | None = None,
    ):
        action_entry: dict[str, Any] = {"action": action}
        if action == "c2pa.created":
            action_entry["digitalSourceType"] = digital_source_type
        if software_agent:
            action_entry["softwareAgent"] = software_agent
        if when:
            action_entry["when"] = when

        super().__init__(
            label="c2pa.actions",
            assertion_type=AssertionType.ACTIONS,
            data={"actions": [action_entry]},
        )


@dataclass
class C2PAManifest:
    """
    C2PA manifest data structure.

    Represents a complete C2PA manifest ready for embedding.

    Note on ``signature`` / ``is_signed``: the underlying ``c2pa-python``
    SDK signs and embeds a manifest as a single atomic operation, so there
    is no native concept of a "signed but not yet embedded" manifest
    object. ``signature`` here holds the raw C2PA manifest store bytes
    returned by the native ``Builder.sign()`` call once ``embed_manifest``
    has actually run; ``is_signed`` is set by ``sign_manifest`` to record
    that this manifest has valid signing credentials attached and is
    ready to be embedded (the real cryptographic signing happens inside
    ``embed_manifest``, where the content bytes it must be hash-bound to
    are available).
    """

    claim_generator: str = "Tastefully-Stained/0.1.0"
    title: str = ""
    format: str = "image/png"
    instance_id: str = field(default_factory=lambda: f"xmp.iid:{uuid.uuid4()}")
    assertions: list[Assertion] = field(default_factory=list)
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: bytes | None = None
    is_signed: bool = False

    # Internal: populated by ManifestBuilder.sign_manifest() so that
    # embed_manifest() knows which certificate/key/algorithm to sign with
    # without requiring callers to pass them again. Not part of the public
    # C2PA manifest shape -- excluded from to_dict().
    _signing_alg: str | None = field(default=None, repr=False, compare=False)
    _certificate_pem: str | None = field(default=None, repr=False, compare=False)
    _private_key_pem: str | None = field(default=None, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary representation."""
        return {
            "claim_generator": self.claim_generator,
            "title": self.title,
            "format": self.format,
            "instance_id": self.instance_id,
            "assertions": [
                {
                    "label": a.label,
                    "data": a.data,
                    "is_redactable": a.is_redactable
                }
                for a in self.assertions
            ],
            "ingredients": self.ingredients,
            "signature_info": {
                "alg": self._signing_alg or "ES256",
                "issuer": "Tastefully Stained",
                "time": self.created.isoformat()
            }
        }


def _detect_signing_alg(private_key_pem: bytes) -> tuple[c2pa.C2paSigningAlg, str]:
    """
    Inspect a PEM private key and determine the matching C2PA signing
    algorithm.

    Returns:
        Tuple of (C2paSigningAlg enum value, human-readable alg name).

    Raises:
        ValueError: If the key type/curve is not one C2PA supports.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )

    if isinstance(private_key, ec.EllipticCurvePrivateKey):
        curve_name = private_key.curve.name
        if curve_name == "secp256r1":
            return c2pa.C2paSigningAlg.ES256, "ES256"
        if curve_name == "secp384r1":
            return c2pa.C2paSigningAlg.ES384, "ES384"
        if curve_name == "secp521r1":
            return c2pa.C2paSigningAlg.ES512, "ES512"
        raise ValueError(
            f"Unsupported EC curve for C2PA signing: {curve_name}"
        )
    if isinstance(private_key, rsa.RSAPrivateKey):
        # Default to PS256 (RSASSA-PSS + SHA-256), the RSA scheme C2PA's
        # cert profile expects; larger keys still use PS256 (the hash
        # width, not the key size, drives the alg choice).
        return c2pa.C2paSigningAlg.PS256, "PS256"
    if isinstance(private_key, ed25519.Ed25519PrivateKey):
        return c2pa.C2paSigningAlg.ED25519, "Ed25519"

    raise ValueError(
        f"Unsupported private key type for C2PA signing: {type(private_key)}"
    )


def _make_callback_signer(
    private_key_pem: bytes,
    alg: c2pa.C2paSigningAlg,
):
    """
    Build a raw-bytes-in/raw-bytes-out signing callback for the given PEM
    private key and algorithm.

    We use ``c2pa.Signer.from_callback`` (the SDK's recommended signer
    construction path -- see ``c2pa-python``'s ``examples/sign.py``, which
    documents ``Signer.from_info()`` as the legacy alternative) rather than
    ``Signer.from_info()``. On this deployment's SDK build (c2pa-python
    0.36.0 / c2pa-rs 0.89.0), ``Signer.from_info()`` reliably fails during
    ``Builder.sign()`` with an opaque ``C2paError.Signature: "empty
    string"`` for every certificate/key/image combination we tested,
    including the SDK's own official test fixtures -- i.e. this reproduces
    with known-good inputs, so it is a rough edge in that code path on
    this build rather than anything specific to our dev certificate. The
    callback-based signer path does not hit this and round-trips cleanly,
    so it is what this module uses.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem, password=None, backend=default_backend()
    )

    if alg in (
        c2pa.C2paSigningAlg.ES256,
        c2pa.C2paSigningAlg.ES384,
        c2pa.C2paSigningAlg.ES512,
    ):
        hash_alg = {
            c2pa.C2paSigningAlg.ES256: hashes.SHA256(),
            c2pa.C2paSigningAlg.ES384: hashes.SHA384(),
            c2pa.C2paSigningAlg.ES512: hashes.SHA512(),
        }[alg]

        def _sign(data: bytes) -> bytes:
            return private_key.sign(data, ec.ECDSA(hash_alg))

        return _sign

    if alg in (
        c2pa.C2paSigningAlg.PS256,
        c2pa.C2paSigningAlg.PS384,
        c2pa.C2paSigningAlg.PS512,
    ):
        hash_alg = {
            c2pa.C2paSigningAlg.PS256: hashes.SHA256(),
            c2pa.C2paSigningAlg.PS384: hashes.SHA384(),
            c2pa.C2paSigningAlg.PS512: hashes.SHA512(),
        }[alg]

        def _sign(data: bytes) -> bytes:
            return private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hash_alg),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hash_alg,
            )

        return _sign

    if alg == c2pa.C2paSigningAlg.ED25519:
        def _sign(data: bytes) -> bytes:
            return private_key.sign(data)

        return _sign

    raise ValueError(f"Unsupported signing algorithm: {alg}")


class ManifestBuilder:
    """
    Builder for C2PA-compliant content credentials manifests.

    Creates, signs, and embeds C2PA manifests in image content
    following the C2PA Version 2.0 specification, using the official
    ``c2pa-python`` binding to the C2PA Rust reference implementation
    for all CBOR/JUMBF/COSE signing work.

    Attributes:
        certificate_path: Path to X.509 signing certificate (chain)
        private_key_path: Path to private key for signing

    Example:
        >>> builder = ManifestBuilder("cert.pem", "key.pem")
        >>> manifest = builder.create_manifest(image_bytes, "My Image")
        >>> manifest = builder.sign_manifest(manifest)
        >>> signed_bytes = builder.embed_manifest(image_bytes, manifest)
    """

    # Supported formats for C2PA embedding
    SUPPORTED_FORMATS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/heic": ".heic",
        "video/mp4": ".mp4",
    }

    def __init__(
        self,
        certificate_path: str | None = None,
        private_key_path: str | None = None,
        claim_generator: str = "Tastefully-Stained/0.1.0"
    ) -> None:
        """
        Initialize Manifest Builder.

        Args:
            certificate_path: Path to X.509 signing certificate chain
                (PEM, leaf cert first then any intermediate/CA certs).
                Falls back to the ``C2PA_CERTIFICATE_PATH`` env var, then
                to the bundled dev-certificate default.
            private_key_path: Path to private key (PEM format). Falls
                back to the ``C2PA_SIGNING_KEY_PATH`` env var, then to
                the bundled dev-certificate default.
            claim_generator: Claim generator identifier string
        """
        self.certificate_path = (
            certificate_path
            or os.environ.get("C2PA_CERTIFICATE_PATH")
            or str(_DEFAULT_CERTIFICATE_PATH)
        )
        self.private_key_path = (
            private_key_path
            or os.environ.get("C2PA_SIGNING_KEY_PATH")
            or str(_DEFAULT_PRIVATE_KEY_PATH)
        )
        self.claim_generator = (
            claim_generator
            or os.environ.get("C2PA_CLAIM_GENERATOR")
            or "Tastefully-Stained/0.1.0"
        )

        logger.info(
            "ManifestBuilder initialized (certificate_path=%s, "
            "private_key_path=%s)",
            self.certificate_path,
            self.private_key_path,
        )

    def create_manifest(
        self,
        content_bytes: bytes,
        title: str,
        mime_type: str = "image/png",
        assertions: list[Assertion] | None = None,
        ingredients: list[dict[str, Any]] | None = None
    ) -> C2PAManifest:
        """
        Create a C2PA manifest for content.

        This stages the manifest definition (title, format, assertions,
        ingredients). The manifest is not yet signed or embedded -- call
        ``sign_manifest`` then ``embed_manifest`` to produce signed,
        embedded output bytes.

        Args:
            content_bytes: Raw content bytes (used to compute a content
                hash recorded via ``compute_content_hash``; the actual
                C2PA hard-binding hash is computed by the native SDK at
                embed time against the exact bytes passed to
                ``embed_manifest``)
            title: Content title
            mime_type: Content MIME type
            assertions: List of assertions to include
            ingredients: Ingredient manifests (for derived content)

        Returns:
            C2PAManifest ready for signing and embedding

        Raises:
            ValueError: If mime_type is not supported

        Example:
            >>> manifest = builder.create_manifest(
            ...     content_bytes=image_bytes,
            ...     title="Watermarked Photo",
            ...     mime_type="image/jpeg"
            ... )
        """
        if mime_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {mime_type}")

        logger.info("Creating manifest for: %s", title)

        resolved_assertions = list(assertions or [])

        # The C2PA spec requires the first action in a c2pa.actions
        # assertion to be c2pa.created or c2pa.opened -- the native SDK
        # rejects manifests missing this entirely
        # ("assertion.action.malformed: first action must be created or
        # opened"). Auto-inject a default c2pa.created actions assertion
        # if the caller didn't supply any c2pa.actions assertion, so
        # every manifest this builder produces is spec-conformant without
        # every call site needing to remember this requirement.
        has_actions_assertion = any(
            a.label == "c2pa.actions" for a in resolved_assertions
        )
        if not has_actions_assertion:
            resolved_assertions.insert(
                0, ActionsAssertion(action="c2pa.created", software_agent=self.claim_generator)
            )

        manifest = C2PAManifest(
            claim_generator=self.claim_generator,
            title=title,
            format=mime_type,
            assertions=resolved_assertions,
            ingredients=list(ingredients or []),
        )

        logger.debug(
            "Manifest staged: title=%s format=%s content_hash=%s",
            title,
            mime_type,
            self.compute_content_hash(content_bytes),
        )

        return manifest

    def sign_manifest(self, manifest: C2PAManifest) -> C2PAManifest:
        """
        Attach signing credentials to a manifest and mark it ready to
        embed.

        Args:
            manifest: Unsigned C2PA manifest

        Returns:
            The same C2PAManifest instance, updated in place, with
            signing credentials attached (``is_signed=True``).

        Raises:
            ValueError: If certificate/key are not configured or cannot
                be read/parsed.

        Note:
            The C2PA SDK signs and JUMBF-embeds a manifest as a single
            atomic operation bound to specific asset bytes, so there is
            no native "signed but unembedded" manifest artifact. This
            method validates that the configured certificate and private
            key exist and are readable/parseable, determines the correct
            signing algorithm from the key type, and stashes that
            information on the manifest so ``embed_manifest`` can perform
            the real native sign+embed call without re-deriving it. The
            actual cryptographic signature is produced inside
            ``embed_manifest``.
        """
        logger.info("Signing C2PA manifest: %s", manifest.title)

        cert_path = Path(self.certificate_path)
        key_path = Path(self.private_key_path)

        if not cert_path.exists():
            raise ValueError(
                f"Certificate not configured: file not found at "
                f"{cert_path}. Set certificate_path / "
                f"C2PA_CERTIFICATE_PATH, or generate the dev "
                f"certificate chain (see backend/certs/dev/README)."
            )
        if not key_path.exists():
            raise ValueError(
                f"Private key not configured: file not found at "
                f"{key_path}. Set private_key_path / "
                f"C2PA_SIGNING_KEY_PATH, or generate the dev "
                f"certificate chain (see backend/certs/dev/README)."
            )

        certificate_pem = cert_path.read_text(encoding="utf-8")
        private_key_pem = key_path.read_bytes()

        try:
            _, alg_name = _detect_signing_alg(private_key_pem)
        except ValueError as exc:
            raise ValueError(f"Cannot sign manifest: {exc}") from exc

        manifest._certificate_pem = certificate_pem
        manifest._private_key_pem = private_key_pem.decode("utf-8")
        manifest._signing_alg = alg_name
        manifest.is_signed = True

        logger.debug("Manifest signing credentials attached (alg=%s)", alg_name)

        return manifest

    def embed_manifest(
        self,
        content_bytes: bytes,
        manifest: C2PAManifest
    ) -> bytes:
        """
        Sign and embed a manifest into content using the C2PA SDK's
        native JUMBF encoder.

        Args:
            content_bytes: Original content bytes
            manifest: Signed C2PA manifest (``sign_manifest`` must have
                been called first)

        Returns:
            Content bytes with embedded, signed C2PA manifest.

        Raises:
            ValueError: If the manifest has not been signed, or if the
                native C2PA SDK fails to build/sign/embed the manifest.
        """
        if not manifest.is_signed:
            raise ValueError(
                "Manifest must be signed via sign_manifest() before it "
                "can be embedded."
            )

        logger.info("Embedding C2PA manifest in content (%d bytes)", len(content_bytes))

        manifest_definition = self._to_builder_json(manifest)

        alg_enum = {
            "ES256": c2pa.C2paSigningAlg.ES256,
            "ES384": c2pa.C2paSigningAlg.ES384,
            "ES512": c2pa.C2paSigningAlg.ES512,
            "PS256": c2pa.C2paSigningAlg.PS256,
            "PS384": c2pa.C2paSigningAlg.PS384,
            "PS512": c2pa.C2paSigningAlg.PS512,
            "Ed25519": c2pa.C2paSigningAlg.ED25519,
        }[manifest._signing_alg]

        sign_callback = _make_callback_signer(
            manifest._private_key_pem.encode("utf-8"), alg_enum
        )

        try:
            with c2pa.Signer.from_callback(
                sign_callback,
                alg_enum,
                manifest._certificate_pem,
                None,
            ) as signer, c2pa.Builder(manifest_definition) as builder:
                import io

                src = io.BytesIO(content_bytes)
                dest = io.BytesIO()
                builder.sign(signer, manifest.format, src, dest)
                signed_bytes = dest.getvalue()
        except c2pa.C2paError as exc:
            raise ValueError(f"C2PA embedding failed: {exc}") from exc

        manifest.signature = signed_bytes

        logger.debug(
            "Manifest embedded: output size=%d bytes (input was %d bytes)",
            len(signed_bytes),
            len(content_bytes),
        )

        return signed_bytes

    def _to_builder_json(self, manifest: C2PAManifest) -> str:
        """Translate our C2PAManifest dataclass into the JSON manifest
        definition shape the native ``c2pa.Builder`` expects."""
        definition: dict[str, Any] = {
            "claim_generator_info": [
                {"name": manifest.claim_generator.split("/")[0], "version": manifest.claim_generator.split("/")[-1]}
            ],
            "title": manifest.title,
            "format": manifest.format,
            "instance_id": manifest.instance_id,
            "ingredients": manifest.ingredients,
            "assertions": [
                {"label": a.label, "data": a.data}
                for a in manifest.assertions
            ],
        }
        return json.dumps(definition)

    @staticmethod
    def compute_content_hash(content_bytes: bytes) -> str:
        """
        Compute SHA-256 hash of content.

        Args:
            content_bytes: Raw content bytes

        Returns:
            SHA-256 hash as hex string with 'sha256:' prefix
        """
        hash_value = hashlib.sha256(content_bytes).hexdigest()
        return f"sha256:{hash_value}"
