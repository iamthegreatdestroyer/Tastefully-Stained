"""
Image Loader Tests
==================

Comprehensive tests for the multi-format image loading utility.

Coverage targets:
- Format detection (extension + magic bytes)
- Load/save round-trip for each supported format
- EXIF/ICC/DPI metadata preservation
- Loading from paths, bytes, and file-like objects
- Error handling for missing files and unsupported formats

Run: pytest backend/tests/test_image_loader.py -v
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from watermark_engine.utils.image_loader import (
    ColorSpace,
    ImageFormat,
    ImageLoader,
    ImageMetadata,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def loader() -> ImageLoader:
    """Default-configured ImageLoader instance."""
    return ImageLoader()


@pytest.fixture
def solid_color_image() -> Image.Image:
    """A small solid-color RGB Pillow image, cheap and deterministic."""
    return Image.new("RGB", (32, 24), color=(200, 50, 100))


@pytest.fixture
def rgba_pattern_image() -> Image.Image:
    """A small RGBA image with a simple pattern (not solid, exercises alpha)."""
    img = Image.new("RGBA", (20, 20), color=(0, 0, 0, 0))
    for x in range(20):
        for y in range(20):
            img.putpixel((x, y), ((x * 12) % 256, (y * 12) % 256, 128, 255 if x > y else 0))
    return img


@pytest.fixture
def png_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def jpeg_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


@pytest.fixture
def webp_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="WEBP", quality=95)
    return buf.getvalue()


@pytest.fixture
def avif_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="AVIF", quality=80)
    return buf.getvalue()


@pytest.fixture
def bmp_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="BMP")
    return buf.getvalue()


@pytest.fixture
def tiff_bytes(solid_color_image: Image.Image) -> bytes:
    buf = io.BytesIO()
    solid_color_image.save(buf, format="TIFF")
    return buf.getvalue()


@pytest.fixture
def png_with_exif_and_dpi_path(tmp_path: Path, rgba_pattern_image: Image.Image) -> Path:
    """A PNG on disk carrying EXIF tags and a DPI value, for round-trip checks.

    Note: PNG EXIF support in Pillow is a real but narrower path than JPEG's;
    we round-trip through JPEG here for the EXIF-preservation assertions and
    use this fixture only for DPI, to avoid coupling the test to Pillow's
    PNG eXIf chunk quirks across versions.
    """
    path = tmp_path / "sample.png"
    rgba_pattern_image.convert("RGB").save(path, format="PNG", dpi=(300, 300))
    return path


@pytest.fixture
def jpeg_with_exif_path(tmp_path: Path, solid_color_image: Image.Image) -> Path:
    """A JPEG on disk carrying real EXIF tags, for metadata round-trip checks."""
    path = tmp_path / "sample_exif.jpg"
    exif = Image.Exif()
    exif[0x0112] = 1  # Orientation
    exif[0x010F] = "TastefullyStainedTestCam"  # Make
    solid_color_image.save(path, format="JPEG", exif=exif.tobytes(), dpi=(150, 150))
    return path


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------


class TestDetectFormat:
    """Tests for ImageLoader.detect_format across extensions and magic bytes."""

    @pytest.mark.parametrize(
        "ext,expected",
        [
            (".jpg", ImageFormat.JPEG),
            (".jpeg", ImageFormat.JPEG),
            (".png", ImageFormat.PNG),
            (".webp", ImageFormat.WEBP),
            (".avif", ImageFormat.AVIF),
            (".tiff", ImageFormat.TIFF),
            (".tif", ImageFormat.TIFF),
            (".bmp", ImageFormat.BMP),
            (".heic", ImageFormat.HEIC),
        ],
    )
    def test_detect_by_extension(self, loader: ImageLoader, ext: str, expected: ImageFormat) -> None:
        assert loader.detect_format(f"some/path/file{ext}") == expected

    def test_detect_unknown_extension_falls_back_to_unknown_for_bad_bytes(self, loader: ImageLoader) -> None:
        assert loader.detect_format(b"not an image at all") == ImageFormat.UNKNOWN

    def test_detect_png_by_magic_bytes(self, loader: ImageLoader, png_bytes: bytes) -> None:
        assert loader.detect_format(png_bytes) == ImageFormat.PNG

    def test_detect_jpeg_by_magic_bytes(self, loader: ImageLoader, jpeg_bytes: bytes) -> None:
        assert loader.detect_format(jpeg_bytes) == ImageFormat.JPEG

    def test_detect_webp_by_magic_bytes(self, loader: ImageLoader, webp_bytes: bytes) -> None:
        assert loader.detect_format(webp_bytes) == ImageFormat.WEBP

    def test_detect_avif_by_magic_bytes(self, loader: ImageLoader, avif_bytes: bytes) -> None:
        assert loader.detect_format(avif_bytes) == ImageFormat.AVIF

    def test_detect_bmp_by_magic_bytes(self, loader: ImageLoader, bmp_bytes: bytes) -> None:
        assert loader.detect_format(bmp_bytes) == ImageFormat.BMP

    def test_detect_tiff_by_magic_bytes(self, loader: ImageLoader, tiff_bytes: bytes) -> None:
        assert loader.detect_format(tiff_bytes) == ImageFormat.TIFF

    def test_riff_without_webp_fourcc_is_not_misdetected(self, loader: ImageLoader) -> None:
        """A RIFF container that isn't WEBP (e.g. a WAV-like header) must not
        be misdetected as WEBP just because it starts with 'RIFF'."""
        fake_wav_header = b"RIFF" + b"\x24\x00\x00\x00" + b"WAVEfmt "
        assert loader.detect_format(fake_wav_header) != ImageFormat.WEBP

    def test_detect_from_path_reads_magic_bytes_when_no_extension(
        self, loader: ImageLoader, tmp_path: Path, png_bytes: bytes
    ) -> None:
        path = tmp_path / "no_extension_file"
        path.write_bytes(png_bytes)
        assert loader.detect_format(path) == ImageFormat.PNG

    def test_detect_missing_path_returns_unknown_not_raise(self, loader: ImageLoader, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist_at_all"
        assert loader.detect_format(missing) == ImageFormat.UNKNOWN


# ---------------------------------------------------------------------------
# load() / load_from_bytes() - round trip per format
# ---------------------------------------------------------------------------


class TestLoadRoundTrip:
    """Load real encoded bytes for each supported format and verify the
    returned (array, metadata) contract."""

    def test_load_png_from_bytes(self, loader: ImageLoader, png_bytes: bytes, solid_color_image: Image.Image) -> None:
        array, metadata = loader.load_from_bytes(png_bytes)

        assert isinstance(array, np.ndarray)
        assert isinstance(metadata, ImageMetadata)
        assert metadata.format == ImageFormat.PNG
        assert metadata.width == solid_color_image.width
        assert metadata.height == solid_color_image.height
        assert array.shape[:2] == (solid_color_image.height, solid_color_image.width)

    def test_load_jpeg_from_bytes(self, loader: ImageLoader, jpeg_bytes: bytes) -> None:
        array, metadata = loader.load_from_bytes(jpeg_bytes)
        assert metadata.format == ImageFormat.JPEG
        assert metadata.color_space == ColorSpace.RGB
        assert array.ndim == 3
        assert array.shape[2] == 3

    def test_load_webp_from_bytes(self, loader: ImageLoader, webp_bytes: bytes) -> None:
        array, metadata = loader.load_from_bytes(webp_bytes)
        assert metadata.format == ImageFormat.WEBP
        assert isinstance(array, np.ndarray)

    def test_load_avif_from_bytes(self, loader: ImageLoader, avif_bytes: bytes) -> None:
        array, metadata = loader.load_from_bytes(avif_bytes)
        assert metadata.format == ImageFormat.AVIF
        assert isinstance(array, np.ndarray)

    def test_load_bmp_from_bytes(self, loader: ImageLoader, bmp_bytes: bytes) -> None:
        array, metadata = loader.load_from_bytes(bmp_bytes)
        assert metadata.format == ImageFormat.BMP

    def test_load_tiff_from_bytes(self, loader: ImageLoader, tiff_bytes: bytes) -> None:
        array, metadata = loader.load_from_bytes(tiff_bytes)
        assert metadata.format == ImageFormat.TIFF

    def test_load_rgba_preserves_alpha_channel(
        self, loader: ImageLoader, rgba_pattern_image: Image.Image
    ) -> None:
        buf = io.BytesIO()
        rgba_pattern_image.save(buf, format="PNG")
        array, metadata = loader.load_from_bytes(buf.getvalue())

        assert metadata.has_alpha is True
        assert array.shape[2] == 4

    def test_load_from_path(self, loader: ImageLoader, tmp_path: Path, png_bytes: bytes) -> None:
        path = tmp_path / "on_disk.png"
        path.write_bytes(png_bytes)

        array, metadata = loader.load(path)

        assert metadata.format == ImageFormat.PNG
        assert isinstance(array, np.ndarray)

    def test_load_from_path_string(self, loader: ImageLoader, tmp_path: Path, png_bytes: bytes) -> None:
        path = tmp_path / "on_disk_str.png"
        path.write_bytes(png_bytes)

        array, metadata = loader.load(str(path))

        assert metadata.format == ImageFormat.PNG

    def test_load_from_file_object(self, loader: ImageLoader, png_bytes: bytes) -> None:
        file_obj = io.BytesIO(png_bytes)

        array, metadata = loader.load(file_obj)

        assert metadata.format == ImageFormat.PNG
        assert isinstance(array, np.ndarray)

    def test_load_bytes_via_load_dispatches_to_load_from_bytes(
        self, loader: ImageLoader, png_bytes: bytes
    ) -> None:
        array, metadata = loader.load(png_bytes)
        assert metadata.format == ImageFormat.PNG

    def test_load_missing_file_raises_file_not_found(self, loader: ImageLoader, tmp_path: Path) -> None:
        missing = tmp_path / "nope.png"
        with pytest.raises(FileNotFoundError):
            loader.load(missing)

    def test_load_garbage_bytes_raises_value_error(self, loader: ImageLoader) -> None:
        with pytest.raises(ValueError):
            loader.load_from_bytes(b"this is definitely not an image")

    def test_load_heic_raises_clear_value_error_not_silent_skip(self, loader: ImageLoader) -> None:
        """HEIC has no decode support installed in this environment (no
        pillow-heif). The stub's contract lists HEIC as a supported format,
        so callers must get an explicit, actionable error rather than a
        silently wrong result."""
        fake_heic_header = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 16
        with pytest.raises(ValueError, match="pillow-heif"):
            loader.load_from_bytes(fake_heic_header)


# ---------------------------------------------------------------------------
# save() - round trip per format
# ---------------------------------------------------------------------------


class TestSaveRoundTrip:
    """Save numpy arrays back out and verify the bytes/format/metadata survive."""

    def test_save_png_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.png"

        raw = loader.save(sample_rgb_image, dest)

        assert dest.exists()
        assert dest.read_bytes() == raw
        reloaded = Image.open(dest)
        assert reloaded.format == "PNG"
        assert reloaded.size == (sample_rgb_image.shape[1], sample_rgb_image.shape[0])

    def test_save_jpeg_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.jpg"

        loader.save(sample_rgb_image, dest, quality=90)

        reloaded = Image.open(dest)
        assert reloaded.format == "JPEG"

    def test_save_webp_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.webp"

        loader.save(sample_rgb_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.format == "WEBP"

    def test_save_avif_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.avif"

        loader.save(sample_rgb_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.format == "AVIF"

    def test_save_bmp_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.bmp"

        loader.save(sample_rgb_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.format == "BMP"

    def test_save_tiff_to_path(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.tiff"

        loader.save(sample_rgb_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.format == "TIFF"

    def test_save_grayscale_array(self, loader: ImageLoader, tmp_path: Path, sample_grayscale_image: np.ndarray) -> None:
        dest = tmp_path / "gray.png"

        loader.save(sample_grayscale_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.mode == "L"

    def test_save_rgba_array_preserves_alpha(self, loader: ImageLoader, tmp_path: Path, sample_rgba_image: np.ndarray) -> None:
        dest = tmp_path / "rgba.png"

        loader.save(sample_rgba_image, dest)

        reloaded = Image.open(dest)
        assert reloaded.mode == "RGBA"

    def test_save_format_override_takes_precedence_over_extension(
        self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray
    ) -> None:
        # Extension says .png but override forces JPEG bytes underneath.
        dest = tmp_path / "tricky.png"

        raw = loader.save(sample_rgb_image, dest, format_override=ImageFormat.JPEG)

        assert raw.startswith(b"\xff\xd8\xff")

    def test_save_no_extension_defaults_to_png(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "no_ext_output"

        raw = loader.save(sample_rgb_image, dest)

        assert raw.startswith(b"\x89PNG\r\n\x1a\n")

    def test_save_to_file_object(self, loader: ImageLoader, sample_rgb_image: np.ndarray) -> None:
        buf = io.BytesIO()

        raw = loader.save(sample_rgb_image, buf)

        assert buf.getvalue() == raw
        buf.seek(0)
        reloaded = Image.open(buf)
        assert reloaded.format == "PNG"

    def test_save_creates_parent_directories(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "nested" / "dirs" / "out.png"

        loader.save(sample_rgb_image, dest)

        assert dest.exists()

    def test_save_heic_raises_clear_value_error(self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray) -> None:
        dest = tmp_path / "out.heic"
        with pytest.raises(ValueError, match="pillow-heif"):
            loader.save(sample_rgb_image, dest)


# ---------------------------------------------------------------------------
# Full round trip: load -> save -> load again, verifying metadata survival
# ---------------------------------------------------------------------------


class TestFullRoundTrip:
    """End-to-end: load an image, save it back out, reload, and confirm
    format/dimensions/metadata all survive the trip."""

    def test_png_dpi_round_trip(self, loader: ImageLoader, png_with_exif_and_dpi_path: Path, tmp_path: Path) -> None:
        array, metadata = loader.load(png_with_exif_and_dpi_path)
        assert metadata.dpi == (300, 300)

        out_path = tmp_path / "roundtrip.png"
        loader.save(array, out_path, metadata=metadata)

        array2, metadata2 = loader.load(out_path)
        assert metadata2.format == ImageFormat.PNG
        assert metadata2.width == metadata.width
        assert metadata2.height == metadata.height
        assert metadata2.dpi == (300, 300)
        assert array2.shape == array.shape

    def test_jpeg_exif_round_trip(self, loader: ImageLoader, jpeg_with_exif_path: Path, tmp_path: Path) -> None:
        array, metadata = loader.load(jpeg_with_exif_path)

        assert metadata.exif is not None
        assert metadata.exif.get(0x010F) == "TastefullyStainedTestCam"
        assert metadata.dpi == (150, 150)

        out_path = tmp_path / "roundtrip_exif.jpg"
        loader.save(array, out_path, metadata=metadata)

        _, metadata2 = loader.load(out_path)
        assert metadata2.exif is not None
        assert metadata2.exif.get(0x010F) == "TastefullyStainedTestCam"

    def test_icc_profile_round_trip(self, loader: ImageLoader, tmp_path: Path, solid_color_image: Image.Image) -> None:
        # Minimal but structurally-plausible fake ICC payload is not required;
        # Pillow treats icc_profile as an opaque blob it writes/reads verbatim,
        # so any bytes exercise the preservation path faithfully.
        fake_icc = b"FAKEICCPROFILEDATA" * 4
        src_path = tmp_path / "with_icc.png"
        solid_color_image.save(src_path, format="PNG", icc_profile=fake_icc)

        array, metadata = loader.load(src_path)
        assert metadata.icc_profile == fake_icc

        out_path = tmp_path / "with_icc_out.png"
        loader.save(array, out_path, metadata=metadata)

        _, metadata2 = loader.load(out_path)
        assert metadata2.icc_profile == fake_icc

    @pytest.mark.parametrize("fmt_ext", ["png", "jpg", "webp", "bmp", "tiff", "avif"])
    def test_dimensions_survive_round_trip_all_formats(
        self, loader: ImageLoader, tmp_path: Path, sample_rgb_image: np.ndarray, fmt_ext: str
    ) -> None:
        out_path = tmp_path / f"dims.{fmt_ext}"

        loader.save(sample_rgb_image, out_path)
        array2, metadata2 = loader.load(out_path)

        assert metadata2.width == sample_rgb_image.shape[1]
        assert metadata2.height == sample_rgb_image.shape[0]
        assert array2.shape[:2] == sample_rgb_image.shape[:2]


# ---------------------------------------------------------------------------
# to_float / to_uint8 - pre-existing helpers, sanity-checked (not reimplemented)
# ---------------------------------------------------------------------------


class TestConversionHelpersUnchanged:
    """Light smoke coverage for the already-implemented static helpers, to
    confirm Phase 1 work did not regress them."""

    def test_to_float_from_uint8(self) -> None:
        arr = np.array([0, 128, 255], dtype=np.uint8)
        result = ImageLoader.to_float(arr)
        assert result.dtype == np.float32
        assert result.max() <= 1.0

    def test_to_uint8_from_float(self) -> None:
        arr = np.array([0.0, 0.5, 1.0], dtype=np.float32)
        result = ImageLoader.to_uint8(arr)
        assert result.dtype == np.uint8
        assert result.max() == 255
