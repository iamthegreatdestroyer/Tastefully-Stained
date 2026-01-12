"""
Core Watermarking Algorithms Package
=====================================

This package contains the core watermarking algorithms:
- DCT (Discrete Cosine Transform) watermarking
- DWT (Discrete Wavelet Transform) watermarking
- Hybrid algorithm orchestration

These algorithms are designed for:
- JPEG compression resistance
- Robustness against scaling and rotation
- Invisibility (high perceptual quality)
- C2PA compliance

Example:
--------
    >>> from watermark_engine.core import DCTWatermarker, DWTWatermarker
    >>> dct = DCTWatermarker(strength=0.5)
    >>> watermarked = dct.embed_watermark(image, watermark_data)
"""

from watermark_engine.core.dct_processor import DCTWatermarker
from watermark_engine.core.dwt_processor import DWTWatermarker
from watermark_engine.core.hybrid_algorithm import HybridWatermarkOrchestrator

__all__ = [
    "DCTWatermarker",
    "DWTWatermarker",
    "HybridWatermarkOrchestrator",
]
