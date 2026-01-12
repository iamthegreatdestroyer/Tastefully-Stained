"""
DWT Watermarking Tests
======================

Comprehensive tests for the DWT watermarking module.

Coverage targets:
- Initialization with various wavelet types
- Watermark embedding and extraction
- Multi-level decomposition
- Error handling

Run: pytest backend/tests/test_dwt.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from watermark_engine.core.dwt_processor import DWTWatermarker


class TestDWTWatermarkerInit:
    """Test DWT watermarker initialization."""
    
    def test_default_initialization(self) -> None:
        """Test default initialization parameters."""
        watermarker = DWTWatermarker()
        
        assert watermarker.wavelet == 'db4'
        assert watermarker.level == 3
        assert watermarker.strength == 0.3
    
    def test_custom_wavelet(self) -> None:
        """Test initialization with custom wavelet."""
        watermarker = DWTWatermarker(wavelet='haar')
        
        assert watermarker.wavelet == 'haar'
    
    def test_custom_level(self) -> None:
        """Test initialization with custom decomposition level."""
        watermarker = DWTWatermarker(level=5)
        
        assert watermarker.level == 5
    
    def test_invalid_wavelet(self) -> None:
        """Test that unsupported wavelet raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported wavelet"):
            DWTWatermarker(wavelet='invalid_wavelet')
    
    def test_invalid_level(self) -> None:
        """Test that non-positive level raises ValueError."""
        with pytest.raises(ValueError, match="Level must be positive"):
            DWTWatermarker(level=0)
    
    def test_invalid_strength(self) -> None:
        """Test that invalid strength raises ValueError."""
        with pytest.raises(ValueError, match="Strength must be in range"):
            DWTWatermarker(strength=2.0)
    
    def test_all_supported_wavelets(self) -> None:
        """Test all supported wavelet types."""
        for wavelet in DWTWatermarker.SUPPORTED_WAVELETS:
            watermarker = DWTWatermarker(wavelet=wavelet)
            assert watermarker.wavelet == wavelet


class TestDWTWatermarkerEmbed:
    """Test DWT watermark embedding."""
    
    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    def test_embed_not_implemented(
        self,
        watermarker: DWTWatermarker,
        sample_image: np.ndarray
    ) -> None:
        """Test that embed raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            watermarker.embed_watermark(sample_image, b"test")


class TestDWTWatermarkerExtract:
    """Test DWT watermark extraction."""
    
    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    def test_extract_not_implemented(
        self,
        watermarker: DWTWatermarker,
        sample_image: np.ndarray
    ) -> None:
        """Test that extract raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            watermarker.extract_watermark(sample_image)


class TestDWTWatermarkerQuality:
    """Test DWT quality metrics."""
    
    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()
    
    def test_quality_metrics_not_implemented(
        self,
        watermarker: DWTWatermarker
    ) -> None:
        """Test that quality metrics raises NotImplementedError until Phase 2."""
        image = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        
        with pytest.raises(NotImplementedError):
            watermarker.calculate_quality_metrics(image, image)
