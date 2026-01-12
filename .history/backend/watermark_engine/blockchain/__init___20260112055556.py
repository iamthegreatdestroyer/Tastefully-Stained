"""
Blockchain Integration Package
==============================

Ethereum blockchain anchoring and IPFS storage for Tastefully Stained.

This package provides:
- Ethereum smart contract interaction for watermark registration
- IPFS storage for watermarked content and manifests
- Transaction management and gas optimization
- Multi-chain support preparation

Example:
--------
    >>> from watermark_engine.blockchain import EthereumAnchor, IPFSHandler
    >>> 
    >>> anchor = EthereumAnchor(provider_url="...")
    >>> tx_hash = await anchor.anchor_watermark(watermark_hash)
"""

from watermark_engine.blockchain.ethereum_anchor import EthereumAnchor
from watermark_engine.blockchain.ipfs_handler import IPFSHandler

__all__ = [
    "EthereumAnchor",
    "IPFSHandler",
]
