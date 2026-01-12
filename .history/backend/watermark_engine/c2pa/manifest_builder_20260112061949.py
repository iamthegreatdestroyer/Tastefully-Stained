"""
C2PA Manifest Builder Module
============================

Create C2PA-compliant content credentials manifests.

This module implements the C2PA Version 2.0 specification for
creating signed manifests that establish content provenance.

Features:
---------
- Manifest creation with required claims
- Assertion embedding (creator, actions, watermark)
- X.509 certificate-based signing
- JUMBF (JPEG Universal Metadata Box Format) encoding
- Ingredient chain management

C2PA Manifest Structure:
------------------------
- claim_generator: Identifies the creating software
- title: Content title
- format: MIME type
- instance_id: Unique identifier
- assertions: Array of provenance assertions
- signature_info: Digital signature data

Example:
--------
    >>> from watermark_engine.c2pa import ManifestBuilder
    >>> 
    >>> builder = ManifestBuilder(
    ...     certificate_path="./certs/signing.pem",
    ...     private_key_path="./certs/signing.key"
    ... )
    >>> 
    >>> manifest = builder.create_manifest(
    ...     content_bytes=image_bytes,
    ...     title="Watermarked Image",
    ...     assertions=[
    ...         CreatorAssertion(name="Artist Name"),
    ...         WatermarkAssertion(data="0x123...")
    ...     ]
    ... )

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AssertionType(str, Enum):
    """C2PA assertion types."""
    
    CREATOR = "c2pa.creator"
    ACTIONS = "c2pa.actions"
    INGREDIENT = "c2pa.ingredient"
    WATERMARK = "tastefully-stained.watermark"
    METADATA = "stds.exif"
    CUSTOM = "custom"


@dataclass
class Assertion:
    """
    Base class for C2PA assertions.
    
    Assertions are claims about the content's creation or modification.
    """
    
    label: str
    assertion_type: AssertionType
    data: dict[str, Any]
    is_redactable: bool = False


@dataclass
class CreatorAssertion(Assertion):
    """Creator identity assertion."""
    
    def __init__(self, name: str, identifier: str | None = None):
        super().__init__(
            label="c2pa.creator",
            assertion_type=AssertionType.CREATOR,
            data={
                "@type": "Person",
                "name": name,
                "identifier": identifier or ""
            }
        )


@dataclass
class WatermarkAssertion(Assertion):
    """Watermark embedding assertion."""
    
    def __init__(
        self,
        watermark_hash: str,
        strategy: str,
        strength: float
    ):
        super().__init__(
            label="tastefully-stained.watermark",
            assertion_type=AssertionType.WATERMARK,
            data={
                "watermark_hash": watermark_hash,
                "strategy": strategy,
                "strength": strength,
                "algorithm_version": "1.0.0"
            }
        )


@dataclass
class C2PAManifest:
    """
    C2PA manifest data structure.
    
    Represents a complete C2PA manifest ready for embedding.
    """
    
    claim_generator: str = "Tastefully-Stained/0.1.0"
    title: str = ""
    format: str = "image/png"
    instance_id: str = field(default_factory=lambda: f"xmp.iid:{uuid.uuid4()}")
    assertions: list[Assertion] = field(default_factory=list)
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    signature: bytes | None = None
    is_signed: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert manifest to dictionary representation."""
        return {
            "claim_generator": self.claim_generator,
            "title": self.title,
            "format": self.format,
            "instance_id": self.instance_id,
            "assertions": [
                {
                    "label": a.label,
                    "data": a.data,
                    "is_redactable": a.is_redactable
                }
                for a in self.assertions
            ],
            "ingredients": self.ingredients,
            "signature_info": {
                "alg": "ES256",
                "issuer": "Tastefully Stained",
                "time": self.created.isoformat()
            }
        }


class ManifestBuilder:
    """
    Builder for C2PA-compliant content credentials manifests.
    
    Creates, signs, and embeds C2PA manifests in image content
    following the C2PA Version 2.0 specification.
    
    Attributes:
        certificate_path: Path to X.509 signing certificate
        private_key_path: Path to private key for signing
    
    Example:
        >>> builder = ManifestBuilder("cert.pem", "key.pem")
        >>> manifest = builder.create_manifest(image_bytes, "My Image")
    """
    
    # Supported formats for C2PA embedding
    SUPPORTED_FORMATS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/avif": ".avif",
        "image/heic": ".heic",
        "video/mp4": ".mp4",
    }
    
    def __init__(
        self,
        certificate_path: str | None = None,
        private_key_path: str | None = None,
        claim_generator: str = "Tastefully-Stained/0.1.0"
    ) -> None:
        """
        Initialize Manifest Builder.
        
        Args:
            certificate_path: Path to X.509 signing certificate
            private_key_path: Path to private key (PEM format)
            claim_generator: Claim generator identifier string
        """
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.claim_generator = claim_generator
        
        logger.info("ManifestBuilder initialized")
    
    def create_manifest(
        self,
        content_bytes: bytes,
        title: str,
        mime_type: str = "image/png",
        assertions: list[Assertion] | None = None,
        ingredients: list[dict[str, Any]] | None = None
    ) -> C2PAManifest:
        """
        Create a C2PA manifest for content.
        
        Args:
            content_bytes: Raw content bytes
            title: Content title
            mime_type: Content MIME type
            assertions: List of assertions to include
            ingredients: Ingredient manifests (for derived content)
        
        Returns:
            C2PAManifest ready for signing and embedding
        
        Raises:
            ValueError: If mime_type is not supported
        
        Example:
            >>> manifest = builder.create_manifest(
            ...     content_bytes=image_bytes,
            ...     title="Watermarked Photo",
            ...     mime_type="image/jpeg"
            ... )
        """
        # TODO: Implement manifest creation in Phase 3
        if mime_type not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {mime_type}")
        
        logger.info(f"Creating manifest for: {title}")
        raise NotImplementedError("Manifest creation will be implemented in Phase 3")
    
    def sign_manifest(self, manifest: C2PAManifest) -> C2PAManifest:
        """
        Sign manifest with X.509 certificate.
        
        Args:
            manifest: Unsigned C2PA manifest
        
        Returns:
            Signed C2PA manifest
        
        Raises:
            ValueError: If certificate not configured
        """
        # TODO: Implement signing in Phase 3
        logger.info("Signing C2PA manifest")
        raise NotImplementedError("Manifest signing will be implemented in Phase 3")
    
    def embed_manifest(
        self,
        content_bytes: bytes,
        manifest: C2PAManifest
    ) -> bytes:
        """
        Embed manifest into content using JUMBF.
        
        Args:
            content_bytes: Original content bytes
            manifest: Signed C2PA manifest
        
        Returns:
            Content bytes with embedded manifest
        """
        # TODO: Implement embedding in Phase 3
        logger.info("Embedding C2PA manifest in content")
        raise NotImplementedError("Manifest embedding will be implemented in Phase 3")
    
    @staticmethod
    def compute_content_hash(content_bytes: bytes) -> str:
        """
        Compute SHA-256 hash of content.
        
        Args:
            content_bytes: Raw content bytes
        
        Returns:
            SHA-256 hash as hex string with 'sha256:' prefix
        """
        hash_value = hashlib.sha256(content_bytes).hexdigest()
        return f"sha256:{hash_value}"
