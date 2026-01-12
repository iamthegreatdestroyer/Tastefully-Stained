# Tastefully Stained - C2PA Specification Implementation

## Overview

This document describes how Tastefully Stained implements the C2PA (Coalition for Content Provenance and Authenticity) specification version 2.0 for content credentials.

## What is C2PA?

C2PA is an open technical standard for certifying the source and history of media content. It provides:

- **Provenance**: Track the origin and history of content
- **Authenticity**: Verify content hasn't been tampered with
- **Attribution**: Identify creators and editors

## Manifest Structure

### Top-Level Structure

```json
{
  "claim_generator": "Tastefully-Stained/0.1.0",
  "title": "Watermarked Image",
  "format": "image/jpeg",
  "instance_id": "xmp.iid:abc123",
  "assertions": [...],
  "ingredients": [...],
  "signature_info": {...}
}
```

### Assertions

#### Creator Assertion

```json
{
  "label": "c2pa.creator",
  "data": {
    "@type": "Person",
    "name": "Creator Name",
    "identifier": "creator@example.com"
  }
}
```

#### Watermark Assertion (Tastefully Stained Extension)

```json
{
  "label": "tastefully-stained.watermark",
  "data": {
    "watermark_hash": "sha256:abc123...",
    "strategy": "hybrid",
    "strength": 0.5,
    "algorithm_version": "1.0.0"
  }
}
```

#### Actions Assertion

```json
{
  "label": "c2pa.actions",
  "data": {
    "actions": [
      {
        "action": "c2pa.watermarked",
        "when": "2024-01-01T00:00:00Z",
        "softwareAgent": "Tastefully-Stained/0.1.0"
      }
    ]
  }
}
```

## Ingredients

For derived content, ingredients reference the source materials:

```json
{
  "ingredients": [
    {
      "title": "Original Image",
      "format": "image/jpeg",
      "document_id": "xmp.did:original123",
      "instance_id": "xmp.iid:original123",
      "relationship": "parentOf"
    }
  ]
}
```

## Signature

Manifests are signed using X.509 certificates:

```json
{
  "signature_info": {
    "alg": "ES256",
    "issuer": "Tastefully Stained",
    "cert_chain": ["...base64 encoded certificate chain..."],
    "time": "2024-01-01T00:00:00Z"
  }
}
```

## JUMBF Encoding

Manifests are embedded in images using JUMBF (JPEG Universal Metadata Box Format):

1. Manifest is serialized to CBOR
2. CBOR is wrapped in JUMBF boxes
3. JUMBF is embedded in image metadata
4. Image hash is computed and included in signature

## Validation Process

1. **Extract JUMBF** from image metadata
2. **Parse manifest** from JUMBF
3. **Verify signature** using certificate chain
4. **Validate certificate** against trust list
5. **Compute hash** of image content
6. **Compare hash** with signed hash in manifest
7. **Check timestamp** for expiration

## Implementation Status

| Feature | Status |
|---------|--------|
| Manifest Creation | 🔄 Phase 3 |
| Assertion Building | 🔄 Phase 3 |
| Certificate Signing | 🔄 Phase 3 |
| JUMBF Encoding | 🔄 Phase 3 |
| Manifest Validation | 🔄 Phase 3 |
| Certificate Validation | 🔄 Phase 3 |
| Ingredient Chains | 📋 Planned |
| Hard Binding | 📋 Planned |

## References

- [C2PA Specification](https://c2pa.org/specifications/)
- [C2PA GitHub](https://github.com/c2pa-org)
- [JUMBF ISO Standard](https://www.iso.org/standard/74417.html)
