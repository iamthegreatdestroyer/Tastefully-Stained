"""
C2PA Manifest Tests
===================

Comprehensive tests for C2PA manifest creation and validation.

Coverage targets:
- Manifest creation
- Assertion handling
- Real signing via c2pa-python (Phase 6)
- Real JUMBF embedding into an actual image (Phase 6)
- Real round-trip validation: create -> sign -> embed -> extract -> validate
- Tamper detection: modified content/manifests must fail validation

These tests exercise the real ``c2pa-python`` binding end to end using a
throwaway development certificate chain (see
``backend/watermark_engine/c2pa/manifest_builder.py``'s module docstring
and ``tools/generate_dev_certs.sh``). They are skipped automatically if
that dev chain hasn't been generated yet, rather than failing the suite --
see the ``_dev_certs_available`` skip condition below.

Run: pytest backend/tests/test_c2pa.py -v
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from watermark_engine.c2pa.manifest_builder import (
    ActionsAssertion,
    AssertionType,
    C2PAManifest,
    CreatorAssertion,
    ManifestBuilder,
    WatermarkAssertion,
    _DEFAULT_CERTIFICATE_PATH,
    _DEFAULT_PRIVATE_KEY_PATH,
)
from watermark_engine.c2pa.validation import C2PAValidator, ValidationStatus

# Real signing/embedding/validation tests need the dev certificate chain
# generated (tools/generate_dev_certs.sh). Skip those specific tests --
# rather than the whole module -- if it's not present, so pure dataclass/
# validation-logic tests still run in environments that haven't run the
# cert generator.
_dev_certs_available = (
    _DEFAULT_CERTIFICATE_PATH.exists() and _DEFAULT_PRIVATE_KEY_PATH.exists()
)
requires_dev_certs = pytest.mark.skipif(
    not _dev_certs_available,
    reason=(
        "Dev certificate chain not found at "
        f"{_DEFAULT_CERTIFICATE_PATH.parent}. Run "
        "tools/generate_dev_certs.sh to generate it."
    ),
)


def _make_test_png(size: tuple[int, int] = (128, 128), color: tuple[int, int, int] = (60, 120, 200)) -> bytes:
    """Build a small real PNG image for embedding tests."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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

    def test_actions_assertion_default(self) -> None:
        """Test default actions assertion is c2pa.created."""
        assertion = ActionsAssertion()

        assert assertion.label == "c2pa.actions"
        assert assertion.assertion_type == AssertionType.ACTIONS
        actions = assertion.data["actions"]
        assert len(actions) == 1
        assert actions[0]["action"] == "c2pa.created"
        assert "digitalSourceType" in actions[0]

    def test_actions_assertion_custom(self) -> None:
        """Test actions assertion with a custom action label."""
        assertion = ActionsAssertion(action="c2pa.watermarked", software_agent="Tastefully-Stained/0.1.0")

        actions = assertion.data["actions"]
        assert actions[0]["action"] == "c2pa.watermarked"
        assert actions[0]["softwareAgent"] == "Tastefully-Stained/0.1.0"


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

    def test_create_manifest_returns_real_manifest(
        self,
        builder: ManifestBuilder
    ) -> None:
        """
        Manifest creation is implemented (Phase 6): it must return a
        real, populated C2PAManifest rather than raising
        NotImplementedError.
        """
        manifest = builder.create_manifest(
            content_bytes=b"test content bytes",
            title="Test",
            mime_type="image/png",
        )

        assert isinstance(manifest, C2PAManifest)
        assert manifest.title == "Test"
        assert manifest.format == "image/png"
        assert manifest.is_signed is False

    def test_create_manifest_auto_injects_actions_assertion(
        self,
        builder: ManifestBuilder
    ) -> None:
        """
        The C2PA spec requires the first action assertion to be
        c2pa.created/c2pa.opened. create_manifest must auto-inject this
        when the caller doesn't provide a c2pa.actions assertion, and it
        must be first in the assertions list.
        """
        manifest = builder.create_manifest(
            content_bytes=b"test",
            title="Test",
            mime_type="image/png",
            assertions=[CreatorAssertion(name="Someone")],
        )

        assert manifest.assertions[0].label == "c2pa.actions"
        assert manifest.assertions[0].data["actions"][0]["action"] == "c2pa.created"
        assert manifest.assertions[1].label == "c2pa.creator"

    def test_create_manifest_respects_explicit_actions_assertion(
        self,
        builder: ManifestBuilder
    ) -> None:
        """If the caller supplies their own c2pa.actions assertion, it
        must not be duplicated or overridden."""
        custom_actions = ActionsAssertion(action="c2pa.opened")
        manifest = builder.create_manifest(
            content_bytes=b"test",
            title="Test",
            mime_type="image/png",
            assertions=[custom_actions],
        )

        actions_assertions = [a for a in manifest.assertions if a.label == "c2pa.actions"]
        assert len(actions_assertions) == 1
        assert actions_assertions[0].data["actions"][0]["action"] == "c2pa.opened"

    def test_sign_manifest_missing_certificate_raises(self) -> None:
        """sign_manifest must raise a clear ValueError when configured
        certificate/key paths don't exist, not a native SDK crash."""
        builder = ManifestBuilder(
            certificate_path="/nonexistent/cert.pem",
            private_key_path="/nonexistent/key.pem",
        )
        manifest = builder.create_manifest(
            content_bytes=b"test", title="Test", mime_type="image/png"
        )

        with pytest.raises(ValueError, match="Certificate not configured"):
            builder.sign_manifest(manifest)

    def test_embed_manifest_requires_signing_first(
        self,
        builder: ManifestBuilder
    ) -> None:
        """embed_manifest must refuse to run on an unsigned manifest."""
        manifest = builder.create_manifest(
            content_bytes=b"test", title="Test", mime_type="image/png"
        )

        with pytest.raises(ValueError, match="must be signed"):
            builder.embed_manifest(b"test", manifest)


@requires_dev_certs
class TestRealSigningAndEmbedding:
    """
    Real end-to-end tests: create -> sign -> embed a C2PA manifest into
    an actual PNG image using the dev certificate chain, then verify the
    output is a real, structurally valid, larger PNG with an embedded
    JUMBF manifest store.
    """

    @pytest.fixture
    def builder(self) -> ManifestBuilder:
        return ManifestBuilder()

    @pytest.fixture
    def test_image(self) -> bytes:
        return _make_test_png()

    def test_full_sign_and_embed_pipeline(
        self, builder: ManifestBuilder, test_image: bytes
    ) -> None:
        """create_manifest -> sign_manifest -> embed_manifest must
        produce real signed output, not stub/placeholder bytes."""
        manifest = builder.create_manifest(
            content_bytes=test_image,
            title="Real Signing Test",
            mime_type="image/png",
            assertions=[
                CreatorAssertion(name="Integration Test Creator"),
                WatermarkAssertion(
                    watermark_hash="sha256:" + "ab" * 32,
                    strategy="hybrid",
                    strength=0.5,
                ),
            ],
        )
        assert manifest.is_signed is False

        manifest = builder.sign_manifest(manifest)
        assert manifest.is_signed is True
        assert manifest._signing_alg is not None

        signed_bytes = builder.embed_manifest(test_image, manifest)

        # Real embedding must produce a larger file (JUMBF manifest store
        # data was actually added) that is still a valid PNG.
        assert isinstance(signed_bytes, bytes)
        assert len(signed_bytes) > len(test_image)
        assert signed_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        # Confirm Pillow can still open it as a normal image (embedding
        # didn't corrupt the base image).
        with Image.open(io.BytesIO(signed_bytes)) as img:
            assert img.size == (128, 128)

    def test_embed_manifest_records_signature_bytes(
        self, builder: ManifestBuilder, test_image: bytes
    ) -> None:
        """After embed_manifest, the manifest's .signature field holds
        the real signed output bytes (not None / a placeholder)."""
        manifest = builder.create_manifest(
            content_bytes=test_image, title="Sig Bytes Test", mime_type="image/png"
        )
        manifest = builder.sign_manifest(manifest)
        signed_bytes = builder.embed_manifest(test_image, manifest)

        assert manifest.signature == signed_bytes
        assert manifest.signature is not None
        assert len(manifest.signature) > 0


@requires_dev_certs
class TestRealRoundTripValidation:
    """
    Real round-trip tests: sign+embed content, then genuinely extract
    and validate it back out, confirming the manifest is actually
    recovered and the signature actually verifies (not mocked).
    """

    @pytest.fixture
    def signed_image(self) -> tuple[bytes, bytes]:
        """Returns (original_bytes, signed_bytes)."""
        builder = ManifestBuilder()
        original = _make_test_png()
        manifest = builder.create_manifest(
            content_bytes=original,
            title="Round Trip Test Image",
            mime_type="image/png",
            assertions=[
                CreatorAssertion(name="Round Trip Creator", identifier="creator@example.com"),
                WatermarkAssertion(
                    watermark_hash="sha256:" + "cd" * 32,
                    strategy="dct",
                    strength=0.7,
                ),
            ],
        )
        manifest = builder.sign_manifest(manifest)
        signed = builder.embed_manifest(original, manifest)
        return original, signed

    def test_extract_manifest_recovers_real_data(
        self, signed_image: tuple[bytes, bytes]
    ) -> None:
        """extract_manifest must genuinely recover the title, creator,
        and watermark data we embedded -- not a stub/empty dict."""
        _, signed = signed_image
        validator = C2PAValidator()

        extracted = validator.extract_manifest(signed)

        assert extracted is not None
        assert extracted["title"] == "Round Trip Test Image"

        labels = [a["label"] for a in extracted["assertions"]]
        assert "c2pa.creator" in labels
        assert "tastefully-stained.watermark" in labels

        creator_assertion = next(
            a for a in extracted["assertions"] if a["label"] == "c2pa.creator"
        )
        assert creator_assertion["data"]["name"] == "Round Trip Creator"

        watermark_assertion = next(
            a for a in extracted["assertions"] if a["label"] == "tastefully-stained.watermark"
        )
        assert watermark_assertion["data"]["strategy"] == "dct"
        assert watermark_assertion["data"]["strength"] == 0.7

    def test_validate_content_passes_for_untampered_signed_image(
        self, signed_image: tuple[bytes, bytes]
    ) -> None:
        """A genuinely signed, unmodified image must validate as valid
        with no errors."""
        _, signed = signed_image
        validator = C2PAValidator()

        result = validator.validate_content(signed)

        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID
        assert result.errors == []
        assert result.creator_name == "Round Trip Creator"
        assert result.claim_generator is not None

    def test_verify_signature_on_extracted_manifest(
        self, signed_image: tuple[bytes, bytes]
    ) -> None:
        """verify_signature must report True for a genuinely valid,
        untampered signature."""
        _, signed = signed_image
        validator = C2PAValidator()

        extracted = validator.extract_manifest(signed)
        assert validator.verify_signature(extracted, b"", b"") is True

    def test_verify_certificate_chain_dev_chain_structure(self) -> None:
        """verify_certificate_chain must accept our real dev chain as
        structurally valid (issued-by-CA, not expired) even though it
        reports the (expected, documented) lack of a public trust
        anchor as an issue when none is configured."""
        validator = C2PAValidator(trust_anchors=[])  # skip trust-anchor check
        fullchain_pem = _DEFAULT_CERTIFICATE_PATH.read_bytes()

        is_valid, issues = validator.verify_certificate_chain(fullchain_pem)

        assert is_valid is True
        # No trust anchors configured is reported as an issue string but
        # does not, by itself, make the chain invalid (expiry/self-signed
        # checks are what gate is_valid).
        assert any("No trust anchors configured" in issue for issue in issues)


@requires_dev_certs
class TestTamperDetection:
    """
    Tamper detection tests -- the most important tests in this module.

    A C2PA implementation that fails to detect tampering is worse than
    useless for a content-provenance product: it would let modified
    content pass as "verified" and "unmodified since signing."
    """

    @pytest.fixture
    def signed_image(self) -> bytes:
        builder = ManifestBuilder()
        original = _make_test_png()
        manifest = builder.create_manifest(
            content_bytes=original,
            title="Tamper Test Image",
            mime_type="image/png",
            assertions=[CreatorAssertion(name="Tamper Test Creator")],
        )
        manifest = builder.sign_manifest(manifest)
        return builder.embed_manifest(original, manifest)

    @staticmethod
    def _locate_png_idat(data: bytes) -> tuple[int, int]:
        """Find the offset/length of the (first) IDAT chunk's data
        bytes within a PNG -- i.e. the real pixel data, guaranteed not
        to be inside the C2PA JUMBF metadata chunk (which PNG stores in
        a separate ancillary chunk, typically named 'caBX')."""
        import struct

        pos = 8  # past the PNG signature
        while pos + 8 <= len(data):
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            ctype = data[pos + 4:pos + 8]
            if ctype == b"IDAT":
                return pos + 8, length
            pos += 8 + length + 4  # length + type + data + CRC
        raise AssertionError("No IDAT chunk found in test PNG -- test fixture is broken")

    def test_tampered_pixel_data_fails_validation(self, signed_image: bytes) -> None:
        """
        Flipping bytes in the actual image pixel data (IDAT chunk) after
        signing must be detected: validation must report is_valid=False
        and a TAMPERED_CONTENT status with a data-hash-mismatch error,
        not silently pass.
        """
        idat_offset, idat_length = self._locate_png_idat(signed_image)
        tampered = bytearray(signed_image)
        # Flip every byte in the IDAT chunk -- guarantees a real content
        # change regardless of compression/pixel layout specifics.
        for i in range(idat_offset, idat_offset + idat_length):
            tampered[i] ^= 0xFF

        validator = C2PAValidator()
        result = validator.validate_content(bytes(tampered))

        assert result.is_valid is False, (
            "TAMPER DETECTION FAILURE: modified pixel data was accepted "
            "as valid. A provenance system that cannot catch this is "
            "not fit for purpose."
        )
        assert result.status == ValidationStatus.TAMPERED_CONTENT
        assert any("dataHash" in e or "hash" in e.lower() for e in result.errors)

    def test_tampered_manifest_bytes_fail_validation(self, signed_image: bytes) -> None:
        """
        Corrupting bytes within the embedded JUMBF manifest store itself
        (as opposed to the image content) must also be detected -- this
        exercises the assertion/thumbnail hash-binding path rather than
        the top-level asset data-hash path.
        """
        import struct

        pos = 8
        cabx_offset = None
        cabx_length = None
        while pos + 8 <= len(signed_image):
            length = struct.unpack(">I", signed_image[pos:pos + 4])[0]
            ctype = signed_image[pos + 4:pos + 8]
            if ctype in (b"caBX", b"cAbX"):
                cabx_offset = pos + 8
                cabx_length = length
                break
            pos += 8 + length + 4
        assert cabx_offset is not None, "No C2PA JUMBF chunk found -- embedding did not run"

        tampered = bytearray(signed_image)
        # Corrupt deep inside the JUMBF payload (skip the first few KB,
        # which tends to be box-header/claim structure rather than
        # hashed assertion payload bytes) to reliably land inside a
        # hash-bound assertion (e.g. the embedded thumbnail).
        deep_offset = cabx_offset + min(20000, cabx_length // 2)
        for i in range(deep_offset, deep_offset + 200):
            tampered[i] ^= 0xFF

        validator = C2PAValidator()
        result = validator.validate_content(bytes(tampered))

        assert result.is_valid is False, (
            "TAMPER DETECTION FAILURE: modified manifest bytes were "
            "accepted as valid."
        )
        assert result.status == ValidationStatus.TAMPERED_CONTENT

    def test_untampered_image_still_valid_after_tamper_tests(
        self, signed_image: bytes
    ) -> None:
        """Sanity check: the original signed bytes (untouched) must
        still validate cleanly -- confirms the tamper tests above are
        actually detecting real modifications, not just always failing."""
        validator = C2PAValidator()
        result = validator.validate_content(signed_image)

        assert result.is_valid is True
        assert result.status == ValidationStatus.VALID

    def test_truncated_content_does_not_falsely_validate(self, signed_image: bytes) -> None:
        """Truncating a signed asset must not be reported as valid --
        either no manifest is found, or validation fails; it must never
        report is_valid=True on truncated data."""
        truncated = signed_image[: len(signed_image) // 2]
        validator = C2PAValidator()

        result = validator.validate_content(truncated)

        assert result.is_valid is False


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

    def test_validate_manifest_returns_real_result(
        self,
        validator: C2PAValidator
    ) -> None:
        """
        Manifest validation is implemented (Phase 6): it must return a
        real ValidationResult rather than raising NotImplementedError.
        A manifest missing required fields is correctly reported as
        invalid with descriptive errors.
        """
        result = validator.validate_manifest({"test": "manifest"})

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert any("claim_generator" in e for e in result.errors)

    def test_validate_manifest_well_formed_minimal(
        self,
        validator: C2PAValidator
    ) -> None:
        """A minimal but structurally complete manifest dict (as Reader
        would produce) is reported as valid at the structural level."""
        result = validator.validate_manifest({
            "claim_generator_info": [{"name": "test", "version": "1.0"}],
            "assertions": [],
            "title": "Minimal",
        })

        assert result.is_valid is True
        assert result.claim_generator == "test/1.0"

    def test_extract_manifest_no_manifest_present(
        self,
        validator: C2PAValidator
    ) -> None:
        """Content with no embedded C2PA manifest must return None, not
        raise or fabricate a manifest."""
        plain_png = _make_test_png()

        result = validator.extract_manifest(plain_png)

        assert result is None

    def test_validate_content_no_manifest_present(
        self,
        validator: C2PAValidator
    ) -> None:
        """Content with no embedded C2PA manifest must be reported as
        invalid (missing assertion / no manifest), not crash."""
        plain_png = _make_test_png()

        result = validator.validate_content(plain_png)

        assert result.is_valid is False
        assert result.status == ValidationStatus.MISSING_ASSERTION
