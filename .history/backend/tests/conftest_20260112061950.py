"""
Pytest Configuration and Fixtures
==================================

Shared fixtures and configuration for the test suite.
"""

from __future__ import annotations

import numpy as np
import pytest


@pytest.fixture(scope="session")
def sample_grayscale_image() -> np.ndarray:
    """Create a sample grayscale test image (session-scoped for efficiency)."""
    np.random.seed(42)  # Reproducible
    return np.random.randint(0, 256, (256, 256), dtype=np.uint8)


@pytest.fixture(scope="session")
def sample_rgb_image() -> np.ndarray:
    """Create a sample RGB test image (session-scoped for efficiency)."""
    np.random.seed(42)  # Reproducible
    return np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)


@pytest.fixture(scope="session")
def sample_rgba_image() -> np.ndarray:
    """Create a sample RGBA test image (session-scoped for efficiency)."""
    np.random.seed(42)  # Reproducible
    return np.random.randint(0, 256, (256, 256, 4), dtype=np.uint8)


@pytest.fixture
def sample_watermark_data() -> bytes:
    """Create sample watermark data."""
    return b"Tastefully Stained Test Watermark v1.0"


@pytest.fixture
def sample_hash() -> str:
    """Create a sample SHA-256 hash."""
    return "sha256:a" * 64


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "blockchain: marks tests requiring blockchain connection"
    )
