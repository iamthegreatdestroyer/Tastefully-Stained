"""
API Package
===========

FastAPI REST API endpoints for Tastefully Stained watermarking service.

This package provides the HTTP API layer for:
- Watermark embedding and extraction
- Image upload and processing
- C2PA manifest management
- Blockchain anchoring

Example:
--------
    >>> from watermark_engine.api import create_app
    >>> app = create_app()
    >>> # Run with: uvicorn watermark_engine.api:app --reload
"""

from watermark_engine.api.routes import router
from watermark_engine.api.models import WatermarkRequest, WatermarkResponse
from watermark_engine.api.middleware import setup_middleware

__all__ = [
    "router",
    "WatermarkRequest",
    "WatermarkResponse",
    "setup_middleware",
]
