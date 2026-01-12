"""
C2PA Manifest Tests
===================

Comprehensive tests for C2PA manifest creation and validation.

Coverage targets:
- Manifest creation
- Assertion handling
- Signature verification
- Content validation

Run: pytest backend/tests/test_c2pa.py -v
"""

from __future__ import annotations

import pytest

from watermark_engine.c2pa.manifest_builder import (
    ManifestBuilder,
    C2PAManifest,
    CreatorAssertion,
    WatermarkAssertion,
    AssertionType,
)
from watermark_engine.c2pa.validation import C2PAValidator, ValidationStatus


class TestAssertions:
    """Test C2PA assertions."""
    
    def test_creator_assertion(self) -> None:
        """Test creator assertion creation."""
        assertion = CreatorAssertion(name="Test Creator")
        
        assert assertion.label == "c2pa.creator"
        assert assertion.assertion_type == AssertionType.CREATOR
        assert assertion.data["name"] == "Test Creator"
    
    def test_watermark_assertion(self) -> None:
        """Test watermark assertion creation."""
        assertion = WatermarkAssertion(
            watermark_hash="0x123abc",
            strategy="hybrid",
            strength=0.5
        )
        
        assert assertion.label == "tastefully-stained.watermark"
        assert assertion.assertion_type == AssertionType.WATERMARK
        assert assertion.data["watermark_hash"] == "0x123abc"
        assert assertion.data["strategy"] == "hybrid"


class TestC2PAManifest:
    """Test C2PA manifest data class."""
    
    def test_manifest_creation(self) -> None:
        """Test manifest creation with defaults."""
        manifest = C2PAManifest(title="Test Image")
        
        assert manifest.title == "Test Image"
        assert manifest.claim_generator == "Tastefully-Stained/0.1.0"
        assert manifest.format == "image/png"
        assert manifest.instance_id.startswith("xmp.iid:")
    
    def test_manifest_to_dict(self) -> None:
        """Test manifest serialization."""
        manifest = C2PAManifest(title="Test")
        result = manifest.to_dict()
        
        assert "claim_generator" in result
        assert "title" in result
        assert "assertions" in result
        assert "signature_info" in result


class TestManifestBuilder:
    """Test manifest builder."""
    
    @pytest.fixture
    def builder(self) -> ManifestBuilder:
        """Create test builder instance."""
        return ManifestBuilder()
    
    def test_supported_formats(self, builder: ManifestBuilder) -> None:
        """Test supported formats list."""
        assert "image/jpeg" in builder.SUPPORTED_FORMATS
        assert "image/png" in builder.SUPPORTED_FORMATS
        assert "image/webp" in builder.SUPPORTED_FORMATS
    
    def test_compute_content_hash(self) -> None:
        """Test content hash computation."""
        content = b"test content"
        hash_value = ManifestBuilder.compute_content_hash(content)
        
        assert hash_value.startswith("sha256:")
        assert len(hash_value) == 71  # sha256: + 64 hex chars
    
    def test_create_manifest_unsupported_format(
        self,
        builder: ManifestBuilder
    ) -> None:
        """Test that unsupported format raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported format"):
            builder.create_manifest(
                content_bytes=b"test",
                title="Test",
                mime_type="application/pdf"
            )
    
    def test_create_manifest_not_implemented(
        self,
        builder: ManifestBuilder
    ) -> None:
        """Test that manifest creation raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            builder.create_manifest(
                content_bytes=b"test",
                title="Test",
                mime_type="image/png"
            )


class TestC2PAValidator:
    """Test C2PA validator."""
    
    @pytest.fixture
    def validator(self) -> C2PAValidator:
        """Create test validator instance."""
        return C2PAValidator()
    
    def test_validation_status_enum(self) -> None:
        """Test validation status values."""
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.INVALID_SIGNATURE.value == "invalid_signature"
        assert ValidationStatus.TAMPERED_CONTENT.value == "tampered_content"
    
    def test_validate_manifest_not_implemented(
        self,
        validator: C2PAValidator
    ) -> None:
        """Test that validation raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            validator.validate_manifest({"test": "manifest"})
