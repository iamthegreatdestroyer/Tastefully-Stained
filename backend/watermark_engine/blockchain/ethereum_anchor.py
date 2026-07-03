"""
Ethereum Blockchain Anchoring Module
====================================

Real Ethereum smart contract interaction for watermark registration and
verification on-chain, backed by web3.py against the deployed
``WatermarkRegistry`` contract (see ``contracts/WatermarkRegistry.sol``).

This module provides:
- Connection to any EVM JSON-RPC endpoint (local Hardhat node, Infura,
  Alchemy, etc.) via ``AsyncWeb3``
- Real transaction signing (via ``eth_account``) and broadcasting
- Gas estimation against live contract calldata
- On-chain event log queries for full anchor history

Features:
---------
- Web3.py (async) integration for Ethereum interaction
- Local transaction signing -- the private key never leaves this process
  and is never logged
- Deterministic keccak256 hashing of caller-supplied strings into the
  bytes32 values the contract expects
- Multi-network support via ``NETWORKS`` (network name only changes
  ``chain_id`` bookkeeping/validation -- ``provider_url`` decides which
  actual chain you talk to)

Example:
--------
    >>> from watermark_engine.blockchain import EthereumAnchor
    >>>
    >>> anchor = EthereumAnchor(
    ...     provider_url="http://127.0.0.1:8545",
    ...     private_key="0x...",
    ...     contract_address="0x...",
    ...     network="ethereum_sepolia",  # bookkeeping only; see NOTE below
    ... )
    >>>
    >>> result = await anchor.anchor_watermark(
    ...     watermark_hash="0x123...",
    ...     content_id="content_001",
    ...     metadata={"creator": "user@example.com"}
    ... )

NOTE on networks vs. provider_url:
-----------------------------------
``network`` is bookkeeping metadata (which ``chain_id`` we *expect* to be
talking to; it is checked against the RPC's actual reported chain id at
connect time as a footgun-guard). The RPC endpoint you actually reach --
local Hardhat node, Sepolia, mainnet -- is entirely determined by
``provider_url``. Pointing an already-configured ``EthereumAnchor`` at a
different network is therefore a **constructor-argument / config change**
(new ``provider_url`` + funded ``private_key`` + that network's deployed
``contract_address``), never a code change.

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eth_account import Account
from web3 import AsyncWeb3
from web3.exceptions import ContractLogicError, TimeExhausted

logger = logging.getLogger(__name__)

# Path to the compiled contract ABI, checked in at
# backend/watermark_engine/blockchain/abi/WatermarkRegistry.json. Loaded
# once at import time and reused for every EthereumAnchor instance.
_ABI_PATH = Path(__file__).parent / "abi" / "WatermarkRegistry.json"

# Default gas headroom applied on top of `eth_estimateGas` results before
# submitting a transaction, to absorb small on-chain state changes between
# estimation and inclusion (standard practice -- avoids "out of gas"
# reverts from estimation drift without wildly overpaying).
_GAS_ESTIMATE_BUFFER_PCT = 20

# How long to wait for a submitted transaction to be mined before giving up.
_RECEIPT_TIMEOUT_SECONDS = 120


def _load_abi() -> list[dict[str, Any]]:
    """Load the WatermarkRegistry ABI from the checked-in JSON file."""
    if not _ABI_PATH.exists():
        raise FileNotFoundError(
            f"WatermarkRegistry ABI not found at {_ABI_PATH}. "
            "Compile the contract (cd blockchain && npx hardhat compile) "
            "and copy artifacts/contracts/WatermarkRegistry.sol/"
            "WatermarkRegistry.json's 'abi' field here, or run "
            "scripts/export_abi.py."
        )
    with _ABI_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    # Support both a bare ABI list and a full Hardhat artifact dict.
    if isinstance(data, dict) and "abi" in data:
        return data["abi"]
    return data


def _to_bytes32(value: str) -> bytes:
    """
    Convert a caller-supplied string into a deterministic bytes32 value
    suitable for the contract's ``bytes32`` parameters.

    Two forms are accepted:
    - A ``0x``-prefixed 64-hex-character string is decoded directly as the
      raw bytes32 value (i.e. the caller already computed a 32-byte hash
      and wants it used verbatim).
    - Any other string (a bare content id like ``"content_001"``, a
      prefixed hash like ``"sha256:aaaa..."``, etc.) is hashed with
      keccak256 to deterministically fold it into 32 bytes. The same input
      string always produces the same bytes32, which is what makes
      anchor/verify round-trips work.
    """
    if value.startswith("0x") and len(value) == 66:
        try:
            return bytes.fromhex(value[2:])
        except ValueError:
            pass  # fall through to keccak256 hashing below
    return AsyncWeb3.keccak(text=value)


def _bytes32_to_hex(value: bytes) -> str:
    """Render a bytes32 value as a ``0x``-prefixed hex string."""
    return "0x" + bytes(value).hex()


@dataclass
class AnchorResult:
    """Result of blockchain anchoring operation."""

    success: bool
    tx_hash: str | None
    block_number: int | None
    gas_used: int | None
    network: str
    timestamp: int | None
    error: str | None = None
    anchor_id: str | None = None


@dataclass
class AnchorEvent:
    """A single on-chain anchor event, as recovered from event logs."""

    anchor_id: str
    watermark_hash: str
    content_hash: str
    creator: str
    timestamp: int
    tx_hash: str
    block_number: int


class EthereumAnchor:
    """
    Ethereum blockchain anchoring for watermark registration.

    This class manages interaction with the deployed ``WatermarkRegistry``
    smart contract for immutable watermark registration and verification.
    It works against any EVM JSON-RPC endpoint -- a local Hardhat node for
    dev/CI, or a public network such as Sepolia once a funded key and the
    network's deployed contract address are supplied.

    Attributes:
        provider_url: Ethereum node provider URL (local Hardhat node,
            Infura, Alchemy, etc.)
        contract_address: Deployed WatermarkRegistry contract address

    Example:
        >>> anchor = EthereumAnchor(
        ...     "http://127.0.0.1:8545",
        ...     private_key="0x...",
        ...     contract_address="0x...",
        ... )
        >>> result = await anchor.anchor_watermark(hash_value, "content_001")
    """

    # Supported networks
    NETWORKS = {
        "ethereum_mainnet": 1,
        "ethereum_goerli": 5,
        "ethereum_sepolia": 11155111,
        "polygon_mainnet": 137,
        "polygon_mumbai": 80001,
        "arbitrum_one": 42161,
        # Local Hardhat / Ganache-style dev chains default to this chain id.
        "hardhat_local": 31337,
    }

    def __init__(
        self,
        provider_url: str,
        private_key: str | None = None,
        contract_address: str | None = None,
        network: str = "ethereum_sepolia",
    ) -> None:
        """
        Initialize Ethereum Anchor.

        Args:
            provider_url: Ethereum node provider URL (Infura, Alchemy,
                local Hardhat node, etc.)
            private_key: Private key for transaction signing. Required for
                anchor_watermark/estimate_gas (state-changing/simulated
                calls); not required for read-only verify_anchor /
                get_anchor_history.
            contract_address: Deployed WatermarkRegistry contract address
            network: Network name from NETWORKS (bookkeeping only -- see
                module docstring "NOTE on networks vs. provider_url")

        Raises:
            ValueError: If network is not supported
        """
        if network not in self.NETWORKS:
            raise ValueError(
                f"Unsupported network: {network}. "
                f"Supported: {list(self.NETWORKS.keys())}"
            )

        self.provider_url = provider_url
        self.private_key = private_key
        self.contract_address = contract_address
        self.network = network
        self.chain_id = self.NETWORKS[network]

        # Web3 connection and contract binding are created lazily on first
        # use (most callers construct this object well before any network
        # I/O is desired, e.g. at app startup / DI wiring time).
        self._web3: AsyncWeb3 | None = None
        self._contract: Any = None
        self._account = Account.from_key(private_key) if private_key else None
        self._abi: list[dict[str, Any]] | None = None

        logger.info(f"EthereumAnchor initialized for network: {network}")

    # ------------------------------------------------------------------
    # Connection / contract binding
    # ------------------------------------------------------------------

    async def _get_web3(self) -> AsyncWeb3:
        """
        Lazily create (and cache) the AsyncWeb3 connection.

        On first successful connection, cross-checks the configured
        ``network``'s expected chain id against what the RPC endpoint
        itself reports (``eth_chainId``) -- this is the "footgun-guard"
        described in the module docstring: catching a
        provider_url/network mismatch immediately with a clear error,
        rather than only discovering it later as an opaque "invalid
        chain id" rejection when a signed transaction is broadcast.
        """
        first_connection = self._web3 is None
        if self._web3 is None:
            self._web3 = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(self.provider_url))

        if not await self._web3.is_connected():
            raise ConnectionError(
                f"Unable to connect to Ethereum node at {self.provider_url}"
            )

        if first_connection:
            actual_chain_id = await self._web3.eth.chain_id
            if actual_chain_id != self.chain_id:
                raise ValueError(
                    f"Chain id mismatch: configured network '{self.network}' "
                    f"expects chain id {self.chain_id}, but the node at "
                    f"{self.provider_url} reports chain id {actual_chain_id}. "
                    "Pass the matching `network=` for that provider_url "
                    "(e.g. network='hardhat_local' for a local Hardhat "
                    "node), or point provider_url at the network you "
                    "actually intend to use."
                )

        return self._web3

    async def _get_contract(self) -> Any:
        """Lazily bind (and cache) the WatermarkRegistry contract instance."""
        if self._contract is None:
            if not self.contract_address:
                raise ValueError(
                    "contract_address is required to interact with "
                    "WatermarkRegistry (set it in the constructor)"
                )
            web3 = await self._get_web3()
            if self._abi is None:
                self._abi = _load_abi()
            checksum_address = web3.to_checksum_address(self.contract_address)
            self._contract = web3.eth.contract(
                address=checksum_address, abi=self._abi
            )
        return self._contract

    async def _require_signing_account(self) -> Any:
        """Return the signing Account, raising a clear error if absent."""
        if self._account is None:
            raise ValueError(
                "private_key is required for this operation (state-changing "
                "transactions must be signed locally)"
            )
        return self._account

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def anchor_watermark(
        self,
        watermark_hash: str,
        content_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> AnchorResult:
        """
        Anchor watermark hash to blockchain.

        Args:
            watermark_hash: SHA-256 hash (or any stable identifier string)
                of the watermark data
            content_id: Unique identifier for the content
            metadata: Additional metadata; serialized to JSON and stored
                on-chain as the anchor's ``metadataUri`` field. (A real
                production deployment would typically store this on IPFS
                and pass the resulting ``ipfs://<cid>`` URI instead of
                inline JSON -- see ``IPFSHandler``, wired in a later
                phase -- but inline JSON keeps this anchor call
                self-contained and dependency-free today.)

        Returns:
            AnchorResult with transaction details

        Raises:
            ConnectionError: If unable to connect to network
            ValueError: If watermark_hash/content_id format is invalid or
                no signing key is configured

        Example:
            >>> result = await anchor.anchor_watermark(
            ...     watermark_hash="0x123abc...",
            ...     content_id="img_001"
            ... )
            >>> print(f"TX: {result.tx_hash}")
        """
        if not watermark_hash:
            raise ValueError("watermark_hash must be a non-empty string")
        if not content_id:
            raise ValueError("content_id must be a non-empty string")

        logger.info(f"Anchoring watermark: {watermark_hash[:16]}... to {self.network}")

        account = await self._require_signing_account()
        web3 = await self._get_web3()
        contract = await self._get_contract()

        watermark_bytes = _to_bytes32(watermark_hash)
        content_bytes = _to_bytes32(content_id)
        metadata_uri = json.dumps(metadata) if metadata else ""

        try:
            anchor_fee: int = await contract.functions.anchorFee().call()

            nonce = await web3.eth.get_transaction_count(account.address)
            gas_price = await web3.eth.gas_price

            fn = contract.functions.anchorWatermark(
                watermark_bytes, content_bytes, metadata_uri
            )
            estimated_gas = await fn.estimate_gas(
                {"from": account.address, "value": anchor_fee}
            )
            gas_limit = int(estimated_gas * (100 + _GAS_ESTIMATE_BUFFER_PCT) / 100)

            tx = await fn.build_transaction(
                {
                    "from": account.address,
                    "value": anchor_fee,
                    "nonce": nonce,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "chainId": self.chain_id,
                }
            )

            signed_tx = account.sign_transaction(tx)
            tx_hash = await web3.eth.send_raw_transaction(signed_tx.raw_transaction)

            receipt = await web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=_RECEIPT_TIMEOUT_SECONDS
            )

            if receipt["status"] != 1:
                return AnchorResult(
                    success=False,
                    tx_hash=tx_hash.to_0x_hex(),
                    block_number=receipt["blockNumber"],
                    gas_used=receipt["gasUsed"],
                    network=self.network,
                    timestamp=None,
                    error="Transaction reverted on-chain",
                )

            anchor_id = None
            anchored_events = contract.events.WatermarkAnchored().process_receipt(
                receipt
            )
            if anchored_events:
                anchor_id = _bytes32_to_hex(anchored_events[0]["args"]["anchorId"])

            block = await web3.eth.get_block(receipt["blockNumber"])

            return AnchorResult(
                success=True,
                tx_hash=tx_hash.to_0x_hex(),
                block_number=receipt["blockNumber"],
                gas_used=receipt["gasUsed"],
                network=self.network,
                timestamp=block["timestamp"],
                anchor_id=anchor_id,
            )

        except ContractLogicError as exc:
            logger.error(f"Contract reverted anchor_watermark: {exc}")
            return AnchorResult(
                success=False,
                tx_hash=None,
                block_number=None,
                gas_used=None,
                network=self.network,
                timestamp=None,
                error=str(exc),
            )
        except TimeExhausted as exc:
            logger.error(f"Timed out waiting for anchor_watermark receipt: {exc}")
            return AnchorResult(
                success=False,
                tx_hash=None,
                block_number=None,
                gas_used=None,
                network=self.network,
                timestamp=None,
                error=f"Transaction not mined within {_RECEIPT_TIMEOUT_SECONDS}s",
            )

    async def verify_anchor(
        self, watermark_hash: str, content_id: str | None = None
    ) -> bool:
        """
        Verify if watermark is anchored on blockchain.

        Args:
            watermark_hash: SHA-256 hash (or stable identifier string) of
                the watermark data
            content_id: Content ID to verify against. The contract indexes
                anchors by content hash, so this is required to look up
                the matching anchor; if omitted, verification cannot
                proceed and this returns False.

        Returns:
            True if a currently-registered anchor for ``content_id`` has a
            matching ``watermark_hash``, False otherwise (including when
            no anchor exists for ``content_id`` at all).

        Example:
            >>> is_valid = await anchor.verify_anchor("0x123...", "img_001")
        """
        if content_id is None:
            logger.warning(
                "verify_anchor called without content_id; the registry "
                "looks anchors up by content hash, so verification "
                "cannot proceed."
            )
            return False

        logger.info(f"Verifying watermark anchor: {watermark_hash[:16]}...")

        contract = await self._get_contract()
        watermark_bytes = _to_bytes32(watermark_hash)
        content_bytes = _to_bytes32(content_id)

        is_valid, _anchor = await contract.functions.verifyWatermark(
            watermark_bytes, content_bytes
        ).call()
        return bool(is_valid)

    async def get_anchor_history(self, content_id: str) -> list[dict[str, Any]]:
        """
        Get full anchoring history for content.

        The contract's ``contentToAnchor`` mapping only exposes the most
        recent anchor for a given content hash, so full history is
        recovered from the ``WatermarkAnchored`` event log, filtered by
        the (indexed) content hash -- this correctly returns every anchor
        ever created for this content_id, not just the latest one.

        Args:
            content_id: Unique content identifier

        Returns:
            List of anchor events (as dicts) with timestamps and details,
            ordered oldest-first. Empty list if content_id was never
            anchored.
        """
        logger.info(f"Getting anchor history for: {content_id}")

        web3 = await self._get_web3()
        contract = await self._get_contract()
        content_bytes = _to_bytes32(content_id)

        logs = await contract.events.WatermarkAnchored().get_logs(
            argument_filters={"contentHash": content_bytes},
            from_block=0,
            to_block="latest",
        )

        history: list[dict[str, Any]] = []
        # Cache block timestamp lookups -- multiple anchors can land in the
        # same block, no need to refetch.
        block_ts_cache: dict[int, int] = {}
        for entry in logs:
            block_number = entry["blockNumber"]
            if block_number not in block_ts_cache:
                block = await web3.eth.get_block(block_number)
                block_ts_cache[block_number] = block["timestamp"]

            args = entry["args"]
            history.append(
                {
                    "anchor_id": _bytes32_to_hex(args["anchorId"]),
                    "watermark_hash": _bytes32_to_hex(args["watermarkHash"]),
                    "content_hash": _bytes32_to_hex(args["contentHash"]),
                    "creator": args["creator"],
                    "timestamp": block_ts_cache[block_number],
                    "tx_hash": entry["transactionHash"].to_0x_hex(),
                    "block_number": block_number,
                }
            )

        history.sort(key=lambda e: (e["block_number"], e["timestamp"]))
        return history

    async def estimate_gas(
        self,
        watermark_hash: str = "gas-estimate-probe-watermark",
        content_id: str = "gas-estimate-probe-content",
        metadata: dict[str, Any] | None = None,
    ) -> int:
        """
        Estimate gas cost for an anchoring transaction.

        Uses ``eth_estimateGas`` against the live contract with
        representative (or caller-supplied) arguments -- this is a real
        simulated call against current chain state, not a hardcoded
        constant.

        Args:
            watermark_hash: Watermark hash to use for the estimate probe.
                Defaults to a placeholder value; pass the real value you
                intend to anchor for a more precise (though for this
                contract, essentially identical) estimate.
            content_id: Content id to use for the estimate probe.
            metadata: Metadata to size the estimate against (larger
                ``metadataUri`` strings cost more calldata gas).

        Returns:
            Estimated gas units (not wei -- multiply by the current gas
            price yourself if you need a wei/native-token cost estimate).
        """
        contract = await self._get_contract()
        watermark_bytes = _to_bytes32(watermark_hash)
        content_bytes = _to_bytes32(content_id)
        metadata_uri = json.dumps(metadata) if metadata else ""

        anchor_fee: int = await contract.functions.anchorFee().call()

        # A "from" address is required for estimate_gas even though this is
        # a read-only simulation; use the configured signing account if we
        # have one, otherwise fall back to a well-known burn address (its
        # balance/nonce have no bearing on the *contract's* gas usage for
        # this particular call). Note: eth_estimateGas is a dry-run against
        # a throwaway EVM snapshot -- it never actually mines a transaction
        # or mutates real chain state, so calling this repeatedly with the
        # same default probe args is safe and will NOT collide with a
        # previously-anchored watermark (which would revert with
        # "anchor exists" only for an actually-mined anchorWatermark tx).
        from_address = (
            self._account.address
            if self._account is not None
            else "0x0000000000000000000000000000000000dEaD"
        )

        estimated = await contract.functions.anchorWatermark(
            watermark_bytes, content_bytes, metadata_uri
        ).estimate_gas({"from": from_address, "value": anchor_fee})

        return int(estimated)
