"""
Utilities Package
=================

Shared utilities for Tastefully Stained watermarking service.

This package provides:
- Image loading and format handling
- Structured logging configuration
- Configuration management
- Common helper functions

Example:
--------
    >>> from watermark_engine.utils import ImageLoader, setup_logging, Config
    >>> 
    >>> setup_logging(level="DEBUG")
    >>> config = Config()
    >>> 
    >>> loader = ImageLoader()
    >>> image = loader.load("path/to/image.jpg")
"""

from watermark_engine.utils.image_loader import ImageLoader
from watermark_engine.utils.logger import setup_logging, get_logger
from watermark_engine.utils.config import Config, get_config

__all__ = [
    "ImageLoader",
    "setup_logging",
    "get_logger",
    "Config",
    "get_config",
]
