"""
Hybrid Watermarking Algorithm Tests
===================================

Comprehensive tests for the hybrid watermarking orchestrator.

Coverage targets:
- Strategy selection
- Fallback mechanisms
- Confidence scoring
- Error handling

Run: pytest backend/tests/test_hybrid.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from watermark_engine.core.hybrid_algorithm import (
    HybridWatermarkOrchestrator,
    WatermarkStrategy,
)


class TestHybridOrchestratorInit:
    """Test hybrid orchestrator initialization."""
    
    def test_default_initialization(self) -> None:
        """Test default initialization creates internal watermarkers."""
        orchestrator = HybridWatermarkOrchestrator()
        
        assert orchestrator.dct_watermarker is not None
        assert orchestrator.dwt_watermarker is not None
    
    def test_custom_watermarkers(self) -> None:
        """Test initialization with custom watermarkers."""
        from watermark_engine.core.dct_processor import DCTWatermarker
        from watermark_engine.core.dwt_processor import DWTWatermarker
        
        dct = DCTWatermarker(strength=0.7)
        dwt = DWTWatermarker(wavelet='haar')
        
        orchestrator = HybridWatermarkOrchestrator(dct, dwt)
        
        assert orchestrator.dct_watermarker.strength == 0.7
        assert orchestrator.dwt_watermarker.wavelet == 'haar'


class TestWatermarkStrategy:
    """Test watermark strategy enum."""
    
    def test_strategy_values(self) -> None:
        """Test strategy enum has expected values."""
        assert WatermarkStrategy.DCT_PRIMARY.value == "dct_primary"
        assert WatermarkStrategy.DWT_PRIMARY.value == "dwt_primary"
        assert WatermarkStrategy.HYBRID_DUAL.value == "hybrid_dual"
        assert WatermarkStrategy.AUTO.value == "auto"


class TestHybridOrchestratorEmbed:
    """Test hybrid watermark embedding."""
    
    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    def test_embed_not_implemented(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray
    ) -> None:
        """Test that embed raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            orchestrator.embed_robust_watermark(sample_image, b"test")


class TestHybridOrchestratorExtract:
    """Test hybrid watermark extraction."""
    
    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()
    
    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image."""
        return np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    
    def test_extract_not_implemented(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray
    ) -> None:
        """Test that extract raises NotImplementedError until Phase 2."""
        with pytest.raises(NotImplementedError):
            orchestrator.extract_watermark(sample_image)


class TestImageAnalysis:
    """Test image characteristic analysis."""
    
    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()
    
    def test_analyze_not_implemented(
        self,
        orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """Test that analysis raises NotImplementedError until Phase 2."""
        image = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        
        with pytest.raises(NotImplementedError):
            orchestrator.analyze_image_characteristics(image)
