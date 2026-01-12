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

Example:
--------
    >>> from watermark_engine.c2pa import ManifestBuilder, C2PAValidator
    >>> 
    >>> builder = ManifestBuilder(certificate_path="./certs/signing.pem")
    >>> manifest = builder.create_manifest(
    ...     content_hash="sha256:...",
    ...     assertions=[creator_assertion, watermark_assertion]
    ... )
    >>> 
    >>> validator = C2PAValidator()
    >>> is_valid = validator.validate_manifest(manifest)

References:
-----------
- C2PA Specification: https://c2pa.org/specifications/
- C2PA GitHub: https://github.com/c2pa-org/c2pa-rs
"""

from watermark_engine.c2pa.manifest_builder import ManifestBuilder
from watermark_engine.c2pa.validation import C2PAValidator

__all__ = [
    "ManifestBuilder",
    "C2PAValidator",
]
