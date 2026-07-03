# 🎨 Tastefully Stained

<div align="center">

**AI Content Provenance & Watermarking Service**

[![CI/CD Pipeline](https://github.com/iamthegreatdestroyer/Tastefully-Stained/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/iamthegreatdestroyer/Tastefully-Stained/actions)
[![Coverage](https://codecov.io/gh/iamthegreatdestroyer/Tastefully-Stained/branch/main/graph/badge.svg)](https://codecov.io/gh/iamthegreatdestroyer/Tastefully-Stained)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![C2PA Compliant](https://img.shields.io/badge/C2PA-v2.0-green.svg)](https://c2pa.org/)

*Invisible watermarking with blockchain-anchored provenance for AI-generated content*

[Features](#features) • [Quick Start](#quick-start) • [Documentation](#documentation) • [API Reference](#api-reference) • [Contributing](#contributing)

</div>

---

> **Current status (2026-07-03):** the watermarking, C2PA manifest, and
> blockchain/IPFS anchoring logic described below is not yet implemented
> (~30 stub functions across 9 files, each `raise NotImplementedError`).
> Real line coverage is 52.91%, not the >95% previously claimed here —
> and much of even that reflects stub functions whose entire body is the
> raise statement, not tested feature logic. A phased implementation
> plan exists; see the repo's CLAUDE.md for the real scope and status.

## 🌟 Overview

**Tastefully Stained** is a C2PA-compliant content watermarking solution that combines advanced **hybrid DCT/DWT algorithms** with **blockchain anchoring** for autonomous revenue generation. It provides invisible, robust watermarking for digital images while maintaining full content authenticity and provenance tracking.

### Why Tastefully Stained?

- **🔒 Invisible Watermarking**: Advanced hybrid DCT/DWT algorithm embeds undetectable watermarks
- **⛓️ Blockchain Anchoring**: Immutable provenance records on Ethereum with IPFS storage
- **📜 C2PA Compliant**: Full adherence to Coalition for Content Provenance and Authenticity v2.0
- **🚧 In Development**: core watermarking/C2PA/blockchain logic is stubbed, not yet implemented (see status note above)
- **💰 Revenue Generation**: Built-in monetization through licensing verification

---

## ✨ Features

### Core Watermarking Engine
- **Hybrid DCT/DWT Algorithm**: Combines Discrete Cosine Transform and Discrete Wavelet Transform for optimal robustness
- **Adaptive Embedding**: Automatically adjusts watermark strength based on image characteristics
- **Multi-scale Protection**: Survives compression, scaling, and various image transformations
- **Batch Processing**: Process thousands of images with parallel execution

### Blockchain Integration
- **Ethereum Smart Contracts**: Secure watermark anchoring with gas-optimized contracts
- **IPFS Storage**: Distributed content-addressed storage for watermark metadata
- **Provenance Chain**: Complete history tracking from creation to current state
- **NFT Support**: Optional ERC-721 token minting for content ownership proof

### C2PA Compliance
- **Manifest Generation**: Automatic C2PA manifest creation and embedding
- **Assertion Support**: Full support for all C2PA assertion types
- **Signature Verification**: Cryptographic verification of content authenticity
- **Ingredient Tracking**: Complete lineage tracking for derivative works

### API & Integration
- **RESTful API**: Full-featured FastAPI backend with OpenAPI documentation
- **React Dashboard**: Modern web interface for watermark management
- **SDK Support**: Python and JavaScript SDKs for integration
- **Webhook Events**: Real-time notifications for watermarking events

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/iamthegreatdestroyer/Tastefully-Stained.git
cd Tastefully-Stained

# Start with Docker (recommended)
docker-compose up -d

# Or manual installation:
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
uvicorn main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key variables:

```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tastefully_stained

# Blockchain
ETHEREUM_RPC_URL=https://sepolia.infura.io/v3/YOUR_PROJECT_ID
ETHEREUM_PRIVATE_KEY=your-private-key

# IPFS
IPFS_API_URL=http://localhost:5001
```

### First Watermark

```python
from tastefully_stained import WatermarkEngine

# Initialize engine
engine = WatermarkEngine()

# Embed watermark
result = engine.embed(
    image_path="input.jpg",
    metadata={
        "creator": "Your Name",
        "license": "CC-BY-4.0"
    }
)

# Save watermarked image
result.save("output.jpg")

# Anchor to blockchain
anchor = engine.anchor_to_blockchain(result.watermark_id)
print(f"Transaction: {anchor.tx_hash}")
```

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Complete REST API documentation |
| [Architecture](docs/ARCHITECTURE.md) | System design and components |
| [Deployment](docs/DEPLOYMENT.md) | Production deployment guide |
| [C2PA Specification](docs/C2PA_SPECIFICATION.md) | C2PA implementation details |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/watermark/embed` | POST | Embed watermark in image |
| `/api/v1/watermark/extract` | POST | Extract watermark from image |
| `/api/v1/watermark/verify` | POST | Verify watermark authenticity |
| `/api/v1/blockchain/anchor` | POST | Anchor watermark to blockchain |
| `/api/v1/c2pa/manifest` | GET | Retrieve C2PA manifest |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │
│  │   React Web UI  │  │   Python SDK    │  │  REST API      │  │
│  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘  │
└───────────┼────────────────────┼───────────────────┼────────────┘
            │                    │                   │
            ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API GATEWAY (FastAPI)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Auth/JWT   │  │  Rate Limit  │  │   Request Validation │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│   Watermark    │  │   Blockchain   │  │     C2PA       │
│    Engine      │  │    Anchor      │  │   Manifest     │
│  ┌──────────┐  │  │  ┌──────────┐  │  │  ┌──────────┐  │
│  │   DCT    │  │  │  │ Ethereum │  │  │  │ Builder  │  │
│  ├──────────┤  │  │  ├──────────┤  │  │  ├──────────┤  │
│  │   DWT    │  │  │  │   IPFS   │  │  │  │Validator │  │
│  ├──────────┤  │  │  └──────────┘  │  │  └──────────┘  │
│  │  Hybrid  │  │  └────────────────┘  └────────────────┘
│  └──────────┘  │
└────────────────┘
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=backend --cov-report=html

# Specific test suites
pytest backend/tests/test_dct.py -v
pytest backend/tests/test_blockchain.py -v

# Integration tests
pytest -m integration
```

---

## 🔧 Development

### Project Structure

```
tastefully-stained/
├── backend/                    # Python FastAPI backend
│   ├── watermark_engine/       # Core watermarking logic
│   │   ├── core/               # DCT, DWT, Hybrid algorithms
│   │   ├── api/                # REST endpoints
│   │   ├── blockchain/         # Ethereum & IPFS integration
│   │   ├── c2pa/               # C2PA manifest handling
│   │   └── utils/              # Shared utilities
│   ├── tests/                  # Test suite
│   └── main.py                 # Application entry
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API clients
│   │   └── styles/             # CSS/Tailwind
│   └── package.json
├── contracts/                  # Solidity smart contracts
├── docs/                       # Documentation
└── docker-compose.yml          # Container orchestration
```

### Code Quality

```bash
# Format code
black backend/
npm run lint --prefix frontend

# Type checking
mypy backend/
npm run typecheck --prefix frontend

# Security scan
bandit -r backend/
```

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [C2PA](https://c2pa.org/) - Content Authenticity Initiative
- [OpenZeppelin](https://openzeppelin.com/) - Smart contract security
- [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python framework
- [Vite](https://vitejs.dev/) - Next-generation frontend tooling

---

<div align="center">

**Built with ❤️ for content authenticity**

[⬆ Back to Top](#-tastefully-stained)

</div>
