"""
Image Loader Utility Module
===========================

Unified image loading and format handling for watermark processing.

This module provides:
- Multi-format image loading (JPEG, PNG, WebP, AVIF, HEIC)
- Automatic format detection
- Color space conversion
- Image normalization for watermarking
- Metadata extraction and preservation

Features:
---------
- Lazy loading for large images
- Memory-efficient processing
- EXIF orientation handling
- Bit depth normalization

Example:
--------
    >>> from watermark_engine.utils import ImageLoader
    >>>
    >>> loader = ImageLoader()
    >>> image = loader.load("photo.jpg")
    >>>
    >>> print(f"Size: {image.shape}")
    >>> print(f"Format: {loader.get_format('photo.jpg')}")

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImageFormat(str, Enum):
    """Supported image formats."""

    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    AVIF = "avif"
    HEIC = "heic"
    TIFF = "tiff"
    BMP = "bmp"
    UNKNOWN = "unknown"


class ColorSpace(str, Enum):
    """Color space options."""

    RGB = "RGB"
    RGBA = "RGBA"
    GRAYSCALE = "L"
    CMYK = "CMYK"
    LAB = "LAB"
    YCbCr = "YCbCr"


@dataclass
class ImageMetadata:
    """
    Image metadata container.

    Preserves original image metadata for restoration after processing.
    """

    format: ImageFormat
    width: int
    height: int
    channels: int
    bit_depth: int
    color_space: ColorSpace
    has_alpha: bool
    exif: dict[str, Any] | None = None
    icc_profile: bytes | None = None
    dpi: tuple[int, int] | None = None


# Pillow format name -> our ImageFormat enum
_PIL_FORMAT_MAP: dict[str, ImageFormat] = {
    "JPEG": ImageFormat.JPEG,
    "PNG": ImageFormat.PNG,
    "WEBP": ImageFormat.WEBP,
    "AVIF": ImageFormat.AVIF,
    "HEIC": ImageFormat.HEIC,
    "HEIF": ImageFormat.HEIC,
    "TIFF": ImageFormat.TIFF,
    "BMP": ImageFormat.BMP,
}

# Our ImageFormat enum -> Pillow format name (for save())
_FORMAT_TO_PIL: dict[ImageFormat, str] = {
    ImageFormat.JPEG: "JPEG",
    ImageFormat.PNG: "PNG",
    ImageFormat.WEBP: "WEBP",
    ImageFormat.AVIF: "AVIF",
    ImageFormat.HEIC: "HEIF",
    ImageFormat.TIFF: "TIFF",
    ImageFormat.BMP: "BMP",
}

# Formats whose docstring/type-hint contract (ImageFormat enum, EXTENSION_MAP)
# requires support, but which this environment cannot decode/encode because no
# plugin is installed. Kept explicit so failures are loud, not silent.
_UNSUPPORTED_FORMAT_HELP: dict[ImageFormat, str] = {
    ImageFormat.HEIC: (
        "HEIC/HEIF support requires the 'pillow-heif' package, which is not "
        "installed in this environment. Install it (pip install pillow-heif) "
        "and register it via pillow_heif.register_heif_opener() to enable "
        "HEIC loading/saving."
    ),
}


class ImageLoader:
    """
    Unified image loading and processing utility.

    Handles loading images from various sources and formats,
    normalizing them for watermark processing.

    Attributes:
        normalize_color_space: Whether to convert to RGB
        preserve_metadata: Whether to extract and store metadata

    Example:
        >>> loader = ImageLoader()
        >>> image = loader.load("input.jpg")
        >>>
        >>> # Process image...
        >>>
        >>> loader.save(processed, "output.jpg", metadata)
    """

    # Magic bytes for format detection
    FORMAT_SIGNATURES = {
        b"\xff\xd8\xff": ImageFormat.JPEG,
        b"\x89PNG\r\n\x1a\n": ImageFormat.PNG,
        b"RIFF": ImageFormat.WEBP,  # Partial, need to check for WEBP
        b"\x00\x00\x00": ImageFormat.AVIF,  # Partial, need more checks
    }

    # Extension to format mapping
    EXTENSION_MAP = {
        ".jpg": ImageFormat.JPEG,
        ".jpeg": ImageFormat.JPEG,
        ".png": ImageFormat.PNG,
        ".webp": ImageFormat.WEBP,
        ".avif": ImageFormat.AVIF,
        ".heic": ImageFormat.HEIC,
        ".heif": ImageFormat.HEIC,
        ".tiff": ImageFormat.TIFF,
        ".tif": ImageFormat.TIFF,
        ".bmp": ImageFormat.BMP,
    }

    def __init__(
        self,
        normalize_color_space: bool = True,
        preserve_metadata: bool = True,
        target_bit_depth: int = 8
    ) -> None:
        """
        Initialize Image Loader.

        Args:
            normalize_color_space: Convert all images to RGB
            preserve_metadata: Extract and preserve metadata
            target_bit_depth: Target bit depth for normalization
        """
        self.normalize_color_space = normalize_color_space
        self.preserve_metadata = preserve_metadata
        self.target_bit_depth = target_bit_depth

        logger.debug("ImageLoader initialized")

    def load(
        self,
        source: str | Path | BinaryIO | bytes
    ) -> tuple[np.ndarray, ImageMetadata]:
        """
        Load image from various sources.

        Args:
            source: File path, file object, or bytes

        Returns:
            Tuple of (numpy array, metadata)

        Raises:
            ValueError: If format is unsupported
            FileNotFoundError: If file doesn't exist

        Example:
            >>> image, metadata = loader.load("photo.jpg")
            >>> print(f"Shape: {image.shape}, Format: {metadata.format}")
        """
        logger.info(f"Loading image from: {source}")

        if isinstance(source, bytes):
            return self.load_from_bytes(source)

        if isinstance(source, (str, Path)):
            path = Path(source)
            if not path.is_file():
                raise FileNotFoundError(f"Image file not found: {path}")
            with open(path, "rb") as f:
                data = f.read()
            return self._load_from_data(data)

        # Assume file-like / BinaryIO
        data = source.read()
        return self._load_from_data(data)

    def load_from_bytes(
        self,
        data: bytes
    ) -> tuple[np.ndarray, ImageMetadata]:
        """
        Load image from raw bytes.

        Args:
            data: Raw image bytes

        Returns:
            Tuple of (numpy array, metadata)
        """
        logger.info(f"Loading image from bytes: {len(data)} bytes")
        return self._load_from_data(data)

    def _load_from_data(
        self,
        data: bytes
    ) -> tuple[np.ndarray, ImageMetadata]:
        """
        Shared decode path for load()/load_from_bytes(): detect format,
        open with Pillow, extract metadata, and normalize to a numpy array.
        """
        detected_format = self.detect_format(data)
        if detected_format in _UNSUPPORTED_FORMAT_HELP:
            raise ValueError(_UNSUPPORTED_FORMAT_HELP[detected_format])

        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception as exc:  # Pillow raises UnidentifiedImageError, OSError, etc.
            raise ValueError(f"Unable to decode image data: {exc}") from exc

        pil_format = (img.format or "").upper()
        resolved_format = _PIL_FORMAT_MAP.get(pil_format, detected_format)

        metadata = self._extract_metadata(img, resolved_format)

        array = self._to_array(img)

        return array, metadata

    def _extract_metadata(self, img: Image.Image, fmt: ImageFormat) -> ImageMetadata:
        """Extract EXIF/ICC/DPI and structural metadata from an opened Pillow image."""
        width, height = img.size
        mode = img.mode

        has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in img.info
        color_space = self._color_space_from_mode(mode)
        channels = len(mode) if mode != "P" else 1
        bit_depth = self._bit_depth_from_mode(mode)

        exif_dict: dict[str, Any] | None = None
        icc_profile: bytes | None = None
        dpi: tuple[int, int] | None = None

        if self.preserve_metadata:
            try:
                exif = img.getexif()
                if exif:
                    exif_dict = {int(k): v for k, v in exif.items()}
            except Exception as exc:  # pragma: no cover - defensive, Pillow-version dependent
                logger.warning(f"Failed to read EXIF data: {exc}")
                exif_dict = None

            icc_profile = img.info.get("icc_profile")

            raw_dpi = img.info.get("dpi")
            if raw_dpi is not None:
                try:
                    # round(), not int(): Pillow round-trips DPI through a
                    # pixels-per-meter representation for some formats (e.g.
                    # PNG's pHYs chunk), which is lossy enough that plain
                    # truncation turns 300 into 299.
                    dpi = (round(raw_dpi[0]), round(raw_dpi[1]))
                except (TypeError, ValueError, IndexError):
                    dpi = None

        return ImageMetadata(
            format=fmt,
            width=width,
            height=height,
            channels=channels,
            bit_depth=bit_depth,
            color_space=color_space,
            has_alpha=has_alpha,
            exif=exif_dict,
            icc_profile=icc_profile,
            dpi=dpi,
        )

    @staticmethod
    def _color_space_from_mode(mode: str) -> ColorSpace:
        """Map a Pillow image mode string to our ColorSpace enum."""
        mapping = {
            "RGB": ColorSpace.RGB,
            "RGBA": ColorSpace.RGBA,
            "L": ColorSpace.GRAYSCALE,
            "1": ColorSpace.GRAYSCALE,
            "CMYK": ColorSpace.CMYK,
            "LAB": ColorSpace.LAB,
            "YCbCr": ColorSpace.YCbCr,
        }
        if mode in mapping:
            return mapping[mode]
        # Palette ("P") and any other mode: Pillow normalizes to RGB/RGBA on
        # conversion, so treat as RGB for our color-space bookkeeping.
        return ColorSpace.RGB

    @staticmethod
    def _bit_depth_from_mode(mode: str) -> int:
        """Map a Pillow image mode string to a per-channel bit depth."""
        if mode == "1":
            return 1
        if mode in ("I", "I;16", "I;16B", "I;16L", "I;16N"):
            return 16
        if mode == "F":
            return 32
        return 8

    def _to_array(self, img: Image.Image) -> np.ndarray:
        """
        Convert a Pillow image to a numpy array, applying EXIF orientation
        and optional RGB normalization per instance configuration.
        """
        try:
            from PIL import ImageOps

            img = ImageOps.exif_transpose(img) or img
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Failed to apply EXIF orientation: {exc}")

        if self.normalize_color_space and img.mode not in ("RGB", "RGBA"):
            if img.mode in ("LA", "P"):
                img = img.convert("RGBA" if "transparency" in img.info else "RGB")
            else:
                img = img.convert("RGB")

        return np.array(img)

    def save(
        self,
        image: np.ndarray,
        destination: str | Path | BinaryIO,
        metadata: ImageMetadata | None = None,
        format_override: ImageFormat | None = None,
        quality: int = 95
    ) -> bytes:
        """
        Save image to destination.

        Args:
            image: Numpy array of image data
            destination: Output path or file object
            metadata: Metadata to embed
            format_override: Force specific output format
            quality: JPEG/WebP quality (1-100)

        Returns:
            Raw bytes of saved image
        """
        logger.info(f"Saving image to: {destination}")

        pil_image = self._from_array(image)

        target_format = self._resolve_save_format(destination, metadata, format_override)
        if target_format in _UNSUPPORTED_FORMAT_HELP:
            raise ValueError(_UNSUPPORTED_FORMAT_HELP[target_format])

        pil_format_name = _FORMAT_TO_PIL.get(target_format, "PNG")

        save_kwargs: dict[str, Any] = {}
        if pil_format_name in ("JPEG", "WEBP", "AVIF"):
            save_kwargs["quality"] = quality
        # Note: subsampling is intentionally left at Pillow's quality-based
        # default here. Pillow's "keep" subsampling mode only works when
        # re-saving the exact PIL.Image object that was just JPEG-decoded
        # (it checks im.format == "JPEG" internally); save() always rebuilds
        # a fresh Image via Image.fromarray(), which has no such format tag,
        # so "keep" would raise ValueError on every call.

        if metadata is not None:
            if metadata.icc_profile:
                save_kwargs["icc_profile"] = metadata.icc_profile
            if metadata.exif:
                exif = Image.Exif()
                for tag, value in metadata.exif.items():
                    try:
                        exif[int(tag)] = value
                    except (TypeError, ValueError):
                        continue
                save_kwargs["exif"] = exif.tobytes()
            if metadata.dpi:
                save_kwargs["dpi"] = metadata.dpi

        buffer = io.BytesIO()
        pil_image.save(buffer, format=pil_format_name, **save_kwargs)
        raw_bytes = buffer.getvalue()

        if isinstance(destination, (str, Path)):
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw_bytes)
        else:
            destination.write(raw_bytes)

        return raw_bytes

    def _resolve_save_format(
        self,
        destination: str | Path | BinaryIO,
        metadata: ImageMetadata | None,
        format_override: ImageFormat | None,
    ) -> ImageFormat:
        """Determine the output format: explicit override > destination extension > metadata > PNG default."""
        if format_override is not None:
            return format_override

        if isinstance(destination, (str, Path)):
            ext = Path(destination).suffix.lower()
            if ext in self.EXTENSION_MAP:
                return self.EXTENSION_MAP[ext]

        if metadata is not None and metadata.format != ImageFormat.UNKNOWN:
            return metadata.format

        return ImageFormat.PNG

    def _from_array(self, image: np.ndarray) -> Image.Image:
        """Convert a numpy array back into a Pillow Image, normalizing dtype first."""
        array = image
        if array.dtype != np.uint8:
            array = self.to_uint8(array)

        if array.ndim == 2:
            mode = "L"
        elif array.ndim == 3 and array.shape[2] == 3:
            mode = "RGB"
        elif array.ndim == 3 and array.shape[2] == 4:
            mode = "RGBA"
        else:
            raise ValueError(f"Unsupported array shape for image save: {array.shape}")

        return Image.fromarray(array, mode=mode)

    def detect_format(
        self,
        source: str | Path | bytes
    ) -> ImageFormat:
        """
        Detect image format from file or bytes.

        Args:
            source: File path or raw bytes

        Returns:
            Detected ImageFormat
        """
        if isinstance(source, (str, Path)):
            # Try extension first
            ext = Path(source).suffix.lower()
            if ext in self.EXTENSION_MAP:
                return self.EXTENSION_MAP[ext]

            # Fall back to magic-byte sniffing of the file contents.
            try:
                with open(source, "rb") as f:
                    header = f.read(32)
                return self._detect_format_from_bytes(header)
            except OSError:
                return ImageFormat.UNKNOWN

        # Raw bytes: magic-byte detection only.
        return self._detect_format_from_bytes(source[:32])

    @staticmethod
    def _detect_format_from_bytes(header: bytes) -> ImageFormat:
        """
        Detect format from a magic-byte header.

        Handles the straightforward single-signature formats directly from
        FORMAT_SIGNATURES, plus the container formats (WEBP/AVIF/TIFF/BMP/HEIC)
        that need a deeper look than a fixed prefix:

        - WEBP: RIFF????WEBP - the four bytes after the RIFF size field must
          spell "WEBP" (plain "RIFF" alone is ambiguous with other RIFF-based
          containers, e.g. WAV).
        - AVIF/HEIC: ISO base media file format ("ftyp" box) - bytes 4-8 are
          literally "ftyp", followed by a brand identifier that distinguishes
          AVIF ("avif"/"avis") from HEIC ("heic"/"heix"/"hevc"/"mif1"/"msf1").
        - TIFF: little/big-endian byte-order marker ("II*\\0" / "MM\\0*").
        - BMP: "BM" prefix.
        """
        if not header:
            return ImageFormat.UNKNOWN

        # JPEG / PNG: exact, unambiguous prefixes.
        if header.startswith(b"\xff\xd8\xff"):
            return ImageFormat.JPEG
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ImageFormat.PNG

        # BMP
        if header.startswith(b"BM"):
            return ImageFormat.BMP

        # TIFF (little-endian "II*\0" or big-endian "MM\0*")
        if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
            return ImageFormat.TIFF

        # WEBP: RIFF container, need to confirm the "WEBP" fourCC.
        if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
            return ImageFormat.WEBP

        # AVIF/HEIC: ISO base media file format ("ftyp" box at offset 4).
        if len(header) >= 12 and header[4:8] == b"ftyp":
            brand = header[8:12]
            if brand in (b"avif", b"avis"):
                return ImageFormat.AVIF
            if brand in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"):
                return ImageFormat.HEIC

        return ImageFormat.UNKNOWN

    @staticmethod
    def to_float(image: np.ndarray) -> np.ndarray:
        """
        Convert image to float32 [0, 1] range.

        Args:
            image: Input image array

        Returns:
            Normalized float32 array
        """
        if image.dtype == np.float32:
            return image
        if image.dtype == np.uint8:
            return image.astype(np.float32) / 255.0
        if image.dtype == np.uint16:
            return image.astype(np.float32) / 65535.0
        return image.astype(np.float32)

    @staticmethod
    def to_uint8(image: np.ndarray) -> np.ndarray:
        """
        Convert image to uint8 [0, 255] range.

        Args:
            image: Input image array (float or int)

        Returns:
            uint8 array
        """
        if image.dtype == np.uint8:
            return image
        if image.dtype in (np.float32, np.float64):
            return np.clip(image * 255.0, 0, 255).astype(np.uint8)
        if image.dtype == np.uint16:
            return (image >> 8).astype(np.uint8)
        return image.astype(np.uint8)
