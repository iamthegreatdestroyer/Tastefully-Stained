"""
API Routes Module
=================

FastAPI route definitions for watermarking endpoints.

This module defines all REST API endpoints for the Tastefully Stained
watermarking service, including watermark embedding, extraction,
verification, and blockchain anchoring.

Endpoints:
----------
- POST /api/v1/watermark/embed - Embed watermark in image
- POST /api/v1/watermark/extract - Extract watermark from image
- POST /api/v1/watermark/verify - Verify watermark authenticity
- POST /api/v1/c2pa/manifest - Generate C2PA manifest
- POST /api/v1/blockchain/anchor - Anchor to blockchain
- GET /api/v1/health - Health check

Example:
--------
    >>> from fastapi import FastAPI
    >>> from watermark_engine.api.routes import router
    >>>
    >>> app = FastAPI()
    >>> app.include_router(router, prefix="/api/v1")

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import base64
import io
import logging
import time
from typing import TYPE_CHECKING

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

if TYPE_CHECKING:
    import numpy as np

from watermark_engine.api.models import (
    HealthResponse,
    WatermarkExtractResponse,
    WatermarkResponse,
    WatermarkStrategy,
    WatermarkVerifyResponse,
)
from watermark_engine.core.dct_processor import DCTWatermarker
from watermark_engine.core.dwt_processor import DWTWatermarker
from watermark_engine.core.hybrid_algorithm import (
    HybridWatermarkOrchestrator,
    WatermarkStrategy as CoreWatermarkStrategy,
)
from watermark_engine.utils.image_loader import ImageLoader

logger = logging.getLogger(__name__)

router = APIRouter(tags=["watermark"])

# Shared image loader. Stateless and cheap to construct once; every request
# still gets its own DCT/DWT/orchestrator instances below because `strength`
# (and, for DWT, `wavelet`/`level`) are per-request inputs baked into those
# classes' constructors rather than passed per-call.
_image_loader = ImageLoader()

# API-facing strategy names (models.WatermarkStrategy: auto/dct/dwt/hybrid)
# to the orchestrator's own strategy enum (hybrid_algorithm.WatermarkStrategy:
# auto/dct_primary/dwt_primary/hybrid_dual). These are deliberately two
# separate enums -- the API contract is stable/simple for callers, while the
# orchestrator's names describe its internal dual-embed mechanics -- so the
# mapping is spelled out explicitly rather than assuming the names line up.
_STRATEGY_TO_CORE: dict[WatermarkStrategy, CoreWatermarkStrategy] = {
    WatermarkStrategy.AUTO: CoreWatermarkStrategy.AUTO,
    WatermarkStrategy.DCT: CoreWatermarkStrategy.DCT_PRIMARY,
    WatermarkStrategy.DWT: CoreWatermarkStrategy.DWT_PRIMARY,
    WatermarkStrategy.HYBRID: CoreWatermarkStrategy.HYBRID_DUAL,
}

# Core orchestrator strategy back to the API-facing enum, for reporting
# `strategy_detected` on extraction (where AUTO is never a real answer --
# extraction always resolves to whichever concrete method actually worked).
_CORE_STRATEGY_TO_API: dict[CoreWatermarkStrategy, WatermarkStrategy] = {
    CoreWatermarkStrategy.DCT_PRIMARY: WatermarkStrategy.DCT,
    CoreWatermarkStrategy.DWT_PRIMARY: WatermarkStrategy.DWT,
    CoreWatermarkStrategy.HYBRID_DUAL: WatermarkStrategy.HYBRID,
}


def _parse_strategy(strategy: str) -> WatermarkStrategy:
    """Validate a raw strategy string against the API enum, 422 on garbage input."""
    try:
        return WatermarkStrategy(strategy.lower())
    except ValueError as exc:
        valid = ", ".join(s.value for s in WatermarkStrategy)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid strategy {strategy!r}. Must be one of: {valid}.",
        ) from exc


async def _read_upload(image: UploadFile) -> bytes:
    """Read an UploadFile's bytes, 400 if the upload is empty."""
    data = await image.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    return data


def _decode_image(data: bytes, *, filename: str | None):
    """
    Decode uploaded bytes into (array, metadata) via ImageLoader.

    Any decode failure -- corrupt data, unsupported/undetected format,
    truncated upload -- is a client error (400), not a server error: the
    image never made it far enough to reach the watermarking engine at all.
    """
    try:
        return _image_loader.load_from_bytes(data)
    except ValueError as exc:
        logger.info(f"Image decode failed for upload {filename!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to decode uploaded image: {exc}",
        ) from exc


def _build_orchestrator(strength: float) -> HybridWatermarkOrchestrator:
    """
    Construct a fresh orchestrator for this request's `strength` (embed only).

    DCTWatermarker/DWTWatermarker take `strength` as a constructor argument,
    not a per-call argument, so a per-request strength value means a
    per-request instance rather than a shared/global watermarker.

    Only used for /watermark/embed. See _build_extraction_orchestrator for
    why extraction does NOT reuse this with a caller-supplied strength.
    """
    try:
        dct = DCTWatermarker(strength=strength)
        dwt = DWTWatermarker(strength=strength)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return HybridWatermarkOrchestrator(dct, dwt)


def _build_extraction_orchestrator() -> HybridWatermarkOrchestrator:
    """
    Construct an orchestrator for /watermark/extract and /watermark/verify,
    using each watermarker's own documented constructor default strength.

    `strength` is NOT embed-only: both DCTWatermarker.extract_watermark and
    DWTWatermarker.extract_watermark derive their QIM decode quantization
    step from `self.strength` (see DWTWatermarker._quantum()), so decoding
    requires the *same* strength the image was embedded with -- there is no
    way to recover it from the image alone. DCT fails loudly on a mismatch
    (Reed-Solomon raises ValueError), but DWT has no error-correcting code
    and can silently "succeed" with a garbage/empty payload instead (see the
    empty-payload guard in extract_watermark()/verify_watermark() below).

    The public API contract for /extract and /verify (see api/models.py) is
    intentionally `image` only -- there is no strength/algorithm-parameter
    field, and no persistent per-watermark metadata store exists in this
    phase to look one up by. Given that contract, the only self-consistent
    behavior is to assume each watermarker's own published default (the
    same assumption a caller who also didn't override `strength` at embed
    time would get right). A caller who deliberately embeds at a
    non-default strength and then expects /extract or /verify to recover it
    without being told the strength is asking for something this API
    doesn't have the information to do; this is a known, documented
    limitation, not a bug to silently paper over.
    """
    return HybridWatermarkOrchestrator(DCTWatermarker(), DWTWatermarker())


def _extract_or_raise(orchestrator: HybridWatermarkOrchestrator, image: np.ndarray):
    """
    Call orchestrator.extract_watermark() with a defensive empty-payload
    guard, raising ValueError (the same exception type/semantics the
    orchestrator itself uses for "no watermark") if it "succeeds" with a
    zero-length payload.

    A genuine embed_watermark() call (DCT or DWT) always frames at least a
    non-empty caller-supplied payload -- neither class supports embedding an
    empty watermark -- so a 0-byte result is never a real watermark. DCT's
    own extract_watermark() already guards this internally (raises on
    declared_length == 0, seen directly in dct_processor.py). DWT's does
    not: it has no error-correcting code, only majority-vote across
    subbands/channels, so an extraction attempted with the wrong `strength`
    (wrong QIM quantization step) can decode a garbage header that
    coincidentally reads as "0 bytes" and return b'' without ever raising,
    rather than failing loudly the way a strength-mismatched DCT attempt
    does. Confirmed directly: DWTWatermarker(strength=0.5) extracting an
    image embedded via DWTWatermarker(strength=0.8) returns b'' with no
    exception. This guard exists at the routes layer (not inside
    hybrid_algorithm.py/dwt_processor.py, which are out of this phase's
    scope) so that case surfaces to API callers as "no watermark detected"
    instead of a false-positive 200 with an empty payload.
    """
    result = orchestrator.extract_watermark(image)
    if not result.data:
        raise ValueError(
            "No watermark detected: extraction nominally succeeded but "
            "recovered a 0-byte payload, which no real embedded watermark "
            "produces. This typically means the image was watermarked "
            "with different parameters (e.g. a non-default `strength`) "
            "than this endpoint assumes, or is not watermarked at all."
        )
    return result


def _quality_metrics(original: np.ndarray, watermarked: np.ndarray) -> dict[str, float]:
    """
    Compute PSNR/SSIM between the original and watermarked arrays.

    Best-effort: quality metrics are diagnostic, not load-bearing, so a
    failure here (e.g. skimage's window-size floor on a tiny image) is
    logged and downgraded to an empty dict rather than failing the whole
    embed request that otherwise succeeded.
    """
    try:
        from skimage.metrics import peak_signal_noise_ratio, structural_similarity

        psnr = float(peak_signal_noise_ratio(original, watermarked, data_range=255))
        multichannel = watermarked.ndim == 3
        ssim = float(
            structural_similarity(
                original,
                watermarked,
                data_range=255,
                channel_axis=-1 if multichannel else None,
            )
        )
        return {"psnr": psnr, "ssim": ssim}
    except Exception as exc:  # noqa: BLE001 - diagnostic only, never fail the request over this
        logger.warning(f"Quality metric computation failed: {exc}")
        return {}


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status
    """
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        service="tastefully-stained"
    )


@router.post("/watermark/embed", response_model=WatermarkResponse)
async def embed_watermark(
    image: UploadFile = File(...),
    watermark_data: str = Form(""),
    strategy: str = Form("auto"),
    strength: float = Form(0.5),
) -> WatermarkResponse:
    """
    Embed watermark in uploaded image.

    Args:
        image: Image file to watermark (JPEG, PNG, WebP)
        watermark_data: Data to embed as watermark
        strategy: Watermarking strategy (auto, dct, dwt, hybrid)
        strength: Watermark embedding strength (0.0-1.0)

    Returns:
        WatermarkResponse with watermarked image and metadata

    Raises:
        HTTPException: 400 if image format is unsupported
        HTTPException: 422 if watermark data or strategy/strength is invalid

    Note:
        `watermark_data`/`strategy`/`strength` must be declared as
        `Form(...)`, not bare defaults, because a route that also has a
        `File(...)`/`UploadFile` parameter switches FastAPI into
        multipart-only parsing for that request: any co-declared plain
        parameter is otherwise interpreted as a *query* parameter (always
        silently falling back to its default, never reading the multipart
        body) rather than a form field. This was verified directly against
        the original stub signature -- it had the identical latent bug,
        invisible only because the stub raised 501 before ever reading these
        arguments.
    """
    logger.info(f"Embed request: file={image.filename}, strategy={strategy}")

    if not watermark_data.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="watermark_data cannot be empty or whitespace.",
        )

    api_strategy = _parse_strategy(strategy)

    raw_bytes = await _read_upload(image)
    array, metadata = _decode_image(raw_bytes, filename=image.filename)

    orchestrator = _build_orchestrator(strength)
    core_strategy = _STRATEGY_TO_CORE[api_strategy]

    start = time.perf_counter()
    try:
        watermarked = orchestrator.embed_robust_watermark(
            array, watermark_data.encode("utf-8"), core_strategy
        )
    except ValueError as exc:
        # Image too small for the chosen strategy's capacity, etc. -- a
        # property of this specific request's inputs, not a server fault.
        logger.info(f"Embedding failed for {image.filename!r}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to embed watermark: {exc}",
        ) from exc
    elapsed_ms = (time.perf_counter() - start) * 1000

    # No object storage / CDN layer exists yet (IPFS handling is an explicit
    # Phase-5-scoped-elsewhere stub in blockchain/ipfs_handler.py that raises
    # NotImplementedError) so the watermarked image is returned inline as a
    # base64 data URL rather than a reference to storage that doesn't exist.
    # This is a real, directly-usable URL (decodable/renderable client-side)
    # rather than a fabricated path into a non-existent download endpoint.
    output_format = metadata.format
    buffer = io.BytesIO()
    saved_bytes = _image_loader.save(
        watermarked, destination=buffer, metadata=metadata, format_override=output_format
    )
    mime = f"image/{output_format.value}" if output_format.value != "unknown" else "image/png"
    data_url = f"data:{mime};base64,{base64.b64encode(saved_bytes).decode('ascii')}"

    quality_metrics = _quality_metrics(array, watermarked)

    watermark_id = f"wm_{base64.urlsafe_b64encode(saved_bytes[:12]).decode('ascii').rstrip('=')}"

    logger.info(
        f"Embed succeeded: file={image.filename}, strategy={core_strategy.value}, "
        f"bytes_out={len(saved_bytes)}, time_ms={elapsed_ms:.2f}"
    )

    return WatermarkResponse(
        success=True,
        message="Watermark embedded successfully",
        watermarked_image_url=data_url,
        watermark_id=watermark_id,
        c2pa_manifest_url=None,  # C2PA manifest generation is out of scope (separate stub subsystem)
        blockchain_tx_hash=None,  # Blockchain anchoring is out of scope (separate stub subsystem)
        quality_metrics=quality_metrics,
        processing_time_ms=elapsed_ms,
    )


@router.post("/watermark/extract", response_model=WatermarkExtractResponse)
async def extract_watermark(
    image: UploadFile = File(...)
) -> WatermarkExtractResponse:
    """
    Extract watermark from uploaded image.

    Args:
        image: Watermarked image file

    Returns:
        WatermarkExtractResponse with extracted data and confidence

    Raises:
        HTTPException: 400 if image format is unsupported
        HTTPException: 404 if no watermark detected
    """
    logger.info(f"Extract request: file={image.filename}")

    raw_bytes = await _read_upload(image)
    array, _metadata = _decode_image(raw_bytes, filename=image.filename)

    orchestrator = _build_extraction_orchestrator()

    try:
        result = _extract_or_raise(orchestrator, array)
    except ValueError as exc:
        # Every failure inside HybridWatermarkOrchestrator.extract_watermark
        # (plus the empty-payload guard in _extract_or_raise) means "no
        # watermark recoverable from this (decodable) image" -- including
        # the "image too small to hold a watermark" case, which
        # dct_processor.py's own docstring frames as "no watermark can be
        # present" rather than "bad image". The image already decoded fine
        # above, so this is a 404, not a 400/422.
        logger.info(f"Extraction failed for {image.filename!r}: {exc}")
        # exc's message already starts with "No watermark detected: " --
        # both HybridWatermarkOrchestrator.extract_watermark's own ValueError
        # and _extract_or_raise's empty-payload guard are worded that way --
        # so pass it through directly rather than re-wrapping/doubling it.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    try:
        watermark_text = result.data.decode("utf-8")
    except UnicodeDecodeError:
        # Watermark payload wasn't UTF-8 text (e.g. embedded via a
        # non-text-producing caller). Surface it losslessly rather than
        # raising -- the extraction itself succeeded.
        watermark_text = base64.b64encode(result.data).decode("ascii")

    logger.info(
        f"Extract succeeded: file={image.filename}, "
        f"strategy={result.strategy_used.value}, confidence={result.confidence:.2f}"
    )

    return WatermarkExtractResponse(
        success=True,
        watermark_data=watermark_text,
        confidence=result.confidence,
        strategy_detected=_CORE_STRATEGY_TO_API[result.strategy_used],
        metadata=result.quality_metrics,
    )


@router.post("/watermark/verify", response_model=WatermarkVerifyResponse)
async def verify_watermark(
    image: UploadFile = File(...)
) -> WatermarkVerifyResponse:
    """
    Verify watermark authenticity and integrity.

    Args:
        image: Image file to verify

    Returns:
        WatermarkVerifyResponse with verification result
    """
    logger.info(f"Verify request: file={image.filename}")

    raw_bytes = await _read_upload(image)
    array, _metadata = _decode_image(raw_bytes, filename=image.filename)

    orchestrator = _build_extraction_orchestrator()

    try:
        result = _extract_or_raise(orchestrator, array)
    except ValueError as exc:
        # Verification's job is to answer "is this valid?" -- absence of a
        # recoverable watermark is a normal, valid *answer* here (is_valid
        # False), not an error condition the way it is for /extract (whose
        # entire point is retrieving the payload). So this returns 200 with
        # is_valid=False rather than 404.
        logger.info(f"Verification found no watermark for {image.filename!r}: {exc}")
        return WatermarkVerifyResponse(
            is_valid=False,
            is_authentic=False,
            confidence=0.0,
            c2pa_verified=False,  # C2PA verification is out of scope (separate stub subsystem)
            blockchain_verified=False,  # Blockchain verification is out of scope (separate stub subsystem)
            tampering_detected=False,
            verification_details={"reason": str(exc)},
        )

    logger.info(
        f"Verify succeeded: file={image.filename}, "
        f"strategy={result.strategy_used.value}, confidence={result.confidence:.2f}"
    )

    return WatermarkVerifyResponse(
        is_valid=True,
        is_authentic=True,
        confidence=result.confidence,
        c2pa_verified=False,
        blockchain_verified=False,
        tampering_detected=False,
        verification_details={
            "strategy_detected": _CORE_STRATEGY_TO_API[result.strategy_used].value,
            **result.quality_metrics,
        },
    )
