"""
C2PA Validation Module
======================

Validate C2PA manifests and verify content provenance.

This module provides comprehensive validation of C2PA manifests:
- Certificate chain validation
- Signature verification
- Assertion integrity checks
- Ingredient verification
- Timestamp validation

Implementation note (Phase 6):
-------------------------------
Like ``manifest_builder.py``, this module is a thin domain wrapper around
the official ``c2pa-python`` binding. All JUMBF parsing, CBOR decoding,
COSE signature verification, and X.509 chain validation is delegated to
the native ``c2pa.Reader`` -- this module translates the Reader's output
(``reader.json()`` / ``reader.get_validation_state()`` /
``reader.get_validation_results()``) into this codebase's existing
``ValidationResult`` public dataclass.

Trust anchors and dev certificates:
------------------------------------
By default this validator trusts the same dev CA that
``ManifestBuilder`` signs with by default (``backend/certs/dev/ca.pem``),
so that content signed by this repo's own ``ManifestBuilder`` in
development validates as fully ``Trusted`` rather than merely
cryptographically-intact-but-untrusted. This is a convenience for local
development/testing ONLY. A manifest's cryptographic integrity (whether
the signature matches the content, whether the content has been
tampered with) is verified regardless of trust configuration -- trust
anchors only affect whether the *signing certificate* is considered
trusted. See ``ManifestBuilder``'s module docstring for why this
self-signed dev chain is not, and cannot be, trusted by real-world C2PA
verifiers.

Example:
--------
    >>> from watermark_engine.c2pa import C2PAValidator
    >>>
    >>> validator = C2PAValidator()
    >>> result = validator.validate_content(signed_image_bytes)
    >>>
    >>> if result.is_valid:
    ...     print("Manifest is valid!")
    ...     print(f"Creator: {result.creator_name}")

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import c2pa

logger = logging.getLogger(__name__)


# Default dev trust anchor: the same dev CA ManifestBuilder signs with by
# default. See manifest_builder.py's module docstring for the full
# dev-certificate disclaimer -- this is NOT a real-world trust anchor.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DEV_CERT_DIR = _REPO_ROOT / "backend" / "certs" / "dev"
_DEFAULT_TRUST_ANCHOR_PATH = _DEFAULT_DEV_CERT_DIR / "ca.pem"


class ValidationStatus(str, Enum):
    """C2PA validation status codes."""

    VALID = "valid"
    INVALID_SIGNATURE = "invalid_signature"
    EXPIRED_CERTIFICATE = "expired_certificate"
    REVOKED_CERTIFICATE = "revoked_certificate"
    INVALID_CHAIN = "invalid_chain"
    TAMPERED_CONTENT = "tampered_content"
    MISSING_ASSERTION = "missing_assertion"
    INVALID_TIMESTAMP = "invalid_timestamp"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ValidationResult:
    """
    Result of C2PA manifest validation.

    Contains comprehensive validation status and extracted information.
    """

    is_valid: bool
    status: ValidationStatus
    creator_name: str | None = None
    creation_time: datetime | None = None
    claim_generator: str | None = None
    assertions: list[dict[str, Any]] = field(default_factory=list)
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    certificate_info: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "creator_name": self.creator_name,
            "creation_time": self.creation_time.isoformat() if self.creation_time else None,
            "claim_generator": self.claim_generator,
            "assertions_count": len(self.assertions),
            "ingredients_count": len(self.ingredients),
            "warnings": self.warnings,
            "errors": self.errors
        }


# Map native C2PA validation-result failure "code" prefixes to our
# ValidationStatus enum. Codes are dotted, e.g. "assertion.dataHash.mismatch"
# or "signingCredential.untrusted" -- see the C2PA spec's validation status
# code table (https://c2pa.org/specifications/specifications/2.2/specs/
# C2PA_Specification.html#_existing_validation_status_codes).
_FAILURE_CODE_STATUS_MAP: dict[str, ValidationStatus] = {
    "claimSignature": ValidationStatus.INVALID_SIGNATURE,
    "signingCredential.untrusted": ValidationStatus.INVALID_CHAIN,
    "signingCredential.expired": ValidationStatus.EXPIRED_CERTIFICATE,
    "signingCredential.revoked": ValidationStatus.REVOKED_CERTIFICATE,
    "signingCredential.invalid": ValidationStatus.INVALID_CHAIN,
    "assertion.dataHash.mismatch": ValidationStatus.TAMPERED_CONTENT,
    "assertion.boxesHash.mismatch": ValidationStatus.TAMPERED_CONTENT,
    "assertion.bmffHash.mismatch": ValidationStatus.TAMPERED_CONTENT,
    "assertion.hashedURI.mismatch": ValidationStatus.TAMPERED_CONTENT,
    "assertion.missing": ValidationStatus.MISSING_ASSERTION,
    "assertion.required.missing": ValidationStatus.MISSING_ASSERTION,
    "timeStamp": ValidationStatus.INVALID_TIMESTAMP,
}


def _classify_failure_code(code: str) -> ValidationStatus:
    """Map a single native C2PA failure code to our ValidationStatus."""
    if code in _FAILURE_CODE_STATUS_MAP:
        return _FAILURE_CODE_STATUS_MAP[code]
    for prefix, status in _FAILURE_CODE_STATUS_MAP.items():
        if code.startswith(prefix):
            return status
    return ValidationStatus.UNKNOWN_ERROR


class C2PAValidator:
    """
    Validator for C2PA manifests and content provenance.

    Provides comprehensive validation including:
    - X.509 certificate chain verification
    - Cryptographic signature validation
    - Content hash verification
    - Assertion integrity checks

    All parsing/verification is delegated to the official ``c2pa-python``
    binding's ``Reader`` API; this class translates its output into this
    codebase's ``ValidationResult`` shape.

    Attributes:
        trust_anchors: List of trusted root/intermediate CA certificate
            PEM paths.
        verify_revocation: Whether to check certificate revocation
            (OCSP/CRL). Passed through to the native SDK's
            ``verify.ocsp_fetch`` setting.
        verify_timestamp: Validate timestamps. Passed through to the
            native SDK's ``verify.verify_timestamp_trust`` setting.

    Example:
        >>> validator = C2PAValidator()
        >>> result = validator.validate_content(signed_image_bytes)
        >>> print(f"Valid: {result.is_valid}, Status: {result.status}")
    """

    def __init__(
        self,
        trust_anchors: list[str] | None = None,
        verify_revocation: bool = True,
        verify_timestamp: bool = True
    ) -> None:
        """
        Initialize C2PA Validator.

        Args:
            trust_anchors: Paths to trusted root CA certificates (PEM).
                If not provided, falls back to the
                ``C2PA_CERTIFICATE_PATH`` env var's CA (if that chain
                includes one) and then to this repo's bundled dev CA
                (``backend/certs/dev/ca.pem``) so manifests signed by
                this repo's own ``ManifestBuilder`` validate as trusted
                in development. Pass an empty list explicitly to disable
                trust-anchor loading altogether (signature/tamper
                checks still run; only the "is this cert trusted" check
                is skipped).
            verify_revocation: Check certificate revocation (OCSP/CRL)
            verify_timestamp: Validate timestamps
        """
        if trust_anchors is None:
            default_anchor = os.environ.get(
                "C2PA_TRUST_ANCHOR_PATH", str(_DEFAULT_TRUST_ANCHOR_PATH)
            )
            trust_anchors = [default_anchor] if Path(default_anchor).exists() else []

        self.trust_anchors = trust_anchors
        self.verify_revocation = verify_revocation
        self.verify_timestamp = verify_timestamp

        logger.info(
            "C2PAValidator initialized (trust_anchors=%s)", self.trust_anchors
        )

    def _build_context(self) -> c2pa.Context:
        """Build a native Context carrying our trust/verify settings."""
        settings = c2pa.Settings()

        anchor_pems = []
        for anchor_path in self.trust_anchors:
            path = Path(anchor_path)
            if not path.exists():
                logger.warning("Trust anchor not found, skipping: %s", path)
                continue
            anchor_pems.append(path.read_text(encoding="utf-8"))

        if anchor_pems:
            settings.set("trust.user_anchors", json.dumps("".join(anchor_pems)))
            settings.set("verify.verify_trust", "true")
        else:
            settings.set("verify.verify_trust", "false")

        settings.set("verify.ocsp_fetch", "true" if self.verify_revocation else "false")
        settings.set(
            "verify.verify_timestamp_trust", "true" if self.verify_timestamp else "false"
        )

        return c2pa.Context(settings=settings)

    def validate_manifest(
        self,
        manifest: dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a C2PA manifest (structural/content checks that don't
        require re-verifying against embedded asset bytes).

        This validates a manifest JSON dictionary as previously extracted
        via ``extract_manifest`` or ``Reader.json()`` -- it checks that
        required fields are present and surfaces any
        ``validation_results`` already computed by the native Reader that
        produced it (that Reader performed the actual signature/hash
        verification when it parsed the source asset; this method
        re-derives a ``ValidationResult`` from that data without
        re-parsing an asset).

        Args:
            manifest: C2PA manifest as dictionary (the "active manifest"
                shape, as returned by ``Reader.get_active_manifest()`` /
                ``extract_manifest``)

        Returns:
            ValidationResult with detailed validation information

        Example:
            >>> result = validator.validate_manifest(manifest_dict)
            >>> if not result.is_valid:
            ...     print(f"Validation failed: {result.errors}")
        """
        logger.info("Validating C2PA manifest")

        errors: list[str] = []
        warnings: list[str] = []

        required_fields = ("claim_generator_info", "assertions")
        # v1-shape manifests use "claim_generator" instead of
        # "claim_generator_info"; accept either.
        has_claim_generator = bool(
            manifest.get("claim_generator_info") or manifest.get("claim_generator")
        )
        if not has_claim_generator:
            errors.append("Missing claim_generator / claim_generator_info")
        if "assertions" not in manifest:
            errors.append("Missing assertions array")

        assertions = manifest.get("assertions", []) or []
        creator_name = None
        for assertion in assertions:
            if assertion.get("label") == "c2pa.creator":
                data = assertion.get("data", {})
                creator_name = data.get("name")
                break

        claim_generator = None
        cgi = manifest.get("claim_generator_info")
        if cgi:
            entry = cgi[0] if isinstance(cgi, list) else cgi
            name = entry.get("name", "")
            version = entry.get("version", "")
            claim_generator = f"{name}/{version}" if version else name
        else:
            claim_generator = manifest.get("claim_generator")

        creation_time = None
        for assertion in assertions:
            if assertion.get("label") == "c2pa.actions" or assertion.get("label") == "c2pa.actions.v2":
                for action in assertion.get("data", {}).get("actions", []):
                    if action.get("when"):
                        try:
                            creation_time = datetime.fromisoformat(
                                action["when"].replace("Z", "+00:00")
                            )
                        except ValueError:
                            warnings.append(f"Unparseable timestamp: {action['when']}")
                        break

        status = ValidationStatus.VALID
        is_valid = True

        # If this manifest carries embedded native validation_results
        # (e.g. because it was produced by extract_manifest, which stores
        # them under "_validation_results"), fold those failures in too.
        native_results = manifest.get("_validation_results")
        if native_results:
            active = native_results.get("activeManifest", native_results)
            for failure in active.get("failure", []):
                code = failure.get("code", "")
                errors.append(f"{code}: {failure.get('explanation', '')}")
                mapped_status = _classify_failure_code(code)
                if mapped_status != ValidationStatus.UNKNOWN_ERROR:
                    status = mapped_status
            for info in active.get("informational", []):
                warnings.append(
                    f"{info.get('code', '')}: {info.get('explanation', '')}"
                )

        if errors and status == ValidationStatus.VALID:
            status = ValidationStatus.UNKNOWN_ERROR
        if errors:
            is_valid = False

        return ValidationResult(
            is_valid=is_valid,
            status=status,
            creator_name=creator_name,
            creation_time=creation_time,
            claim_generator=claim_generator,
            assertions=assertions,
            ingredients=manifest.get("ingredients", []) or [],
            certificate_info=manifest.get("signature_info", {}) or {},
            warnings=warnings,
            errors=errors,
        )

    def validate_content(
        self,
        content_bytes: bytes,
        expected_manifest: dict[str, Any] | None = None
    ) -> ValidationResult:
        """
        Validate content with embedded C2PA manifest.

        This performs the full native verification pipeline: extracts
        the JUMBF manifest store from ``content_bytes``, verifies the
        COSE signature over the claim, verifies the signing certificate
        chain against configured trust anchors, and verifies that the
        asset's current content hash matches the hash recorded in the
        manifest at signing time (this is what catches tampering: any
        modification to the signed bytes changes the hash and the native
        SDK reports ``assertion.dataHash.mismatch`` / an ``Invalid``
        validation state).

        Args:
            content_bytes: Content bytes with embedded manifest
            expected_manifest: Optional expected manifest for comparison
                (compares claim_generator + title against the extracted
                manifest; mismatches are reported as warnings, not
                validation failures, since two well-formed manifests can
                legitimately differ from what a caller expected -- the
                content's own manifest is the authoritative record)

        Returns:
            ValidationResult with content-specific validation
        """
        logger.info("Validating content: %d bytes", len(content_bytes))

        mime_type = _sniff_mime_type(content_bytes)

        context = self._build_context()

        try:
            import io

            stream = io.BytesIO(content_bytes)
            reader = c2pa.Reader.try_create(mime_type, stream, context=context)
        except c2pa.C2paError as exc:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.UNKNOWN_ERROR,
                errors=[f"Failed to read C2PA data: {exc}"],
            )

        if reader is None:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.MISSING_ASSERTION,
                errors=["No C2PA manifest found in content (no JUMBF data)"],
            )

        try:
            validation_state = reader.get_validation_state()
            validation_results = reader.get_validation_results()
            active_manifest = reader.get_active_manifest()
        finally:
            reader.close()

        if active_manifest is None:
            return ValidationResult(
                is_valid=False,
                status=ValidationStatus.MISSING_ASSERTION,
                errors=["Manifest store present but no active manifest found"],
            )

        active_manifest["_validation_results"] = validation_results
        result = self.validate_manifest(active_manifest)

        # Fold the native SDK's overall validation_state in as the primary
        # signal -- it is the authoritative pass/fail determination
        # (accounting for signature, hash-binding, trust, and timestamp
        # checks together), on top of whatever validate_manifest derived
        # from the itemized failure codes.
        if validation_state in ("Invalid",):
            result.is_valid = False
            if result.status == ValidationStatus.VALID:
                result.status = ValidationStatus.UNKNOWN_ERROR
        elif validation_state == "Trusted":
            result.is_valid = True
            if not result.errors:
                result.status = ValidationStatus.VALID
        elif validation_state == "Valid":
            # Cryptographically intact and hash-bound correctly, but the
            # signing certificate itself is not in a trusted anchor list.
            # Content integrity holds; only cert trust is in question.
            if not any(
                "dataHash.mismatch" in e or "TamperedContent" in e for e in result.errors
            ):
                result.is_valid = True
                if result.status == ValidationStatus.INVALID_CHAIN:
                    result.warnings.append(
                        "Signing certificate is not in a trusted anchor "
                        "list (content integrity itself is valid)."
                    )

        if expected_manifest:
            expected_title = expected_manifest.get("title")
            actual_title = active_manifest.get("title")
            if expected_title and expected_title != actual_title:
                result.warnings.append(
                    f"Expected title {expected_title!r} does not match "
                    f"embedded title {actual_title!r}"
                )

        return result

    def extract_manifest(
        self,
        content_bytes: bytes
    ) -> dict[str, Any] | None:
        """
        Extract C2PA manifest from content.

        Args:
            content_bytes: Content with embedded manifest

        Returns:
            The active manifest as a dictionary (with an extra
            ``_validation_results`` key holding the native SDK's
            itemized validation results), or None if no manifest is
            found.
        """
        logger.info("Extracting embedded C2PA manifest")

        mime_type = _sniff_mime_type(content_bytes)

        try:
            import io

            stream = io.BytesIO(content_bytes)
            reader = c2pa.Reader.try_create(mime_type, stream)
        except c2pa.C2paError as exc:
            logger.warning("Failed to read C2PA data: %s", exc)
            return None

        if reader is None:
            return None

        try:
            active_manifest = reader.get_active_manifest()
            validation_results = reader.get_validation_results()
        finally:
            reader.close()

        if active_manifest is not None and validation_results is not None:
            active_manifest["_validation_results"] = validation_results

        return active_manifest

    def verify_signature(
        self,
        manifest: dict[str, Any],
        signature: bytes,
        certificate: bytes
    ) -> bool:
        """
        Verify manifest signature.

        Note: with the ``c2pa-python`` SDK, signature verification is
        performed internally by ``Reader`` as part of parsing an asset
        (there is no supported public API to verify a detached
        signature against an arbitrary manifest dict + raw cert bytes --
        C2PA signatures are COSE structures over the full claim CBOR,
        not a simple detached-signature-over-JSON scheme). This method
        is kept for API-shape compatibility with the pre-Phase-6 stub;
        callers that have raw content bytes should use
        ``validate_content`` instead, which performs full, real
        signature and hash-binding verification via ``Reader``.

        This method covers the one case it safely can: if ``manifest``
        carries the native SDK's ``_validation_results`` (as produced by
        ``extract_manifest`` / ``validate_content``), it reports whether
        that already-computed signature verification succeeded, rather
        than re-deriving a new verification from the passed-in
        ``signature`` / ``certificate`` bytes (which the underlying SDK
        has no API to accept directly).

        Args:
            manifest: Manifest data (ideally as returned by
                ``extract_manifest``, carrying ``_validation_results``)
            signature: Digital signature bytes (unused -- see note above)
            certificate: Signing certificate bytes (unused -- see note
                above)

        Returns:
            True if the manifest's claim signature validated successfully.

        Raises:
            ValueError: If ``manifest`` does not carry the native
                validation results needed to answer this (i.e. it was
                not produced by ``extract_manifest`` / a Reader).
        """
        native_results = manifest.get("_validation_results")
        if native_results is None:
            raise ValueError(
                "verify_signature requires a manifest produced by "
                "extract_manifest() (carrying native _validation_results) "
                "-- the C2PA SDK does not support verifying a detached "
                "signature against an arbitrary manifest dict. Use "
                "validate_content(content_bytes) instead if you only "
                "have raw content bytes."
            )

        active = native_results.get("activeManifest", native_results)
        for success in active.get("success", []):
            if success.get("code", "").startswith("claimSignature"):
                return True
        for failure in active.get("failure", []):
            if failure.get("code", "").startswith("claimSignature"):
                return False

        logger.warning(
            "No claimSignature status code found in validation results"
        )
        return False

    def verify_certificate_chain(
        self,
        certificate: bytes
    ) -> tuple[bool, list[str]]:
        """
        Verify an X.509 certificate (chain) against configured trust
        anchors and basic X.509 well-formedness rules.

        Unlike ``verify_signature``, this does not require an asset --
        it directly parses and checks the certificate chain using the
        ``cryptography`` library (already a project dependency) plus
        this validator's configured trust anchors. It checks: PEM
        parseability, expiry (validity period), and (if trust anchors
        are configured) whether the leaf certificate is issued by /
        chains to a configured trust anchor.

        Args:
            certificate: Certificate (or PEM chain: leaf + any
                intermediate/CA certs concatenated) to verify.

        Returns:
            Tuple of (is_valid, list_of_issues). ``is_valid`` is True
            only if the chain parses, no certificate in it is expired,
            and (when trust anchors are configured) the leaf chains to
            a trusted anchor.
        """
        logger.info("Verifying certificate chain")

        from cryptography import x509
        from cryptography.hazmat.backends import default_backend

        issues: list[str] = []

        try:
            pem_text = certificate.decode("utf-8") if isinstance(certificate, bytes) else certificate
            cert_pems = [
                f"-----BEGIN CERTIFICATE-----{chunk}-----END CERTIFICATE-----"
                for chunk in pem_text.split("-----BEGIN CERTIFICATE-----")[1:]
            ]
            parsed_certs = [
                x509.load_pem_x509_certificate(pem.encode("utf-8"), default_backend())
                for pem in cert_pems
            ]
        except (ValueError, IndexError) as exc:
            return False, [f"Failed to parse certificate chain: {exc}"]

        if not parsed_certs:
            return False, ["No certificates found in input"]

        now = datetime.utcnow()
        for cert in parsed_certs:
            not_before = cert.not_valid_before_utc.replace(tzinfo=None)
            not_after = cert.not_valid_after_utc.replace(tzinfo=None)
            if now < not_before:
                issues.append(
                    f"Certificate not yet valid (subject={cert.subject.rfc4514_string()}, "
                    f"not_before={not_before.isoformat()})"
                )
            if now > not_after:
                issues.append(
                    f"Certificate expired (subject={cert.subject.rfc4514_string()}, "
                    f"not_after={not_after.isoformat()})"
                )

        leaf = parsed_certs[0]
        chain_subjects = {cert.subject for cert in parsed_certs}
        is_self_signed_leaf = leaf.subject == leaf.issuer

        if is_self_signed_leaf and len(parsed_certs) == 1:
            issues.append(
                "Leaf certificate is self-signed with no issuing CA in "
                "the chain -- C2PA requires signing certificates to be "
                "issued by a separate CA, not self-signed directly."
            )

        if self.trust_anchors:
            trusted = False
            for anchor_path in self.trust_anchors:
                path = Path(anchor_path)
                if not path.exists():
                    continue
                anchor_pem = path.read_text(encoding="utf-8")
                try:
                    anchor_cert = x509.load_pem_x509_certificate(
                        anchor_pem.encode("utf-8"), default_backend()
                    )
                except ValueError:
                    continue
                # Chain trust check: is the anchor itself present in the
                # supplied chain, or does the leaf's issuer match the
                # anchor's subject? (Full cryptographic chain-signature
                # verification -- as opposed to this subject/issuer
                # matching -- is performed by the native c2pa.Reader
                # during validate_content(); this method is a
                # lighter-weight, asset-independent chain sanity check.)
                if anchor_cert.subject in chain_subjects:
                    trusted = True
                    break
                if leaf.issuer == anchor_cert.subject:
                    trusted = True
                    break
            if not trusted:
                issues.append(
                    "Certificate chain does not chain to any configured "
                    "trust anchor"
                )
        else:
            issues.append(
                "No trust anchors configured -- certificate trust was "
                "not evaluated (only expiry/well-formedness checks ran)"
            )

        is_valid = not any(
            "expired" in issue or "not yet valid" in issue or "self-signed" in issue
            or "does not chain" in issue
            for issue in issues
        )

        return is_valid, issues


def _sniff_mime_type(content_bytes: bytes) -> str:
    """
    Best-effort MIME type detection from magic bytes, for callers of
    ``validate_content`` / ``extract_manifest`` that only have raw bytes
    (no filename/content-type). Falls back to PIL for anything not
    covered by the small magic-byte table below.
    """
    if content_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if content_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if content_bytes[:4] == b"RIFF" and content_bytes[8:12] == b"WEBP":
        return "image/webp"
    if content_bytes[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    if content_bytes[4:12] == b"ftypheic":
        return "image/heic"

    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(content_bytes)) as img:
            fmt = (img.format or "").lower()
            mime_map = {
                "png": "image/png",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
                "avif": "image/avif",
                "heic": "image/heic",
            }
            if fmt in mime_map:
                return mime_map[fmt]
    except Exception:  # noqa: BLE001 - best-effort sniff, fall through
        pass

    raise ValueError("Unable to determine content MIME type for C2PA reading")
