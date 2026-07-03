"""
Blockchain Integration Tests
============================

Comprehensive tests for Ethereum anchoring and IPFS storage.

Coverage targets:
- Ethereum connection and transactions
- IPFS storage and retrieval
- Error handling and retry logic

Run: pytest backend/tests/test_blockchain.py -v

Ethereum test requirements (Phase 7):
--------------------------------------
``TestEthereumAnchorLiveChain`` runs real anchor/verify/history/gas-estimate
round trips against a live **local** Hardhat node: the ``blockchain``
service in ``docker-compose.yml``, with ``WatermarkRegistry`` deployed to
it via ``blockchain/scripts/deploy.js``. Real EVM, real signed
transactions, real gas -- just not a public network, so no faucet/funding
is needed. Start it with:

    docker compose --profile blockchain up -d blockchain
    cd blockchain && npm install && npx hardhat compile && \
        npx hardhat run scripts/deploy.js --network dockerHost

If the node isn't reachable (checked live) or the contract hasn't been
deployed (checked via ``blockchain/deployments/dockerHost.json``, written
by the deploy script above), ``TestEthereumAnchorLiveChain`` skips with a
message explaining exactly what to run, rather than failing the suite --
matching the ``requires_live_kubo`` / dev-cert skip patterns used
elsewhere in this test suite.

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
import json
import os
import uuid
from pathlib import Path

import pytest

from watermark_engine.blockchain.ethereum_anchor import AnchorResult, EthereumAnchor
from watermark_engine.blockchain.ipfs_handler import IPFSHandler, IPFSStorageResult

# Real Kubo RPC API endpoint used for integration tests. Matches this
# repo's docker-compose.yml host port mapping (17750 -> container 5001).
IPFS_TEST_GATEWAY_URL = os.getenv("IPFS_API_URL", "http://localhost:17750")

# ---------------------------------------------------------------------------
# Live local Hardhat chain fixture data (Phase 7)
# ---------------------------------------------------------------------------
#
# Deployment record written by `npx hardhat run scripts/deploy.js --network
# dockerHost` (see blockchain/scripts/deploy.js). Gitignored -- a local
# node's deployed address only exists for the life of that node process, so
# it's read dynamically here rather than hardcoded, and re-running the
# deploy script (e.g. after restarting the node) is all that's needed to
# regenerate it.
_DEPLOYMENT_RECORD_PATH = (
    Path(__file__).parent.parent.parent / "blockchain" / "deployments" / "dockerHost.json"
)

# Host-published port for the `blockchain` docker-compose service
# ("17740:8545" in docker-compose.yml).
_HARDHAT_RPC_URL = "http://127.0.0.1:17740"

# Hardhat's account #0. This is one of twenty deterministic, publicly
# documented dev accounts that a `hardhat node` process pre-funds with
# 10000 test ETH -- printed to stdout by the node itself, identical on
# every machine that runs `npx hardhat node`. It is not a secret: using it
# to sign transactions here is exactly what it's for (local dev/test
# signing), and it must never be used for anything beyond a local/ephemeral
# chain.
_HARDHAT_DEV_PRIVATE_KEY = (
    "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
)


def _read_deployment_record() -> dict | None:
    if not _DEPLOYMENT_RECORD_PATH.exists():
        return None
    with _DEPLOYMENT_RECORD_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _hardhat_node_reachable() -> bool:
    """Live connectivity probe -- is a JSON-RPC endpoint actually up?"""
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(
            _HARDHAT_RPC_URL,
            data=json.dumps(
                {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


_deployment_record = _read_deployment_record()
_node_reachable = _hardhat_node_reachable()
_live_chain_available = _deployment_record is not None and _node_reachable

if _deployment_record is None:
    _skip_reason = (
        "No WatermarkRegistry deployment record found at "
        f"{_DEPLOYMENT_RECORD_PATH}. From the repo root, run: "
        "docker compose --profile blockchain up -d blockchain && "
        "cd blockchain && npm install && npx hardhat compile && "
        "npx hardhat run scripts/deploy.js --network dockerHost"
    )
elif not _node_reachable:
    _skip_reason = (
        f"Hardhat node not reachable at {_HARDHAT_RPC_URL}. From the repo "
        "root, run: docker compose --profile blockchain up -d blockchain"
    )
else:
    _skip_reason = ""

requires_live_chain = pytest.mark.skipif(
    not _live_chain_available, reason=_skip_reason
)


def _unique_content_id(label: str) -> str:
    """
    A content_id that has never been anchored before, on this run or any
    prior one.

    The local Hardhat node is a long-lived process whose chain state is
    NOT reset between separate `pytest` invocations (unlike, say, a fresh
    in-memory `hardhat` network per test session) -- so a fixed literal
    content_id like "test-foo" would accumulate anchors across repeated
    test runs and break assertions that count exact history length. Every
    live-chain test that anchors data must use a fresh id each time it
    actually runs.
    """
    return f"pytest-{label}-{uuid.uuid4().hex}"


def _unique_watermark_hash() -> str:
    """A watermark_hash value guaranteed not to collide with a prior run."""
    return "0x" + uuid.uuid4().hex + uuid.uuid4().hex


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

    def test_hardhat_local_network(self) -> None:
        """Test that the local-dev chain id is registered."""
        anchor = EthereumAnchor(
            provider_url=_HARDHAT_RPC_URL,
            network="hardhat_local",
        )
        assert anchor.chain_id == 31337


class TestEthereumAnchorValidation:
    """Test input validation that doesn't require network access."""

    @pytest.fixture
    def anchor(self) -> EthereumAnchor:
        return EthereumAnchor(provider_url="https://sepolia.infura.io/v3/test")

    @pytest.mark.asyncio
    async def test_anchor_watermark_requires_signing_key(
        self, anchor: EthereumAnchor
    ) -> None:
        """anchor_watermark needs a private_key configured to sign with."""
        with pytest.raises(ValueError, match="private_key is required"):
            await anchor.anchor_watermark("0x" + "a" * 64, "content_id")

    @pytest.mark.asyncio
    async def test_anchor_watermark_rejects_empty_hash(
        self, anchor: EthereumAnchor
    ) -> None:
        with pytest.raises(ValueError, match="watermark_hash"):
            await anchor.anchor_watermark("", "content_id")

    @pytest.mark.asyncio
    async def test_anchor_watermark_rejects_empty_content_id(
        self, anchor: EthereumAnchor
    ) -> None:
        with pytest.raises(ValueError, match="content_id"):
            await anchor.anchor_watermark("0x" + "a" * 64, "")

    @pytest.mark.asyncio
    async def test_verify_anchor_without_content_id_returns_false(
        self, anchor: EthereumAnchor
    ) -> None:
        """
        The registry looks anchors up by content hash; without a
        content_id there's nothing to verify against, so this reports
        False rather than raising or guessing.
        """
        result = await anchor.verify_anchor("0x" + "a" * 64, content_id=None)
        assert result is False


@requires_live_chain
class TestEthereumAnchorLiveChain:
    """
    Real anchor/verify/history/gas-estimate round-trips against the local
    Hardhat node with WatermarkRegistry deployed. See module docstring for
    the setup commands this class needs to have been run already.
    """

    @pytest.fixture(scope="class")
    def contract_address(self) -> str:
        record = _read_deployment_record()
        assert record is not None  # guaranteed by requires_live_chain gate
        return record["address"]

    @pytest.fixture
    def anchor(self, contract_address: str) -> EthereumAnchor:
        """A funded EthereumAnchor pointed at the live local chain."""
        return EthereumAnchor(
            provider_url=_HARDHAT_RPC_URL,
            private_key=_HARDHAT_DEV_PRIVATE_KEY,
            contract_address=contract_address,
            network="hardhat_local",
        )

    @pytest.fixture
    def read_only_anchor(self, contract_address: str) -> EthereumAnchor:
        """
        An EthereumAnchor with no private_key, for exercising the
        read-only verify_anchor / get_anchor_history paths independent of
        signing.
        """
        return EthereumAnchor(
            provider_url=_HARDHAT_RPC_URL,
            contract_address=contract_address,
            network="hardhat_local",
        )

    @pytest.mark.asyncio
    async def test_chain_id_mismatch_is_detected(
        self, contract_address: str
    ) -> None:
        """
        Configuring the wrong `network=` for a given provider_url (e.g.
        labeling a local Hardhat node as "ethereum_sepolia") must raise a
        clear error at first connection, not silently sign transactions
        with a mismatched chainId.
        """
        misconfigured = EthereumAnchor(
            provider_url=_HARDHAT_RPC_URL,
            contract_address=contract_address,
            network="ethereum_sepolia",  # wrong on purpose -- real chain is 31337
        )
        with pytest.raises(ValueError, match="Chain id mismatch"):
            await misconfigured.verify_anchor("0x" + "a" * 64, "irrelevant")

    @pytest.mark.asyncio
    async def test_anchor_watermark_real_transaction(
        self, anchor: EthereumAnchor
    ) -> None:
        """A real signed, mined transaction against the local chain."""
        result = await anchor.anchor_watermark(
            watermark_hash=_unique_watermark_hash(),
            content_id=_unique_content_id("anchor-real-tx"),
            metadata={"creator": "pytest@tastefullystained.test"},
        )

        assert isinstance(result, AnchorResult)
        assert result.success is True
        assert result.error is None
        assert result.tx_hash is not None and result.tx_hash.startswith("0x")
        assert result.block_number is not None and result.block_number > 0
        assert result.gas_used is not None and result.gas_used > 0
        assert result.timestamp is not None and result.timestamp > 0
        assert result.anchor_id is not None and result.anchor_id.startswith("0x")
        assert result.network == "hardhat_local"

    @pytest.mark.asyncio
    async def test_verify_anchor_true_for_matching_anchor(
        self, anchor: EthereumAnchor, read_only_anchor: EthereumAnchor
    ) -> None:
        """Anchor a watermark, then verify it comes back True."""
        watermark_hash = _unique_watermark_hash()
        content_id = _unique_content_id("verify-true")

        anchor_result = await anchor.anchor_watermark(watermark_hash, content_id)
        assert anchor_result.success is True

        is_valid = await read_only_anchor.verify_anchor(watermark_hash, content_id)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_anchor_false_for_never_anchored_content(
        self, read_only_anchor: EthereumAnchor
    ) -> None:
        """
        Verifying a hash/content_id combination that was never anchored
        must report False -- not raise, not a false positive. Uses a
        fresh uuid each run so there's no possibility this content_id was
        anchored by a previous test run against this same persistent
        local node.
        """
        is_valid = await read_only_anchor.verify_anchor(
            _unique_watermark_hash(), _unique_content_id("never-anchored")
        )
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_anchor_false_for_wrong_hash(
        self, anchor: EthereumAnchor, read_only_anchor: EthereumAnchor
    ) -> None:
        """Right content_id, wrong watermark_hash must not verify."""
        content_id = _unique_content_id("verify-wrong-hash")
        await anchor.anchor_watermark(_unique_watermark_hash(), content_id)

        is_valid = await read_only_anchor.verify_anchor(
            _unique_watermark_hash(), content_id
        )
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_get_anchor_history_empty_for_unknown_content(
        self, read_only_anchor: EthereumAnchor
    ) -> None:
        """History for content that was never anchored is an empty list,
        not an error."""
        history = await read_only_anchor.get_anchor_history(
            _unique_content_id("no-history")
        )
        assert history == []

    @pytest.mark.asyncio
    async def test_get_anchor_history_returns_all_anchors(
        self, anchor: EthereumAnchor, read_only_anchor: EthereumAnchor
    ) -> None:
        """
        WatermarkRegistry's on-chain mapping only exposes the *latest*
        anchor per content hash, but get_anchor_history must recover full
        history (every anchor ever created) from the event log.
        """
        content_id = _unique_content_id("history-multiple")
        watermark_hash_1 = _unique_watermark_hash()
        watermark_hash_2 = _unique_watermark_hash()

        result_1 = await anchor.anchor_watermark(watermark_hash_1, content_id)
        result_2 = await anchor.anchor_watermark(watermark_hash_2, content_id)
        assert result_1.success and result_2.success
        assert result_1.anchor_id != result_2.anchor_id

        history = await read_only_anchor.get_anchor_history(content_id)

        assert len(history) == 2
        # oldest-first ordering
        assert history[0]["block_number"] <= history[1]["block_number"]
        watermark_hashes = {entry["watermark_hash"] for entry in history}
        assert watermark_hash_1.lower() in watermark_hashes
        assert watermark_hash_2.lower() in watermark_hashes
        for entry in history:
            assert entry["tx_hash"].startswith("0x")
            assert entry["creator"].startswith("0x")
            assert entry["timestamp"] > 0

    @pytest.mark.asyncio
    async def test_estimate_gas_returns_sane_value(
        self, anchor: EthereumAnchor
    ) -> None:
        """
        estimate_gas must return a real, positive gas estimate from a live
        eth_estimateGas simulation -- sane bounds for a contract call this
        simple are roughly 21000 (bare tx floor) to a few hundred thousand.
        """
        estimate = await anchor.estimate_gas()

        assert isinstance(estimate, int)
        assert 21_000 < estimate < 500_000

    @pytest.mark.asyncio
    async def test_estimate_gas_is_a_dry_run_not_a_real_transaction(
        self, anchor: EthereumAnchor
    ) -> None:
        """
        Calling estimate_gas repeatedly with identical probe arguments
        must not mutate chain state (it's a simulation) -- so it must not
        raise "anchor exists" and must return the same estimate each time.
        """
        first = await anchor.estimate_gas()
        second = await anchor.estimate_gas()
        assert first == second

    @pytest.mark.asyncio
    async def test_estimate_gas_scales_with_metadata_size(
        self, anchor: EthereumAnchor
    ) -> None:
        """Larger on-chain metadata should cost at least as much gas."""
        small = await anchor.estimate_gas(metadata={"a": "1"})
        large = await anchor.estimate_gas(
            metadata={"description": "x" * 2000, "creator": "y" * 500}
        )
        assert large >= small


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
