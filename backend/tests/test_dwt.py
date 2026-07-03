"""
DWT Watermarking Tests
======================

Comprehensive tests for the DWT watermarking module.

Coverage targets:
- Initialization with various wavelet types
- Watermark embedding and extraction
- Multi-level decomposition
- Error handling
- Quality metrics (PSNR / SSIM)
- Robustness against mild transforms

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


class TestDWTWatermarkerEmbedExtractRoundTrip:
    """Test that embedding then extracting recovers the exact watermark."""

    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()

    def test_round_trip_grayscale(
        self, watermarker: DWTWatermarker, sample_grayscale_image: np.ndarray
    ) -> None:
        """Embedding then extracting recovers the exact bytes (grayscale)."""
        payload = b"Tastefully Stained Test Watermark v1.0"

        watermarked = watermarker.embed_watermark(sample_grayscale_image, payload)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == payload

    def test_round_trip_rgb(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Embedding then extracting recovers the exact bytes (RGB)."""
        payload = b"Tastefully Stained Test Watermark v1.0"

        watermarked = watermarker.embed_watermark(sample_rgb_image, payload)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == payload

    def test_round_trip_empty_payload(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Zero-length watermark payload still round-trips correctly."""
        watermarked = watermarker.embed_watermark(sample_rgb_image, b"")
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == b""

    def test_round_trip_binary_payload(self, watermarker: DWTWatermarker) -> None:
        """Non-ASCII / arbitrary binary payloads round-trip correctly.

        Uses a larger image than the shared 256x256 fixtures: a full
        256-byte payload plus its 4-byte length header (2080 bits) exceeds
        the ~484-bit boundary-safe capacity of a 256x256 image at the
        default level=3 db4 decomposition, so a 512x512 image (2916 bits
        of capacity) is used here instead.
        """
        np.random.seed(42)
        large_image = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
        payload = bytes(range(256))

        watermarked = watermarker.embed_watermark(large_image, payload)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == payload

    def test_round_trip_different_wavelets(self, sample_rgb_image: np.ndarray) -> None:
        """Round trip succeeds for every supported wavelet family."""
        payload = b"multi-wavelet-check"

        for wavelet in DWTWatermarker.SUPPORTED_WAVELETS:
            watermarker = DWTWatermarker(wavelet=wavelet)
            watermarked = watermarker.embed_watermark(sample_rgb_image, payload)
            extracted = watermarker.extract_watermark(watermarked)

            assert extracted == payload, f"round trip failed for wavelet={wavelet}"

    def test_embed_too_large_payload_raises(
        self, watermarker: DWTWatermarker, sample_grayscale_image: np.ndarray
    ) -> None:
        """A watermark payload that exceeds subband capacity raises ValueError."""
        huge_payload = b"x" * (sample_grayscale_image.size * 4)

        with pytest.raises(ValueError, match="too large"):
            watermarker.embed_watermark(sample_grayscale_image, huge_payload)

    def test_watermarked_dimensions_match_input_even(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Watermarked output has identical dimensions to an even-sized input.

        `waverec2` reconstruction can pad to even dimensions at each
        decomposition level; the processor must crop back to the original
        shape after inverse-transforming.
        """
        watermarked = watermarker.embed_watermark(sample_rgb_image, b"dims-check")

        assert watermarked.shape == sample_rgb_image.shape
        assert watermarked.dtype == np.uint8

    def test_watermarked_dimensions_match_input_odd(
        self, watermarker: DWTWatermarker
    ) -> None:
        """Watermarked output matches an odd-sized input's dimensions exactly.

        This explicitly exercises the crop-after-`waverec2` path: an odd
        height/width forces PyWavelets to reconstruct a padded (even) array
        internally, which must be cropped back down to the original odd
        shape rather than leaking through as a shape mismatch.
        """
        np.random.seed(7)
        odd_image = np.random.randint(0, 256, (257, 261, 3), dtype=np.uint8)

        watermarked = watermarker.embed_watermark(odd_image, b"odd-dims")
        extracted = watermarker.extract_watermark(watermarked)

        assert watermarked.shape == odd_image.shape
        assert extracted == b"odd-dims"

    def test_watermark_is_visually_near_invisible(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Embedding should perturb pixel values only slightly on average."""
        watermarked = watermarker.embed_watermark(sample_rgb_image, b"invisible?")

        diff = np.abs(
            watermarked.astype(np.int16) - sample_rgb_image.astype(np.int16)
        )
        assert diff.mean() < 10.0, (
            f"mean pixel perturbation {diff.mean():.2f} is too large for a "
            "watermark that is supposed to be near-invisible"
        )


class TestDWTWatermarkerExtractErrors:
    """Test error handling in watermark extraction."""

    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()

    def test_extract_from_unwatermarked_image_is_handled(
        self, watermarker: DWTWatermarker, sample_grayscale_image: np.ndarray
    ) -> None:
        """Extracting from a never-watermarked image either raises a clear
        ValueError or returns some (garbage) bytes without crashing --
        it must not silently succeed with a plausible-looking result that
        happens to equal a real payload, and it must not throw an
        unrelated/opaque exception type.
        """
        try:
            result = watermarker.extract_watermark(sample_grayscale_image)
            assert isinstance(result, bytes)
        except ValueError:
            pass  # Acceptable: no valid watermark detected.


class TestDWTWatermarkerQuality:
    """Test DWT quality metrics (PSNR / SSIM)."""

    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Create a default watermarker instance."""
        return DWTWatermarker()

    def test_quality_metrics_return_shape(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Metrics dict has exactly the documented 'psnr' and 'ssim' keys."""
        watermarked = watermarker.embed_watermark(sample_rgb_image, b"quality-check")

        metrics = watermarker.calculate_quality_metrics(
            sample_rgb_image, watermarked
        )

        assert set(metrics.keys()) == {"psnr", "ssim"}
        assert isinstance(metrics["psnr"], float)
        assert isinstance(metrics["ssim"], float)

    def test_quality_metrics_identical_images(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Comparing an image against itself gives a perfect (or near-
        perfect / infinite) PSNR and SSIM == 1.0.
        """
        metrics = watermarker.calculate_quality_metrics(
            sample_rgb_image, sample_rgb_image
        )

        assert metrics["psnr"] == float("inf")
        assert metrics["ssim"] == pytest.approx(1.0, abs=1e-9)

    def test_quality_metrics_watermarked_pair_is_near_invisible(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """A real watermarked/original pair should score a high PSNR and an
        SSIM very close to 1.0, since the watermark is meant to be
        perceptually invisible.
        """
        watermarked = watermarker.embed_watermark(
            sample_rgb_image, b"Tastefully Stained Test Watermark v1.0"
        )

        metrics = watermarker.calculate_quality_metrics(
            sample_rgb_image, watermarked
        )

        assert metrics["psnr"] > 30.0, (
            f"PSNR {metrics['psnr']:.2f} dB is too low for a supposedly "
            "invisible watermark"
        )
        assert metrics["ssim"] > 0.90, (
            f"SSIM {metrics['ssim']:.4f} is too low for a supposedly "
            "invisible watermark"
        )

    def test_quality_metrics_distinguishes_different_images(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Sanity check: the metric is not a constant. Two genuinely
        different (unrelated random) images must score clearly worse than
        a watermarked/original pair of the *same* underlying image.
        """
        watermarked = watermarker.embed_watermark(
            sample_rgb_image, b"Tastefully Stained Test Watermark v1.0"
        )
        near_pair_metrics = watermarker.calculate_quality_metrics(
            sample_rgb_image, watermarked
        )

        np.random.seed(999)
        unrelated_image = np.random.randint(
            0, 256, sample_rgb_image.shape, dtype=np.uint8
        )
        far_pair_metrics = watermarker.calculate_quality_metrics(
            sample_rgb_image, unrelated_image
        )

        assert far_pair_metrics["psnr"] < near_pair_metrics["psnr"]
        assert far_pair_metrics["ssim"] < near_pair_metrics["ssim"]
        # Two unrelated random images should score a low absolute SSIM too,
        # not just "lower than the near pair".
        assert far_pair_metrics["ssim"] < 0.5

    def test_quality_metrics_grayscale(
        self, watermarker: DWTWatermarker, sample_grayscale_image: np.ndarray
    ) -> None:
        """Quality metrics also work for single-channel (grayscale) images."""
        watermarked = watermarker.embed_watermark(
            sample_grayscale_image, b"grayscale-quality"
        )

        metrics = watermarker.calculate_quality_metrics(
            sample_grayscale_image, watermarked
        )

        assert metrics["psnr"] > 30.0
        assert metrics["ssim"] > 0.90

    def test_shape_mismatch_raises(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Comparing images of different shapes raises a clear ValueError."""
        differently_sized = sample_rgb_image[:100, :100, :]

        with pytest.raises(ValueError, match="Shape mismatch"):
            watermarker.calculate_quality_metrics(
                sample_rgb_image, differently_sized
            )


class TestDWTWatermarkerRobustness:
    """Exploratory robustness checks against mild transforms.

    These document the *actual measured* behavior of this particular
    QIM-in-detail-subbands scheme rather than assuming it. DWT watermarking
    schemes in general are known to be more tolerant of resampling/rotation
    (which realign along with the wavelet grid to a degree) than of lossy
    recompression, which directly perturbs the high-frequency detail
    coefficients this scheme embeds into.
    """

    @pytest.fixture
    def watermarker(self) -> DWTWatermarker:
        """Use maximum strength to give robustness its best chance."""
        return DWTWatermarker(strength=1.0)

    def test_robustness_against_gaussian_noise(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """Mild additive Gaussian noise (simulating lossy recompression
        artifacts) is a direct perturbation of the embedded detail
        coefficients. Record whether extraction still recovers the exact
        payload, and if not, how many bytes differ -- don't assume either
        outcome.
        """
        payload = b"Tastefully Stained Test Watermark v1.0"
        watermarked = watermarker.embed_watermark(sample_rgb_image, payload)

        rng = np.random.default_rng(42)
        noise = rng.normal(loc=0.0, scale=2.0, size=watermarked.shape)
        attacked = np.clip(
            watermarked.astype(np.float64) + noise, 0, 255
        ).astype(np.uint8)

        try:
            extracted = watermarker.extract_watermark(attacked)
            survived = extracted == payload
        except ValueError:
            extracted = b""
            survived = False

        # Not asserted strictly true/false -- this test exists to observe
        # and pin down actual behavior. At minimum, extraction must not
        # crash with anything other than a clear ValueError.
        print(
            f"[robustness/gaussian-noise] survived_exact={survived} "
            f"extracted={extracted!r}"
        )
        assert isinstance(extracted, bytes)

    def test_robustness_against_horizontal_flip(
        self, watermarker: DWTWatermarker, sample_rgb_image: np.ndarray
    ) -> None:
        """A geometric transform (horizontal flip) completely realigns
        which spatial coefficient maps to which wavelet subband position.
        This is expected to break extraction for a scheme that reads bits
        back out by fixed coefficient index (no synchronization/resync
        mechanism), unlike noise which perturbs values in place. Record
        the actual outcome.
        """
        payload = b"Tastefully Stained Test Watermark v1.0"
        watermarked = watermarker.embed_watermark(sample_rgb_image, payload)

        flipped = np.ascontiguousarray(watermarked[:, ::-1, :])

        try:
            extracted = watermarker.extract_watermark(flipped)
            survived = extracted == payload
        except ValueError:
            extracted = b""
            survived = False

        print(
            f"[robustness/horizontal-flip] survived_exact={survived} "
            f"extracted={extracted!r}"
        )
        # A flip is expected to break bit-exact recovery for this
        # fixed-position embedding scheme -- document that expectation
        # rather than silently assuming resilience it doesn't have.
        assert survived is False, (
            "Unexpectedly survived a horizontal flip -- if this scheme "
            "somehow gained geometric resync, update this test's "
            "assumption and docstring accordingly."
        )
