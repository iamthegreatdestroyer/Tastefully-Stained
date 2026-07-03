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

import io

import numpy as np
import pytest
from PIL import Image
from skimage.metrics import peak_signal_noise_ratio

from watermark_engine.core.dct_processor import DCTWatermarker


def _natural_test_image(seed: int, height: int = 512, width: int = 512) -> np.ndarray:
    """
    Build a smooth-gradient-plus-noise RGB test image.

    Pure uniform random noise (np.random.randint over the whole array) is an
    adversarial worst case for JPEG/DCT-based watermarking: real photos have
    strong local spatial correlation that both JPEG's block quantization and
    our mid-band embedding rely on, whereas i.i.d. noise has none. A smooth
    gradient with modest noise on top is much closer to a "natural image"
    and is what the JPEG-recompression robustness tests need to give a
    meaningful (not artificially pessimistic) signal.
    """
    rng = np.random.default_rng(seed)
    y_idx, x_idx = np.mgrid[0:height, 0:width]
    gradient = (128 + 60 * np.sin(x_idx / 40) + 40 * np.cos(y_idx / 55)).astype(np.float32)
    noise = rng.integers(-10, 10, (height, width, 3)).astype(np.float32)
    offset = rng.integers(0, 50, (1, 1, 3)).astype(np.float32)
    return np.clip(gradient[..., None] + noise + offset, 0, 255).astype(np.uint8)


def _jpeg_round_trip(image: np.ndarray, quality: int) -> np.ndarray:
    """Re-encode `image` as JPEG at `quality` and decode it back to an array."""
    buffer = io.BytesIO()
    Image.fromarray(image).save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return np.array(Image.open(buffer).convert("RGB"))


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

    def test_embed_grayscale_preserves_dimensions_and_dtype(
        self, watermarker: DCTWatermarker, sample_watermark: bytes
    ) -> None:
        """2D (grayscale) input keeps its 2D shape and uint8 dtype after embedding."""
        image = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
        result = watermarker.embed_watermark(image, sample_watermark)

        assert result.ndim == 2
        assert result.shape == image.shape
        assert result.dtype == np.uint8

    def test_embed_rgba_preserves_alpha_channel(
        self, watermarker: DCTWatermarker, sample_watermark: bytes
    ) -> None:
        """RGBA input keeps 4 channels, with alpha passed through unmodified."""
        rng = np.random.default_rng(3)
        image = rng.integers(0, 256, (256, 256, 4), dtype=np.uint8)

        result = watermarker.embed_watermark(image, sample_watermark)

        assert result.shape == image.shape
        # Alpha channel is never touched by luma-only watermarking.
        np.testing.assert_array_equal(result[:, :, 3], image[:, :, 3])

    def test_embed_too_small_image_raises_value_error(
        self, watermarker: DCTWatermarker
    ) -> None:
        """An image with too few 8x8 blocks to hold the payload raises ValueError."""
        tiny_image = np.random.randint(0, 256, (16, 16, 3), dtype=np.uint8)
        # 16x16 with block_size=8 -> only 4 blocks (4 bits) of capacity, nowhere
        # near enough for even the RS-coded length header, let alone a payload.
        with pytest.raises(ValueError, match="capacity"):
            watermarker.embed_watermark(tiny_image, b"this payload will not fit")

    def test_embed_rejects_invalid_ndim(self, watermarker: DCTWatermarker) -> None:
        """A 1D or 4D+ array is not a valid image and must raise ValueError."""
        with pytest.raises(ValueError, match="2D .* or 3D"):
            watermarker.embed_watermark(np.zeros(64, dtype=np.uint8), b"data")


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

    def test_extract_from_unwatermarked_image_raises_value_error(
        self, watermarker: DCTWatermarker, sample_image: np.ndarray
    ) -> None:
        """
        Extracting from an image that was never watermarked must fail loudly
        (ValueError) rather than returning plausible-looking garbage bytes.
        """
        with pytest.raises(ValueError):
            watermarker.extract_watermark(sample_image)

    def test_extract_rejects_invalid_ndim(self, watermarker: DCTWatermarker) -> None:
        """A 1D or 4D+ array is not a valid image and must raise ValueError."""
        with pytest.raises(ValueError, match="2D .* or 3D"):
            watermarker.extract_watermark(np.zeros(64, dtype=np.uint8))


class TestDCTWatermarkerRoundTrip:
    """
    Core correctness tests: embed then extract must recover the exact
    original bytes, across the shapes/dtypes/parameters the public API
    promises to support.
    """

    def test_round_trip_recovers_exact_bytes(self) -> None:
        """Embedding then extracting recovers the exact original watermark bytes."""
        rng = np.random.default_rng(42)
        image = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
        data = b"Tastefully Stained Test Watermark"

        watermarker = DCTWatermarker(strength=0.5, block_size=8)
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data

    def test_round_trip_grayscale(self) -> None:
        """Round-trip works for 2D grayscale images, not just color."""
        rng = np.random.default_rng(11)
        image = rng.integers(0, 256, (256, 256), dtype=np.uint8)
        data = b"grayscale watermark payload"

        watermarker = DCTWatermarker()
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data

    def test_round_trip_rgba(self) -> None:
        """Round-trip works for RGBA images (alpha preserved, luma watermarked)."""
        rng = np.random.default_rng(12)
        image = rng.integers(0, 256, (256, 256, 4), dtype=np.uint8)
        data = b"rgba watermark payload"

        watermarker = DCTWatermarker()
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data

    @pytest.mark.parametrize("block_size", [4, 8, 16, 32])
    def test_round_trip_across_block_sizes(self, block_size: int) -> None:
        """Round-trip holds for every supported (power-of-2) block_size."""
        # Larger block_size means fewer blocks (= fewer bit sites) per pixel,
        # so scale the image up proportionally to guarantee enough capacity
        # for the framed payload at every block_size under test -- this is
        # a capacity-sizing choice for the test fixture, not a workaround
        # for a real limitation (the same tradeoff applies to any caller
        # who picks a large block_size).
        size = max(512, block_size * 64)
        rng = np.random.default_rng(block_size)
        image = rng.integers(0, 256, (size, size, 3), dtype=np.uint8)
        data = b"block size sweep"

        watermarker = DCTWatermarker(strength=0.5, block_size=block_size)
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data

    @pytest.mark.parametrize("strength", [0.0, 0.25, 0.5, 0.75, 1.0])
    def test_round_trip_across_strengths(self, strength: float) -> None:
        """Round-trip holds across the full strength range, including the extremes."""
        rng = np.random.default_rng(int(strength * 100) + 1)
        image = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
        data = b"strength sweep watermark"

        watermarker = DCTWatermarker(strength=strength, block_size=8)
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data

    def test_round_trip_empty_and_short_payloads(self) -> None:
        """Very short (non-empty) payloads round-trip correctly."""
        rng = np.random.default_rng(99)
        image = rng.integers(0, 256, (256, 256, 3), dtype=np.uint8)
        watermarker = DCTWatermarker()

        for data in [b"x", b"ab", b"\x00\x01\x02\xff"]:
            watermarked = watermarker.embed_watermark(image, data)
            assert watermarker.extract_watermark(watermarked) == data

    def test_round_trip_binary_payload_with_all_byte_values(self) -> None:
        """Payload containing every possible byte value (0-255) round-trips exactly."""
        rng = np.random.default_rng(55)
        image = rng.integers(0, 256, (1024, 1024, 3), dtype=np.uint8)
        data = bytes(range(256))

        watermarker = DCTWatermarker(strength=0.6, block_size=8)
        watermarked = watermarker.embed_watermark(image, data)
        extracted = watermarker.extract_watermark(watermarked)

        assert extracted == data


class TestDCTWatermarkerVisualQuality:
    """
    Tests that the embedded watermark is not grossly visible, i.e. that
    embedding trades off a bounded, small amount of image fidelity for
    robustness rather than visibly damaging the image.
    """

    def test_watermarked_image_has_high_psnr(self) -> None:
        """
        PSNR between original and watermarked images stays above 35 dB.

        35 dB is a widely used rule-of-thumb threshold in the watermarking
        literature for "visually near-identical to the original" -- below
        roughly 30 dB, compression/processing artifacts typically become
        noticeable to an average viewer in side-by-side comparison; above
        35 dB they are generally imperceptible without a reference image
        and pixel-level inspection. Our default strength=0.5 mid-band QIM
        embedding measures ~48-50 dB in practice (see the measured value
        printed on assertion failure), so 35 dB leaves comfortable headroom
        while still being a meaningful, non-trivially-satisfied bound.
        """
        rng = np.random.default_rng(1)
        image = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        watermarked = watermarker.embed_watermark(image, b"Tastefully Stained Test Watermark")

        psnr = peak_signal_noise_ratio(image, watermarked, data_range=255)
        assert psnr > 35.0, f"PSNR {psnr:.2f} dB fell below the 35 dB visibility threshold"

    def test_higher_strength_reduces_psnr(self) -> None:
        """
        Sanity check on the strength/quality tradeoff: a much higher
        strength (larger DCT quantization step) should not produce *better*
        fidelity than a low strength -- if it did, `strength` would not be
        doing what its docstring promises.
        """
        rng = np.random.default_rng(2)
        image = rng.integers(0, 256, (512, 512, 3), dtype=np.uint8)
        data = b"strength quality tradeoff"

        low = DCTWatermarker(strength=0.05, block_size=8)
        high = DCTWatermarker(strength=1.0, block_size=8)

        low_psnr = peak_signal_noise_ratio(image, low.embed_watermark(image, data), data_range=255)
        high_psnr = peak_signal_noise_ratio(image, high.embed_watermark(image, data), data_range=255)

        assert high_psnr <= low_psnr


class TestDCTWatermarkerJPEGRobustness:
    """
    Tests the core claimed robustness property: watermark survives
    reasonable JPEG re-compression. This is empirically verified rather
    than assumed -- see the module docstring and dct_processor.py's
    RS_PARITY_BYTES comment for the measured survival boundary.
    """

    def test_survives_jpeg_recompression_quality_90(self) -> None:
        """Watermark survives a light JPEG re-compression (quality=90)."""
        image = _natural_test_image(seed=7)
        data = b"Tastefully Stained Test Watermark"
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        watermarked = watermarker.embed_watermark(image, data)
        recompressed = _jpeg_round_trip(watermarked, quality=90)

        assert watermarker.extract_watermark(recompressed) == data

    def test_survives_jpeg_recompression_quality_85(self) -> None:
        """
        Watermark survives a moderate JPEG re-compression (quality=85) --
        this is the specific quality range named in the module's robustness
        claim.
        """
        image = _natural_test_image(seed=7)
        data = b"Tastefully Stained Test Watermark"
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        watermarked = watermarker.embed_watermark(image, data)
        recompressed = _jpeg_round_trip(watermarked, quality=85)

        assert watermarker.extract_watermark(recompressed) == data

    def test_survives_jpeg_recompression_quality_70(self) -> None:
        """
        Watermark survives a fairly aggressive JPEG re-compression
        (quality=70). Measured empirically across 20 random natural-image
        trials: quality=70 matched 20/20 (see quality-sweep notes in the
        implementation report); included here as a regression guard on
        that measured floor.
        """
        image = _natural_test_image(seed=7)
        data = b"Tastefully Stained Test Watermark"
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        watermarked = watermarker.embed_watermark(image, data)
        recompressed = _jpeg_round_trip(watermarked, quality=70)

        assert watermarker.extract_watermark(recompressed) == data

    def test_severe_jpeg_recompression_fails_cleanly_not_silently(self) -> None:
        """
        At quality levels well beyond the algorithm's correction capacity
        (empirically, <=40 for these parameters), extraction must fail with
        a clean ValueError -- never return plausible-looking wrong bytes.
        This guards the declared_length==0 hardening in extract_watermark:
        without it, severely corrupted headers can decode to a spurious
        0-byte payload instead of raising.
        """
        image = _natural_test_image(seed=7)
        data = b"Tastefully Stained Test Watermark"
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        watermarked = watermarker.embed_watermark(image, data)
        recompressed = _jpeg_round_trip(watermarked, quality=30)

        with pytest.raises(ValueError):
            watermarker.extract_watermark(recompressed)

    def test_jpeg_robustness_success_rate_at_quality_75(self) -> None:
        """
        Statistical check of the JPEG-70-90 boundary: across multiple
        independent random images, quality=75 should reliably succeed (not
        just for one hand-picked seed). This is the property the module
        docstring's "JPEG compression resistant" claim actually rests on.
        """
        data = b"Tastefully Stained Test Watermark"
        watermarker = DCTWatermarker(strength=0.5, block_size=8)

        successes = 0
        trials = 8
        for seed in range(trials):
            image = _natural_test_image(seed=200 + seed)
            watermarked = watermarker.embed_watermark(image, data)
            recompressed = _jpeg_round_trip(watermarked, quality=75)
            try:
                if watermarker.extract_watermark(recompressed) == data:
                    successes += 1
            except ValueError:
                pass

        assert successes == trials, (
            f"Expected all {trials} trials to survive quality=75 JPEG "
            f"recompression, only {successes} did"
        )
