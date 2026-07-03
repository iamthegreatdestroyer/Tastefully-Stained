"""
Hybrid Watermarking Algorithm Tests
===================================

Comprehensive tests for the hybrid watermarking orchestrator.

Coverage targets:
- Strategy selection
- Redundant dual embedding + round-trip extraction
- Fallback mechanisms
- Confidence scoring
- Error handling

Run: pytest backend/tests/test_hybrid.py -v
"""

from __future__ import annotations

import numpy as np
import pytest

from watermark_engine.core.hybrid_algorithm import (
    ExtractionResult,
    HybridWatermarkOrchestrator,
    ImageCharacteristics,
    WatermarkStrategy,
)


# ---------------------------------------------------------------------------
# Shared test image fixtures
# ---------------------------------------------------------------------------
#
# These mirror the fixture style already used in test_dct.py
# (`_natural_test_image`): deliberately distinct images so
# analyze_image_characteristics has something genuinely different to
# differentiate between, rather than relying on i.i.d. random noise alone
# (which is an adversarial worst case, not representative "smooth" content).


def _natural_test_image(seed: int, height: int = 512, width: int = 512) -> np.ndarray:
    """Smooth-gradient-plus-mild-noise RGB image (moderate detail)."""
    rng = np.random.default_rng(seed)
    y_idx, x_idx = np.mgrid[0:height, 0:width]
    gradient = (128 + 60 * np.sin(x_idx / 40) + 40 * np.cos(y_idx / 55)).astype(np.float32)
    noise = rng.integers(-10, 10, (height, width, 3)).astype(np.float32)
    offset = rng.integers(0, 50, (1, 1, 3)).astype(np.float32)
    return np.clip(gradient[..., None] + noise + offset, 0, 255).astype(np.uint8)


def _smooth_test_image(height: int = 512, width: int = 512) -> np.ndarray:
    """
    Very smooth, low-frequency-only RGB image: a flat linear gradient with
    zero noise. This is the "low edge density, low variance" end of the
    spectrum analyze_image_characteristics needs to recognize.
    """
    y_idx, x_idx = np.mgrid[0:height, 0:width]
    gradient = (100 + (x_idx / width) * 80 + (y_idx / height) * 40).astype(np.float32)
    img = np.repeat(gradient[..., None], 3, axis=2)
    return np.clip(img, 0, 255).astype(np.uint8)


def _noisy_test_image(seed: int, height: int = 512, width: int = 512) -> np.ndarray:
    """
    High-detail / noisy RGB image: i.i.d. uniform random pixels. This is
    the adversarial worst case for edge density / variance -- the "high
    detail" end of the spectrum.
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (height, width, 3), dtype=np.uint8)


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


class TestImageAnalysis:
    """
    Test image characteristic analysis.

    These assertions were derived from empirical measurements (see
    hybrid_algorithm.py's threshold-calibration comment block), not
    invented: a genuinely smooth image and a genuinely high-detail/noisy
    image were run through analyze_image_characteristics and their
    edge_density / color_variance / recommended_strategy outputs were
    confirmed to differ in the expected direction before these thresholds
    were fixed in the implementation.
    """

    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()

    def test_analyze_returns_image_characteristics(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """Test that analysis returns a well-formed ImageCharacteristics."""
        image = _natural_test_image(seed=1)

        result = orchestrator.analyze_image_characteristics(image)

        assert isinstance(result, ImageCharacteristics)
        assert isinstance(result.recommended_strategy, WatermarkStrategy)
        assert 0.0 <= result.edge_density <= 1.0
        assert result.color_variance >= 0.0

    def test_smooth_image_has_low_edge_density_and_variance(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """A flat gradient should score very low on both edge density and
        color variance -- there is essentially no high-frequency content
        or texture for Canny or pixel variance to pick up on."""
        smooth = _smooth_test_image()

        result = orchestrator.analyze_image_characteristics(smooth)

        assert result.edge_density < 0.02
        assert result.color_variance < 1000.0
        assert result.is_photographic is True
        assert result.has_high_frequency is False

    def test_noisy_image_has_high_edge_density_and_variance(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """i.i.d. random noise should score much higher on edge density
        and color variance than a smooth gradient -- there is nothing
        but high-frequency content."""
        noisy = _noisy_test_image(seed=2)

        result = orchestrator.analyze_image_characteristics(noisy)

        assert result.edge_density > 0.15
        assert result.color_variance > 4000.0
        assert result.has_high_frequency is True

    def test_smooth_and_noisy_images_are_genuinely_differentiated(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """
        Directly compare a smooth image against a noisy one and assert the
        analysis actually differentiates them (rather than each test above
        independently happening to clear a fixed threshold). This is the
        core "sane, differentiated output for genuinely different images"
        requirement.
        """
        smooth = _smooth_test_image()
        noisy = _noisy_test_image(seed=3)

        smooth_result = orchestrator.analyze_image_characteristics(smooth)
        noisy_result = orchestrator.analyze_image_characteristics(noisy)

        assert smooth_result.edge_density < noisy_result.edge_density
        assert smooth_result.color_variance < noisy_result.color_variance
        # Different enough inputs should not collapse to the same
        # recommendation.
        assert (
            smooth_result.recommended_strategy
            != noisy_result.recommended_strategy
        )
        assert smooth_result.recommended_strategy == WatermarkStrategy.DWT_PRIMARY
        assert noisy_result.recommended_strategy == WatermarkStrategy.DCT_PRIMARY

    def test_moderate_detail_image_recommends_hybrid_dual(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """A moderate gradient+mild-noise image (neither flat nor
        adversarially noisy) should fall into the middle band and get the
        redundant dual-embedding recommendation."""
        natural = _natural_test_image(seed=4)

        result = orchestrator.analyze_image_characteristics(natural)

        assert result.recommended_strategy == WatermarkStrategy.HYBRID_DUAL

    def test_analyze_rejects_bad_dimensions(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """1D input should raise rather than silently misbehave."""
        with pytest.raises(ValueError):
            orchestrator.analyze_image_characteristics(np.zeros(100, dtype=np.uint8))


class TestHybridOrchestratorEmbedExtractRoundTrip:
    """
    Test hybrid watermark embedding + extraction round trips.

    These confirm the actual, empirically-verified composition behavior:
    DCT and DWT can both be embedded redundantly into the same image (DCT
    first, then DWT on the DCT-watermarked output) and each is
    independently recoverable afterward -- neither corrupts the other.
    """

    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()

    @pytest.fixture
    def sample_image(self) -> np.ndarray:
        """Create a sample test image with genuine spatial structure
        (not pure noise) so DCT/DWT embedding capacity assumptions hold
        the same way they do in the DCT/DWT test suites."""
        return _natural_test_image(seed=100)

    def test_embed_dct_primary_round_trip(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """DCT_PRIMARY strategy embeds via DCT only; extract_watermark
        should recover it (falling through DCT's own success path)."""
        payload = b"dct-primary-payload"

        watermarked = orchestrator.embed_robust_watermark(
            sample_image, payload, WatermarkStrategy.DCT_PRIMARY
        )

        assert watermarked.shape == sample_image.shape
        assert watermarked.dtype == np.uint8

        result = orchestrator.extract_watermark(watermarked)
        assert isinstance(result, ExtractionResult)
        assert result.data == payload
        assert result.strategy_used == WatermarkStrategy.DCT_PRIMARY
        assert result.confidence > 0.0

    def test_embed_dwt_primary_round_trip(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """DWT_PRIMARY strategy embeds via DWT only; extract_watermark
        should fall back to DWT after DCT fails to find its watermark."""
        payload = b"dwt-primary-payload"

        watermarked = orchestrator.embed_robust_watermark(
            sample_image, payload, WatermarkStrategy.DWT_PRIMARY
        )

        result = orchestrator.extract_watermark(watermarked)
        assert result.data == payload
        assert result.strategy_used == WatermarkStrategy.DWT_PRIMARY
        assert result.confidence > 0.0

    def test_embed_hybrid_dual_round_trip_both_methods_recover(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """
        Core redundant-embedding requirement: the SAME watermark payload
        is embedded via BOTH DCT and DWT into the same image, and BOTH
        methods must be able to independently recover it afterward --
        not just whichever one extract_watermark() happens to try first.
        """
        payload = b"redundant-hybrid-payload-1234"

        watermarked = orchestrator.embed_robust_watermark(
            sample_image, payload, WatermarkStrategy.HYBRID_DUAL
        )

        assert watermarked.shape == sample_image.shape

        # Directly verify both underlying watermarkers can recover the
        # payload independently (this is the "verify empirically that both
        # watermarks are actually independently recoverable" requirement).
        dct_recovered = orchestrator.dct_watermarker.extract_watermark(watermarked)
        dwt_recovered = orchestrator.dwt_watermarker.extract_watermark(watermarked)
        assert dct_recovered == payload
        assert dwt_recovered == payload

        # And the orchestrator's own extract_watermark() should also
        # succeed (via whichever method it tries first).
        result = orchestrator.extract_watermark(watermarked)
        assert result.data == payload

    def test_embed_hybrid_dual_preserves_perceptual_quality(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """Redundant dual embedding (two watermarks stacked on the same
        image) should still produce a high-fidelity result, not visibly
        destroy the image. PSNR > 40dB and SSIM > 0.98 are conservative
        floors well below what was empirically measured (~49-50dB /
        ~0.995) during development."""
        payload = b"quality-check-payload"

        watermarked = orchestrator.embed_robust_watermark(
            sample_image, payload, WatermarkStrategy.HYBRID_DUAL
        )

        metrics = orchestrator.dwt_watermarker.calculate_quality_metrics(
            sample_image, watermarked
        )
        assert metrics["psnr"] > 40.0
        assert metrics["ssim"] > 0.98

    def test_embed_auto_strategy_resolves_and_round_trips(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """AUTO strategy should analyze the image, pick a concrete
        strategy, and produce a watermark recoverable via
        extract_watermark()."""
        payload = b"auto-strategy-payload"

        watermarked = orchestrator.embed_robust_watermark(
            sample_image, payload, WatermarkStrategy.AUTO
        )

        result = orchestrator.extract_watermark(watermarked)
        assert result.data == payload

    def test_embed_unknown_strategy_raises(
        self,
        orchestrator: HybridWatermarkOrchestrator,
        sample_image: np.ndarray,
    ) -> None:
        """A strategy value that isn't handled should fail loudly, not
        silently no-op."""

        class _FakeStrategy:
            value = "not_a_real_strategy"

        with pytest.raises(ValueError):
            orchestrator.embed_robust_watermark(
                sample_image, b"data", _FakeStrategy()  # type: ignore[arg-type]
            )


class TestHybridOrchestratorExtractFallback:
    """Test extraction fallback and failure behavior."""

    @pytest.fixture
    def orchestrator(self) -> HybridWatermarkOrchestrator:
        """Create a default orchestrator instance."""
        return HybridWatermarkOrchestrator()

    def test_extract_raises_on_unwatermarked_image(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """An image with no watermark at all should raise, having tried
        (and failed) both DCT and DWT rather than returning garbage."""
        plain_image = _natural_test_image(seed=200)

        with pytest.raises(ValueError):
            orchestrator.extract_watermark(plain_image)

    def test_extract_falls_back_from_dct_to_dwt(
        self, orchestrator: HybridWatermarkOrchestrator
    ) -> None:
        """When only a DWT watermark is present, DCT extraction must fail
        internally and the orchestrator must fall back to DWT rather than
        propagating the DCT failure."""
        image = _natural_test_image(seed=201)
        payload = b"dwt-only-fallback-check"

        watermarked = orchestrator.dwt_watermarker.embed_watermark(image, payload)

        result = orchestrator.extract_watermark(watermarked)
        assert result.data == payload
        assert result.strategy_used == WatermarkStrategy.DWT_PRIMARY
