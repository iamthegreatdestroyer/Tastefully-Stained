"""
API Models Module
=================

Pydantic models for API request/response validation.

This module defines the data models used for validating and serializing
API requests and responses using Pydantic v2.

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WatermarkStrategy(str, Enum):
    """Watermarking strategy options."""
    
    AUTO = "auto"
    DCT = "dct"
    DWT = "dwt"
    HYBRID = "hybrid"


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service health status")
    version: str = Field(..., description="API version")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


class WatermarkRequest(BaseModel):
    """Request model for watermark embedding."""
    
    watermark_data: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Data to embed as watermark"
    )
    strategy: WatermarkStrategy = Field(
        default=WatermarkStrategy.AUTO,
        description="Watermarking strategy to use"
    )
    strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Watermark embedding strength"
    )
    include_c2pa: bool = Field(
        default=True,
        description="Include C2PA manifest"
    )
    anchor_blockchain: bool = Field(
        default=False,
        description="Anchor to blockchain"
    )
    
    @field_validator("watermark_data")
    @classmethod
    def validate_watermark_data(cls, v: str) -> str:
        """Validate watermark data is not empty or whitespace."""
        if not v.strip():
            raise ValueError("Watermark data cannot be empty or whitespace")
        return v


class WatermarkResponse(BaseModel):
    """Response model for watermark embedding."""
    
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Operation result message")
    watermarked_image_url: str | None = Field(
        None,
        description="URL to download watermarked image"
    )
    watermark_id: str | None = Field(
        None,
        description="Unique watermark identifier"
    )
    c2pa_manifest_url: str | None = Field(
        None,
        description="URL to C2PA manifest"
    )
    blockchain_tx_hash: str | None = Field(
        None,
        description="Blockchain transaction hash"
    )
    quality_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Image quality metrics (PSNR, SSIM)"
    )
    processing_time_ms: float = Field(
        default=0.0,
        description="Processing time in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


class WatermarkExtractResponse(BaseModel):
    """Response model for watermark extraction."""
    
    success: bool = Field(..., description="Extraction success status")
    watermark_data: str | None = Field(
        None,
        description="Extracted watermark data"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score"
    )
    strategy_detected: WatermarkStrategy | None = Field(
        None,
        description="Detected watermarking strategy"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional extraction metadata"
    )


class WatermarkVerifyResponse(BaseModel):
    """Response model for watermark verification."""
    
    is_valid: bool = Field(..., description="Watermark validity status")
    is_authentic: bool = Field(
        default=False,
        description="Watermark authenticity status"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Verification confidence score"
    )
    c2pa_verified: bool = Field(
        default=False,
        description="C2PA manifest verification status"
    )
    blockchain_verified: bool = Field(
        default=False,
        description="Blockchain anchoring verification status"
    )
    tampering_detected: bool = Field(
        default=False,
        description="Whether tampering was detected"
    )
    verification_details: dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed verification results"
    )
