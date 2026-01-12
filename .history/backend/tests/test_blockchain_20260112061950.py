"""
Blockchain Integration Tests
============================

Comprehensive tests for Ethereum anchoring and IPFS storage.

Coverage targets:
- Ethereum connection and transactions
- IPFS storage and retrieval
- Error handling and retry logic

Run: pytest backend/tests/test_blockchain.py -v
"""

from __future__ import annotations

import pytest

from watermark_engine.blockchain.ethereum_anchor import EthereumAnchor, AnchorResult
from watermark_engine.blockchain.ipfs_handler import IPFSHandler


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


class TestIPFSHandlerOperations:
    """Test IPFS handler operations."""
    
    @pytest.fixture
    def handler(self) -> IPFSHandler:
        """Create test handler instance."""
        return IPFSHandler(gateway_url="https://ipfs.infura.io:5001")
    
    @pytest.mark.asyncio
    async def test_store_not_implemented(self, handler: IPFSHandler) -> None:
        """Test that storage raises NotImplementedError until Phase 5."""
        with pytest.raises(NotImplementedError):
            await handler.store_watermarked_image(b"test data")
    
    def test_get_public_url(self, handler: IPFSHandler) -> None:
        """Test public URL generation."""
        cid = "QmTest123"
        url = handler.get_public_url(cid)
        
        assert cid in url
        assert url.startswith("https://")
