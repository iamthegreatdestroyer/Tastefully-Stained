"""
Tastefully Stained - Backend Package
=====================================

AI Content Provenance & Watermarking Service Backend.

This package provides the core watermarking engine, C2PA integration,
blockchain anchoring, and REST API for the Tastefully Stained service.

Modules:
--------
- watermark_engine: Core watermarking algorithms (DCT, DWT, hybrid)
- watermark_engine.api: FastAPI REST API endpoints
- watermark_engine.blockchain: Ethereum anchoring and IPFS storage
- watermark_engine.c2pa: C2PA manifest building and validation
- watermark_engine.utils: Utility functions and configuration

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

__version__ = "0.1.0"
__author__ = "Tastefully Stained Team"
__license__ = "MIT"
