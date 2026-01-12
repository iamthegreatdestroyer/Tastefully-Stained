"""
DCT Watermarking Tests
======================

Comprehensive tests for the DCT watermarking module.

Coverage targets:
- Initialization with various parameters
- Watermark embedding and extraction
- JPEG compression resistance
- Error handling
- Edge cases

Run: pytest backend/tests/test_dct.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from watermark_engine.core.dct_processor import DCTWatermarker


class TestDCTWatermarkerInit:
    """Test DCT watermarker initialization."""
    
    def test_default_initialization(self) -> None:
        """Test default initialization parameters."""
        watermarker = DCTWatermarker()
        
        assert watermarker.strength == 0.5
        assert watermarker.block_size == 8
    
    def test_custom_strength(self) -> None:
        """Test initialization with custom strength."""
        watermarker = DCTWatermarker(strength=0.3)
        
        assert watermarker.strength == 0.3
    
    def test_custom_block_size(self) -> None:
        """Test initialization with custom block size."""
        watermarker = DCTWatermarker(block_size=16)
        
        assert watermarker.block_size == 16
    
    def test_invalid_strength_low(self) -> None:
        """Test that strength below 0 raises ValueError."""
        with pytest.raises(ValueError, match="Strength must be in range"):
            DCTWatermarker(strength=-0.1)
    
    def test_invalid_strength_high(self) -> None:
        """Test that strength above 1 raises ValueError."""
        with pytest.raises(ValueError, match="Strength must be in range"):
            DCTWatermarker(strength=1.5)
    
    def test_invalid_block_size(self) -> None:
        """Test that non-power-of-2 block size raises ValueError."""
        with pytest.raises(ValueError, match="Block size must be a power of 2"):
            DCTWatermarker(block_size=7)
    
    def test_valid_block_sizes(self) -> None:
        """Test valid power-of-2 block sizes."""
        for size in [4, 8, 16, 32]:
            watermarker = DCTWatermarker(block_size=size)
            assert watermarker.block_size == size


class TestDCTWatermarkerEmbed:
    """Test DCT watermark embedding."""
    
    @pytest.fixture
    def watermarker(self) -> DCTWatermarker:
        """Create a default watermarker instance."""
        return DCTWatermarker()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    @pytest.fixture
    def sample_watermark(self) -> bytes:
        """Create sample watermark data."""
        return b"Tastefully Stained Test Watermark"
    
    @pytest.mark.skip(reason="Implementation pending in Phase 2")
    def test_embed_watermark_basic(
        self,
        watermarker: DCTWatermarker,
        sample_image: np.ndarray,
        sample_watermark: bytes
    ) -> None:
        """Test basic watermark embedding."""
        result = watermarker.embed_watermark(sample_image, sample_watermark)
        
        assert result.shape == sample_image.shape
        assert result.dtype == sample_image.dtype
    
    @pytest.mark.skip(reason="Implementation pending in Phase 2")
    def test_embed_preserves_dimensions(
        self,
        watermarker: DCTWatermarker,
        sample_watermark: bytes
    ) -> None:
        """Test that embedding preserves image dimensions."""
        for shape in [(256, 256), (512, 512, 3), (1024, 768, 3)]:
            image = np.random.randint(0, 256, shape, dtype=np.uint8)
            result = watermarker.embed_watermark(image, sample_watermark)
            assert result.shape == image.shape
    
    def test_embed_not_implemented(
        self,
        watermarker: DCTWatermarker,
        sample_image: np.ndarray,
        sample_watermark: bytes
    ) -> None:
        """Test that embed raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            watermarker.embed_watermark(sample_image, sample_watermark)


class TestDCTWatermarkerExtract:
    """Test DCT watermark extraction."""
    
    @pytest.fixture
    def watermarker(self) -> DCTWatermarker:
        """Create a default watermarker instance."""
        return DCTWatermarker()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    def test_extract_not_implemented(
        self,
        watermarker: DCTWatermarker,
        sample_image: np.ndarray
    ) -> None:
        """Test that extract raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            watermarker.extract_watermark(sample_image)
