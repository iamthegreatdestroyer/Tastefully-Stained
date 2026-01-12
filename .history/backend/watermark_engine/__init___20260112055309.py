"""
Watermark Engine Package
========================

Core watermarking engine for Tastefully Stained.

This package provides production-grade DCT and DWT watermarking algorithms
with hybrid strategy selection for maximum robustness.

Submodules:
-----------
- core: Core watermarking algorithms (DCT, DWT, hybrid orchestrator)
- api: FastAPI REST API endpoints and models
- blockchain: Ethereum anchoring and IPFS storage
- c2pa: C2PA manifest building and validation
- utils: Utility functions, logging, and configuration

Example:
--------
    >>> from watermark_engine.core import HybridWatermarkOrchestrator
    >>> orchestrator = HybridWatermarkOrchestrator()
    >>> result = orchestrator.embed_robust_watermark(image, watermark_data)
"""

from watermark_engine.core import (
    DCTWatermarker,
    DWTWatermarker,
    HybridWatermarkOrchestrator,
)

__all__ = [
    "DCTWatermarker",
    "DWTWatermarker",
    "HybridWatermarkOrchestrator",
]
