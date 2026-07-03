"""
C2PA (Coalition for Content Provenance and Authenticity) Package
=================================================================

C2PA manifest creation and validation for Tastefully Stained.

This package implements C2PA Version 2.0 specification for:
- Content credentials manifest creation
- Assertion embedding and validation
- Certificate management
- Provenance chain verification

C2PA provides a technical standard for certifying the source and
history of media content, establishing trust in digital media.

Real implementation (Phase 6): both ``ManifestBuilder`` and
``C2PAValidator`` are thin domain wrappers around the official
``c2pa-python`` binding (https://github.com/contentauth/c2pa-python) --
see the module docstrings in ``manifest_builder.py`` / ``validation.py``
for details, including the development-only self-signed certificate
disclaimer.

Example:
--------
    >>> from watermark_engine.c2pa import ManifestBuilder, C2PAValidator
    >>> from watermark_engine.c2pa import CreatorAssertion, WatermarkAssertion
    >>>
    >>> builder = ManifestBuilder()  # uses backend/certs/dev/ by default
    >>> manifest = builder.create_manifest(
    ...     content_bytes=image_bytes,
    ...     title="My Image",
    ...     assertions=[
    ...         CreatorAssertion(name="Artist Name"),
    ...         WatermarkAssertion(
    ...             watermark_hash="sha256:...", strategy="hybrid", strength=0.5
    ...         ),
    ...     ],
    ... )
    >>> manifest = builder.sign_manifest(manifest)
    >>> signed_bytes = builder.embed_manifest(image_bytes, manifest)
    >>>
    >>> validator = C2PAValidator()
    >>> result = validator.validate_content(signed_bytes)
    >>> print(result.is_valid, result.status)

References:
-----------
- C2PA Specification: https://c2pa.org/specifications/
- C2PA GitHub: https://github.com/c2pa-org/c2pa-rs
- c2pa-python binding: https://github.com/contentauth/c2pa-python
"""

from watermark_engine.c2pa.manifest_builder import (
    ActionsAssertion,
    Assertion,
    AssertionType,
    C2PAManifest,
    CreatorAssertion,
    ManifestBuilder,
    WatermarkAssertion,
)
from watermark_engine.c2pa.validation import (
    C2PAValidator,
    ValidationResult,
    ValidationStatus,
)

__all__ = [
    "ManifestBuilder",
    "C2PAValidator",
    "C2PAManifest",
    "Assertion",
    "AssertionType",
    "CreatorAssertion",
    "WatermarkAssertion",
    "ActionsAssertion",
    "ValidationResult",
    "ValidationStatus",
]
