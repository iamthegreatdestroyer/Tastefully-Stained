"""
Blockchain Integration Tests
============================

Comprehensive tests for Ethereum anchoring and IPFS storage.

Coverage targets:
- Ethereum connection and transactions
- IPFS storage and retrieval
- Error handling and retry logic

Run: pytest backend/tests/test_blockchain.py -v

IPFS test requirements (Phase 8):
----------------------------------
The ``TestIPFSHandler*`` classes below run real store/retrieve/verify
round trips against a live Kubo node -- no mocking of the RPC API. This
matches this repo's ``docker-compose.yml``, which defines an ``ipfs``
service (``ipfs/kubo``) with its RPC API on host port 17750. Start it
with ``docker compose up -d ipfs`` before running this file; tests in
``TestIPFSHandlerOperations`` are marked ``@pytest.mark.integration``
and will fail with a connection error if no Kubo node is reachable at
``IPFS_API_URL`` (default ``http://localhost:17750``).
"""

from __future__ import annotations

import hashlib
import os

import pytest

from watermark_engine.blockchain.ethereum_anchor import EthereumAnchor, AnchorResult
from watermark_engine.blockchain.ipfs_handler import IPFSHandler, IPFSStorageResult

# Real Kubo RPC API endpoint used for integration tests. Matches this
# repo's docker-compose.yml host port mapping (17750 -> container 5001).
IPFS_TEST_GATEWAY_URL = os.getenv("IPFS_API_URL", "http://localhost:17750")


class TestEthereumAnchorInit:
    """Test Ethereum anchor initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        anchor = EthereumAnchor(
            provider_url="https://sepolia.infura.io/v3/test"
        )

        assert anchor.network == "ethereum_sepolia"
        assert anchor.chain_id == 11155111

    def test_custom_network(self) -> None:
        """Test initialization with custom network."""
        anchor = EthereumAnchor(
            provider_url="https://polygon.infura.io/v3/test",
            network="polygon_mainnet"
        )

        assert anchor.network == "polygon_mainnet"
        assert anchor.chain_id == 137

    def test_invalid_network(self) -> None:
        """Test that invalid network raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported network"):
            EthereumAnchor(
                provider_url="test",
                network="invalid_network"
            )


class TestEthereumAnchorOperations:
    """Test Ethereum anchor operations."""

    @pytest.fixture
    def anchor(self) -> EthereumAnchor:
        """Create test anchor instance."""
        return EthereumAnchor(
            provider_url="https://sepolia.infura.io/v3/test"
        )

    @pytest.mark.asyncio
    async def test_anchor_not_implemented(self, anchor: EthereumAnchor) -> None:
        """Test that anchoring raises NotImplementedError until Phase 5."""
        with pytest.raises(NotImplementedError):
            await anchor.anchor_watermark("0x123", "content_id")

    @pytest.mark.asyncio
    async def test_verify_not_implemented(self, anchor: EthereumAnchor) -> None:
        """Test that verification raises NotImplementedError until Phase 5."""
        with pytest.raises(NotImplementedError):
            await anchor.verify_anchor("0x123")


class TestIPFSHandlerInit:
    """Test IPFS handler initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization."""
        handler = IPFSHandler(gateway_url="https://ipfs.infura.io:5001")

        assert handler.gateway_url == "https://ipfs.infura.io:5001"

    def test_trailing_slash_removed(self) -> None:
        """Test that trailing slash is removed from gateway URL."""
        handler = IPFSHandler(gateway_url="https://ipfs.infura.io:5001/")

        assert handler.gateway_url == "https://ipfs.infura.io:5001"

    def test_from_env_uses_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that from_env() falls back to the documented default."""
        monkeypatch.delenv("IPFS_API_URL", raising=False)
        handler = IPFSHandler.from_env()

        assert handler.gateway_url == "http://localhost:17750"

    def test_from_env_respects_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that from_env() picks up IPFS_API_URL when set."""
        monkeypatch.setenv("IPFS_API_URL", "http://ipfs:5001")
        handler = IPFSHandler.from_env()

        assert handler.gateway_url == "http://ipfs:5001"


@pytest.mark.integration
class TestIPFSHandlerOperations:
    """
    Test IPFS handler operations against a real, running Kubo node.

    These tests require ``docker compose up -d ipfs`` to have been run
    beforehand (see this repo's ``docker-compose.yml``). No part of the
    Kubo RPC API is mocked here -- content is genuinely stored on and
    retrieved from the local node, and CIDs are real, content-derived
    identifiers.
    """

    @pytest.fixture
    def handler(self) -> IPFSHandler:
        """Create a handler pointed at the local Kubo test node."""
        return IPFSHandler(gateway_url=IPFS_TEST_GATEWAY_URL)

    @pytest.fixture
    def short_timeout_handler(self) -> IPFSHandler:
        """
        Handler with a short RPC timeout, for the "CID was never stored"
        test below -- so that test doesn't have to wait out the full
        production timeout budget to observe clean failure.
        """
        return IPFSHandler(gateway_url=IPFS_TEST_GATEWAY_URL, timeout_seconds=3.0)

    @pytest.mark.asyncio
    async def test_store_watermarked_image_round_trip(self, handler: IPFSHandler) -> None:
        """Store real bytes, get a real CID, retrieve it, confirm byte-identical."""
        payload = b"tastefully-stained real watermark payload for round-trip test"

        result = await handler.store_watermarked_image(payload, filename="watermarked.png")

        assert isinstance(result, IPFSStorageResult)
        assert result.success is True
        assert result.error is None
        assert result.cid is not None and result.cid.startswith("Qm")
        assert result.size_bytes == len(payload)
        assert result.pinned is True
        assert result.gateway_url is not None and result.cid in result.gateway_url

        retrieved = await handler.retrieve_content(result.cid)

        assert retrieved == payload

    @pytest.mark.asyncio
    async def test_store_c2pa_manifest_round_trip(self, handler: IPFSHandler) -> None:
        """Store a C2PA manifest dict, retrieve it back as identical JSON."""
        import json

        manifest = {
            "claim_generator": "tastefully-stained/test",
            "title": "Integration Test Manifest",
            "assertions": [{"label": "c2pa.watermark", "hash": "sha256:" + "b" * 64}],
        }

        result = await handler.store_c2pa_manifest(manifest)

        assert result.success is True
        assert result.cid is not None

        retrieved = await handler.retrieve_content(result.cid)
        assert json.loads(retrieved) == manifest

    @pytest.mark.asyncio
    async def test_verify_content_matches(self, handler: IPFSHandler) -> None:
        """verify_content returns True when the hash genuinely matches."""
        payload = b"content whose hash we will verify correctly"
        result = await handler.store_watermarked_image(payload)
        expected_hash = "sha256:" + hashlib.sha256(payload).hexdigest()

        assert await handler.verify_content(result.cid, expected_hash) is True

    @pytest.mark.asyncio
    async def test_verify_content_detects_mismatch(self, handler: IPFSHandler) -> None:
        """
        verify_content must genuinely detect a mismatch -- store one
        thing, verify against a different expected hash, confirm it
        reports failure rather than trivially returning True.
        """
        payload = b"the actual stored content"
        result = await handler.store_watermarked_image(payload)

        wrong_hash = "sha256:" + hashlib.sha256(b"a completely different payload").hexdigest()

        assert await handler.verify_content(result.cid, wrong_hash) is False

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_cid_fails_cleanly(
        self, short_timeout_handler: IPFSHandler
    ) -> None:
        """
        Retrieving a syntactically valid CID that was never stored must
        raise FileNotFoundError within a bounded time, not hang. A raw
        Kubo `cat` against such a CID blocks indefinitely searching the
        DHT unless a timeout is applied client- or server-side.
        """
        never_stored_cid = "QmZzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

        with pytest.raises(FileNotFoundError):
            await short_timeout_handler.retrieve_content(never_stored_cid)

    @pytest.mark.asyncio
    async def test_verify_content_nonexistent_cid_returns_false(
        self, short_timeout_handler: IPFSHandler
    ) -> None:
        """verify_content on an unretrievable CID reports failure, not an exception."""
        never_stored_cid = "QmZzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"

        result = await short_timeout_handler.verify_content(
            never_stored_cid, "sha256:" + "0" * 64
        )

        assert result is False

    def test_get_public_url(self, handler: IPFSHandler) -> None:
        """Test public URL generation."""
        cid = "QmTest123"
        url = handler.get_public_url(cid)

        assert cid in url
        assert url.startswith("https://")
