"""
DCT (Discrete Cosine Transform) Watermarking Module
====================================================

Production-grade DCT watermarking implementation for JPEG-resistant
invisible watermarks.

This module implements frequency-domain watermarking using the Discrete
Cosine Transform, which embeds watermark data in the DCT coefficients
of image blocks.

Features:
---------
- JPEG compression resistant watermarking
- Bit-by-bit embedding in frequency domain
- Error correction using Reed-Solomon codes
- Adaptive strength based on image content
- Full type hints and documentation

Example:
--------
    >>> from watermark_engine.core.dct_processor import DCTWatermarker
    >>> import numpy as np
    >>>
    >>> watermarker = DCTWatermarker(strength=0.5, block_size=8)
    >>> image = np.random.randint(0, 256, (512, 512, 3), dtype=np.uint8)
    >>> watermark_data = b"Tastefully Stained Watermark"
    >>>
    >>> watermarked = watermarker.embed_watermark(image, watermark_data)
    >>> extracted = watermarker.extract_watermark(watermarked)

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import logging
import struct
from typing import TYPE_CHECKING

import cv2
import numpy as np
import reedsolo

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Wire-format / algorithm constants
# ---------------------------------------------------------------------------

# Reed-Solomon parity symbols (bytes) for the watermark *payload* block.
# RSCodec can correct up to floor(nsym / 2) corrupted bytes per 255-byte
# coded chunk. 20 parity bytes -> up to 10 corrupted bytes recoverable per
# chunk, which comfortably covers the handful of bit-flips that JPEG
# requantization at quality>=70 introduces into a payload of a few dozen
# bytes (see the JPEG round-trip test for the empirically measured survival
# threshold).
RS_PARITY_BYTES = 20

# Reed-Solomon parity symbols for the length *header* block. This is
# deliberately a separate, independent RS codeword from the payload (see
# the framing note below) rather than a smaller slice of it.
RS_HEADER_PARITY_BYTES = 8

# The wire format is two independently Reed-Solomon-encoded blocks placed
# back to back in the bitstream:
#
#   [ RS(length_prefix, RS_HEADER_PARITY_BYTES) ][ RS(watermark_data, RS_PARITY_BYTES) ]
#
# This is *not* "RS-encode a single length+data message and read a prefix of
# it": Reed-Solomon parity symbols are computed over the entire codeword, so
# a truncated prefix of one big RS(length+data) codeword is not a valid,
# independently-decodable codeword on its own -- attempting to RS-decode
# just the first N bytes of a longer encoded message reliably raises
# ReedSolomonError, it does not degrade gracefully. Framing the length as
# its own small RS block (fixed, known-in-advance size:
# _LENGTH_PREFIX_SIZE + RS_HEADER_PARITY_BYTES bytes) makes it safe to
# extract_watermark() the header alone -- before the payload's length (and
# therefore its encoded size) is even known -- then separately decode the
# payload block once its size can be computed.
_LENGTH_PREFIX_FORMAT = ">I"
_LENGTH_PREFIX_SIZE = struct.calcsize(_LENGTH_PREFIX_FORMAT)
_HEADER_FRAME_SIZE = _LENGTH_PREFIX_SIZE + RS_HEADER_PARITY_BYTES

# Zig-zag-adjacent mid-frequency coefficient position (row, col) within each
# block, used as the single embedding site per block.
#
# Rationale for (3, 3) at block_size=8 (scaled proportionally for other
# block sizes, see _midband_position()):
# - Low frequencies (near (0, 0), including DC) carry most of a block's
#   visible energy; perturbing them shows up as visible blockiness/blur.
# - High frequencies (near (block_size-1, block_size-1)) are exactly what
#   JPEG quantization tables discard most aggressively -- a bit hidden there
#   is usually the first thing compression destroys.
# - Mid-band coefficients are the classic compromise: perceptually
#   inexpensive to modify (Watson/Hernandez-style visual masking is
#   strongest for the eye in this band) while surviving JPEG's quantization
#   tables at moderate-to-high quality, since those tables assign mid-band
#   entries a *moderate* (not tiny, not huge) quantization step.
_DEFAULT_MIDBAND_FRACTION = (3.0 / 8.0, 3.0 / 8.0)

# Minimum block size for which the fixed mid-band heuristic remains sane.
# Below 4x4 there isn't a meaningful "mid" band distinct from DC/high-freq.
_MIN_BLOCK_SIZE = 4


class DCTWatermarker:
    """
    DCT-based watermarking implementation.

    This class provides methods to embed and extract watermarks using
    Discrete Cosine Transform in the frequency domain.

    Attributes:
        strength (float): Watermark embedding strength (0.0-1.0)
        block_size (int): Size of DCT blocks (typically 8x8)

    Example:
        >>> watermarker = DCTWatermarker(strength=0.5)
        >>> watermarked = watermarker.embed_watermark(image, b"data")
    """

    def __init__(self, strength: float = 0.5, block_size: int = 8) -> None:
        """
        Initialize DCT Watermarker.

        Args:
            strength: Watermark embedding strength (0.0-1.0). Higher values
                     increase robustness but may affect image quality.
            block_size: Size of DCT blocks. Default is 8 for JPEG compatibility.

        Raises:
            ValueError: If strength is not in range [0.0, 1.0]
            ValueError: If block_size is not a power of 2
        """
        if not 0.0 <= strength <= 1.0:
            raise ValueError(f"Strength must be in range [0.0, 1.0], got {strength}")
        if block_size & (block_size - 1) != 0:
            raise ValueError(f"Block size must be a power of 2, got {block_size}")

        self.strength = strength
        self.block_size = block_size
        logger.info(f"DCTWatermarker initialized: strength={strength}, block_size={block_size}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_watermark(
        self,
        image: NDArray[np.uint8],
        watermark_data: bytes
    ) -> NDArray[np.uint8]:
        """
        Embed watermark data into an image using DCT.

        Args:
            image: Input image as numpy array (H, W, C) or (H, W)
            watermark_data: Binary data to embed as watermark

        Returns:
            Watermarked image as numpy array

        Raises:
            ValueError: If image dimensions are too small for watermarking

        Example:
            >>> watermarked = watermarker.embed_watermark(image, b"secret")
        """
        logger.info(f"Embedding watermark: {len(watermark_data)} bytes")

        if image.ndim not in (2, 3):
            raise ValueError(
                f"Image must be 2D (grayscale) or 3D (H, W, C), got shape {image.shape}"
            )

        bitstream = self._encode_payload_to_bits(watermark_data)

        luma, chroma = self._split_luma(image)
        capacity_bits = self._capacity_bits(luma.shape)
        if len(bitstream) > capacity_bits:
            raise ValueError(
                f"Image dimensions {luma.shape} provide capacity for "
                f"{capacity_bits} bits ({capacity_bits // 8} bytes after RS/framing "
                f"overhead), but {len(watermark_data)} bytes of watermark data "
                f"require {len(bitstream)} bits. Use a larger image, a smaller "
                f"watermark payload, or a smaller block_size."
            )

        watermarked_luma = self._embed_bits_in_channel(luma, bitstream)
        watermarked_image = self._merge_luma(watermarked_luma, chroma, image)

        logger.info(
            f"Watermark embedded: {len(bitstream)} bits across "
            f"{capacity_bits} available block sites"
        )
        return watermarked_image

    def extract_watermark(self, image: NDArray[np.uint8]) -> bytes:
        """
        Extract watermark data from a watermarked image.

        Args:
            image: Watermarked image as numpy array

        Returns:
            Extracted watermark data as bytes

        Raises:
            ValueError: If no watermark is detected

        Example:
            >>> data = watermarker.extract_watermark(watermarked_image)
        """
        logger.info("Extracting watermark from image")

        if image.ndim not in (2, 3):
            raise ValueError(
                f"Image must be 2D (grayscale) or 3D (H, W, C), got shape {image.shape}"
            )

        luma, _ = self._split_luma(image)
        capacity_bits = self._capacity_bits(luma.shape)

        # Phase 1: read the fixed-size, independently RS-coded header block
        # to recover the payload length. This block's size never depends on
        # the payload, so it can always be read/decoded before anything else
        # is known (see the wire-format note above _LENGTH_PREFIX_FORMAT).
        header_bits_needed = _HEADER_FRAME_SIZE * 8
        if capacity_bits < header_bits_needed:
            raise ValueError(
                f"Image dimensions {luma.shape} provide only {capacity_bits} "
                f"watermark bit sites, fewer than the {header_bits_needed} "
                "needed just to read a length header. No watermark can be "
                "present/extracted from an image this small."
            )

        header_bits = self._extract_bits_from_channel(luma, header_bits_needed)
        header_frame = self._bits_to_bytes(header_bits)

        header_rsc = reedsolo.RSCodec(RS_HEADER_PARITY_BYTES)
        try:
            header_decoded, _, _ = header_rsc.decode(header_frame)
        except reedsolo.ReedSolomonError as exc:
            raise ValueError(
                "No watermark detected: Reed-Solomon decoding of the length "
                f"header failed ({exc}). The image may be unwatermarked, "
                "watermarked with different parameters, or too badly degraded."
            ) from exc

        if len(header_decoded) != _LENGTH_PREFIX_SIZE:
            raise ValueError(
                "No watermark detected: decoded header size "
                f"({len(header_decoded)} bytes) does not match the expected "
                f"length prefix size ({_LENGTH_PREFIX_SIZE} bytes)."
            )

        (declared_length,) = struct.unpack(_LENGTH_PREFIX_FORMAT, bytes(header_decoded))

        # A declared length of exactly 0 is never produced by a real
        # embedded watermark (embed_watermark always frames at least the
        # 4-byte length prefix around a non-empty caller payload -- this
        # class does not support embedding an empty watermark). In
        # practice it is the signature of Reed-Solomon "successfully"
        # decoding a header block whose corruption exceeded its correction
        # capacity (floor(RS_HEADER_PARITY_BYTES / 2) = 4 bytes): bounded-
        # distance RS decoding is only *guaranteed* correct below that
        # error count: above it, decode() does not reliably raise, it can
        # converge on an internally-consistent but wrong codeword instead
        # (observed empirically on JPEG requantization at quality<=40,
        # where 9/12 header bytes were corrupted). Treat it as a decode
        # failure rather than a "found a 0-byte watermark" success so this
        # degenerate case surfaces as a loud, honest error instead of a
        # silently-wrong empty payload.
        if declared_length == 0:
            raise ValueError(
                "No watermark detected: decoded length header declared a "
                "0-byte payload, which no real watermark produces. This "
                "indicates the header block's corruption exceeded Reed-"
                "Solomon's correction capacity and decode() converged on "
                "a spurious codeword rather than genuinely recovering one."
            )

        # Phase 2: now that the payload length is known, compute the
        # payload block's encoded size (accounting for RSCodec's internal
        # chunking above 255 bytes, see _rs_parity_overhead) and read/decode
        # exactly that many additional bits.
        payload_frame_bytes = declared_length + _rs_parity_overhead(declared_length)
        payload_bits_needed = payload_frame_bytes * 8
        total_bits_needed = header_bits_needed + payload_bits_needed

        if declared_length < 0 or total_bits_needed > capacity_bits:
            raise ValueError(
                "No watermark detected: decoded length header "
                f"({declared_length} bytes) is inconsistent with this image's "
                f"capacity ({capacity_bits} bits). This indicates the header "
                "survived RS correction by chance on corrupted/non-watermarked "
                "data rather than reflecting a real embedded payload."
            )

        all_bits = self._extract_bits_from_channel(luma, total_bits_needed)
        payload_frame = self._bits_to_bytes(all_bits[header_bits_needed:])

        payload_rsc = reedsolo.RSCodec(RS_PARITY_BYTES)
        try:
            payload_decoded, _, _ = payload_rsc.decode(payload_frame)
        except reedsolo.ReedSolomonError as exc:
            raise ValueError(
                f"No watermark detected: Reed-Solomon decoding failed ({exc}). "
                "The image may be unwatermarked or too badly degraded to recover."
            ) from exc

        payload = bytes(payload_decoded)
        if len(payload) != declared_length:
            raise ValueError(
                "No watermark detected: recovered payload length "
                f"({len(payload)}) does not match declared length "
                f"({declared_length})."
            )

        logger.info(f"Watermark extracted: {len(payload)} bytes")
        return payload

    # ------------------------------------------------------------------
    # Payload framing (Reed-Solomon + length prefix) <-> bit array
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_payload_to_bits(watermark_data: bytes) -> NDArray[np.uint8]:
        """
        Build the two-block wire frame -- RS(length_prefix) followed by
        RS(watermark_data), each encoded independently (see the wire-format
        note above _LENGTH_PREFIX_FORMAT for why they must be independent
        codewords rather than one combined message) -- and unpack the
        concatenated frame to a flat array of 0/1 bits (MSB-first per byte)
        ready for one-bit-per-block embedding.
        """
        length_prefix = struct.pack(_LENGTH_PREFIX_FORMAT, len(watermark_data))
        header_rsc = reedsolo.RSCodec(RS_HEADER_PARITY_BYTES)
        header_encoded = bytes(header_rsc.encode(length_prefix))

        payload_rsc = reedsolo.RSCodec(RS_PARITY_BYTES)
        payload_encoded = bytes(payload_rsc.encode(watermark_data))

        frame = header_encoded + payload_encoded
        return np.unpackbits(np.frombuffer(frame, dtype=np.uint8))

    @staticmethod
    def _bits_to_bytes(bits: NDArray[np.uint8]) -> bytes:
        """Inverse of _encode_payload_to_bits's bit-unpacking step."""
        # np.packbits requires a length that's a multiple of 8; callers of
        # this helper always extract bit counts computed as byte_count * 8,
        # so this is always exact and never needs padding.
        return np.packbits(bits).tobytes()

    # ------------------------------------------------------------------
    # Color handling: watermark is embedded in luma only
    # ------------------------------------------------------------------

    def _split_luma(
        self, image: NDArray[np.uint8]
    ) -> tuple[NDArray[np.uint8], NDArray[np.uint8] | None]:
        """
        Split an image into a luma (Y) channel to watermark and whatever
        chroma/alpha data needs to be preserved and reattached unchanged.

        Embedding only in luma (rather than every channel independently) is
        the standard approach for color watermarking: the human eye is far
        less sensitive to small luma perturbations than chroma ones for a
        given visibility budget, and it keeps embedding capacity/robustness
        analysis identical between grayscale and color inputs.

        Returns:
            (luma, chroma) where chroma is None for 2D grayscale input, or
            the full original array (so _merge_luma can slice color/alpha
            back out of it) for color input.
        """
        if image.ndim == 2:
            return image, None

        # 3D input: (H, W, C). Convert RGB/RGBA -> YCrCb, watermark Y only.
        # Alpha (if present) passes through untouched via `image` (the
        # merge step re-slices it from the original array).
        rgb = image[:, :, :3]
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        luma = ycrcb[:, :, 0]
        return luma, image

    def _merge_luma(
        self,
        watermarked_luma: NDArray[np.uint8],
        chroma_source: NDArray[np.uint8] | None,
        original_image: NDArray[np.uint8],
    ) -> NDArray[np.uint8]:
        """Recombine a watermarked luma channel with the original chroma/alpha."""
        if chroma_source is None:
            return watermarked_luma

        rgb = original_image[:, :, :3]
        ycrcb = cv2.cvtColor(rgb, cv2.COLOR_RGB2YCrCb)
        ycrcb[:, :, 0] = watermarked_luma
        watermarked_rgb = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2RGB)

        if original_image.shape[2] == 3:
            return watermarked_rgb

        # Preserve alpha (or any extra channels) unchanged.
        result = original_image.copy()
        result[:, :, :3] = watermarked_rgb
        return result

    # ------------------------------------------------------------------
    # Block-DCT bit embedding / extraction on a single 2D channel
    # ------------------------------------------------------------------

    def _capacity_bits(self, channel_shape: tuple[int, int]) -> int:
        """Number of one-bit embedding sites (whole blocks) in a channel."""
        height, width = channel_shape
        return (height // self.block_size) * (width // self.block_size)

    def _midband_position(self) -> tuple[int, int]:
        """
        Resolve the fixed mid-band coefficient (row, col) for this
        instance's block_size, scaling the block_size=8 reference position
        proportionally so smaller/larger blocks still land in the mid-band
        rather than drifting into DC or the highest frequencies.
        """
        if self.block_size < _MIN_BLOCK_SIZE:
            raise ValueError(
                f"block_size must be >= {_MIN_BLOCK_SIZE} for mid-band DCT "
                f"watermarking, got {self.block_size}"
            )
        row_frac, col_frac = _DEFAULT_MIDBAND_FRACTION
        row = max(1, min(self.block_size - 2, round(row_frac * self.block_size)))
        col = max(1, min(self.block_size - 2, round(col_frac * self.block_size)))
        return row, col

    def _quantization_step(self) -> float:
        """
        Map self.strength (0.0-1.0) to a DCT-domain quantization step Q.

        The embedding rule below rounds the mid-band coefficient to the
        nearest multiple of Q and encodes one bit in the parity (even/odd)
        of that multiple -- so Q sets the minimum coefficient perturbation
        needed to flip a bit, i.e. the robustness margin against any noise
        (JPEG requantization, mild resampling, etc.) that perturbs the
        coefficient by less than roughly Q/2.

        Range chosen empirically: Q=4 (strength=0) is already enough
        separation to survive light requantization while staying visually
        negligible on 8-bit pixel data (DCT coefficients here are computed
        on values in [-128, 127], not normalized [0, 1]); Q=40 (strength=1)
        trades noticeably more visible mid-band ringing for much higher
        robustness. 0.5 (the class default) maps to Q=22, the midpoint.
        """
        return 4.0 + self.strength * 36.0

    def _embed_bits_in_channel(
        self, channel: NDArray[np.uint8], bits: NDArray[np.uint8]
    ) -> NDArray[np.uint8]:
        """
        Embed `bits` (one bit per block, in row-major block order) into the
        mid-band DCT coefficient of each block of a single-channel image.
        """
        bs = self.block_size
        row, col = self._midband_position()
        q = self._quantization_step()

        height, width = channel.shape
        blocks_h = height // bs
        blocks_w = width // bs

        # Work in float32, centered at zero (standard DCT-of-image-blocks
        # convention: subtract 128 so the DC term isn't dominated by the
        # [0, 255] offset), matching cv2.dct's expected float input.
        watermarked = channel.astype(np.float32).copy()

        bit_index = 0
        for block_row in range(blocks_h):
            if bit_index >= len(bits):
                break
            r0 = block_row * bs
            for block_col in range(blocks_w):
                if bit_index >= len(bits):
                    break
                c0 = block_col * bs

                block = watermarked[r0:r0 + bs, c0:c0 + bs] - 128.0
                coeffs = cv2.dct(block)

                coeffs[row, col] = self._quantize_coefficient(
                    coeffs[row, col], q, int(bits[bit_index])
                )

                restored = cv2.idct(coeffs) + 128.0
                watermarked[r0:r0 + bs, c0:c0 + bs] = restored

                bit_index += 1

        return np.clip(np.round(watermarked), 0, 255).astype(np.uint8)

    def _extract_bits_from_channel(
        self, channel: NDArray[np.uint8], num_bits: int
    ) -> NDArray[np.uint8]:
        """
        Read back `num_bits` bits (one per block, same row-major block
        order used by _embed_bits_in_channel) from the mid-band DCT
        coefficient of each block.
        """
        bs = self.block_size
        row, col = self._midband_position()
        q = self._quantization_step()

        height, width = channel.shape
        blocks_h = height // bs
        blocks_w = width // bs

        channel_f = channel.astype(np.float32)
        bits = np.empty(num_bits, dtype=np.uint8)

        bit_index = 0
        for block_row in range(blocks_h):
            if bit_index >= num_bits:
                break
            r0 = block_row * bs
            for block_col in range(blocks_w):
                if bit_index >= num_bits:
                    break
                c0 = block_col * bs

                block = channel_f[r0:r0 + bs, c0:c0 + bs] - 128.0
                coeffs = cv2.dct(block)

                bits[bit_index] = self._read_coefficient_bit(coeffs[row, col], q)
                bit_index += 1

        return bits

    @staticmethod
    def _quantize_coefficient(value: float, q: float, bit: int) -> float:
        """
        Round `value` to the nearest multiple of `q` whose "multiple index"
        (value / q, rounded) has parity equal to `bit`. This is a standard
        quantization-index-modulation (QIM) style embedding: it encodes one
        bit as the even/odd parity of the quantized coefficient, which
        degrades gracefully under further quantization (e.g. JPEG) as long
        as the additional distortion is smaller than roughly q/2.
        """
        k = round(value / q)
        if (k % 2) != bit:
            # Nudge to the nearest neighboring multiple with correct parity.
            # Choosing the neighbor on the side closer to the original value
            # minimizes the perturbation (and thus visible distortion).
            if value - k * q >= 0:
                k += 1
            else:
                k -= 1
        return k * q

    @staticmethod
    def _read_coefficient_bit(value: float, q: float) -> int:
        """Inverse of _quantize_coefficient's encoding: recover the embedded bit."""
        k = round(value / q)
        return int(k % 2)


def _rs_parity_overhead(message_length: int) -> int:
    """
    Total Reed-Solomon parity byte overhead that RSCodec(RS_PARITY_BYTES)
    adds when encoding a message of `message_length` bytes.

    RSCodec transparently chunks messages longer than 255 - RS_PARITY_BYTES
    bytes into multiple RS blocks (each still carrying RS_PARITY_BYTES
    parity bytes), so total overhead scales with the number of chunks, not
    just a single fixed RS_PARITY_BYTES addition. This mirrors reedsolo's
    own internal chunking (see RSCodec.encode) so extract_watermark can
    predict the on-the-wire frame size for a declared payload length without
    re-encoding anything.
    """
    chunk_size = 255 - RS_PARITY_BYTES
    num_chunks = max(1, -(-message_length // chunk_size))  # ceil division
    return num_chunks * RS_PARITY_BYTES
