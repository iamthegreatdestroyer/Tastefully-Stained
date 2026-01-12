# Tastefully Stained - Architecture

## System Overview

Tastefully Stained is a C2PA-compliant content watermarking service with hybrid DCT/DWT algorithms and blockchain anchoring.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TASTEFULLY STAINED                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│   │   Frontend  │────▶│   Backend   │────▶│  Blockchain │          │
│   │   (React)   │     │  (FastAPI)  │     │  (Ethereum) │          │
│   └─────────────┘     └──────┬──────┘     └─────────────┘          │
│                              │                                      │
│                              ▼                                      │
│                  ┌───────────────────────┐                         │
│                  │   Watermark Engine    │                         │
│                  │  ┌─────┐ ┌─────┐     │                         │
│                  │  │ DCT │ │ DWT │     │                         │
│                  │  └──┬──┘ └──┬──┘     │                         │
│                  │     └───┬───┘        │                         │
│                  │     ┌───┴───┐        │                         │
│                  │     │Hybrid │        │                         │
│                  │     └───────┘        │                         │
│                  └───────────────────────┘                         │
│                                                                     │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│   │    C2PA     │     │    IPFS     │     │  PostgreSQL │          │
│   │  Manifest   │     │   Storage   │     │   Database  │          │
│   └─────────────┘     └─────────────┘     └─────────────┘          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Backend (Python/FastAPI)

```
backend/
├── watermark_engine/
│   ├── core/                 # Watermarking algorithms
│   │   ├── dct_processor.py  # DCT (frequency domain)
│   │   ├── dwt_processor.py  # DWT (wavelet domain)
│   │   └── hybrid_algorithm.py
│   ├── api/                  # REST API
│   │   ├── routes.py         # Endpoint definitions
│   │   ├── models.py         # Pydantic models
│   │   └── middleware.py     # CORS, auth, logging
│   ├── blockchain/           # Web3 integration
│   │   ├── ethereum_anchor.py
│   │   └── ipfs_handler.py
│   ├── c2pa/                 # Content Authenticity
│   │   ├── manifest_builder.py
│   │   └── validation.py
│   └── utils/                # Shared utilities
│       ├── config.py
│       ├── logger.py
│       └── image_loader.py
└── tests/                    # Test suite
```

### Watermarking Algorithms

#### DCT (Discrete Cosine Transform)

- JPEG-compression resistant
- Embeds in frequency domain
- Best for photographic content

#### DWT (Discrete Wavelet Transform)

- Scaling/rotation resistant
- Multi-level decomposition
- Best for geometric transformations

#### Hybrid Strategy

- Automatic algorithm selection
- Image analysis for optimal choice
- Redundant embedding for robustness

## Data Flow

### Watermark Embedding

```
1. Upload Image
       │
       ▼
2. Image Analysis
   (determine optimal strategy)
       │
       ▼
3. Watermark Embedding
   (DCT, DWT, or Hybrid)
       │
       ▼
4. C2PA Manifest Creation
   (content credentials)
       │
       ▼
5. Blockchain Anchoring (optional)
   (immutable proof)
       │
       ▼
6. Return Watermarked Image + Metadata
```

### Watermark Verification

```
1. Upload Image
       │
       ▼
2. Extract C2PA Manifest
       │
       ▼
3. Verify Blockchain Anchor
       │
       ▼
4. Extract Watermark Data
       │
       ▼
5. Validate Integrity
       │
       ▼
6. Return Verification Result
```

## Technology Stack

| Layer        | Technology                       |
| ------------ | -------------------------------- |
| Frontend     | React, TypeScript, TailwindCSS   |
| Backend      | Python, FastAPI, Uvicorn         |
| Watermarking | NumPy, SciPy, PyWavelets, OpenCV |
| Blockchain   | Ethereum, Solidity, Web3.py      |
| Storage      | PostgreSQL, Redis, IPFS          |
| Container    | Docker, Docker Compose           |
| CI/CD        | GitHub Actions                   |

## Security Considerations

1. **API Authentication**: API key + rate limiting
2. **Input Validation**: Pydantic models, file type verification
3. **Blockchain Keys**: Secure key management (HSM recommended)
4. **C2PA Signing**: X.509 certificate chain
5. **CORS**: Configurable origins
