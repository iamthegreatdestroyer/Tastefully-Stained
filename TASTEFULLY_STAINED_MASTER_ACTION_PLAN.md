# TASTEFULLY STAINED: AI Content Provenance & Watermarking Service
## Master Action Plan for GitHub Copilot-Assisted Development

**Repository:** https://github.com/iamthegreatdestroyer/Tastefully-Stained.git
**Project Goal:** Build a production-ready C2PA-compliant content watermarking solution with hybrid DCT/DWT algorithms and blockchain anchoring for autonomous revenue generation.

**Timeline:** 100-150 hours of development
**Architecture:** Multi-language stack (Python, Rust, Go, TypeScript/React)
**Deployment:** Docker containerization with GitHub Actions CI/CD

---

## PHASE 1: ENVIRONMENT & INFRASTRUCTURE SETUP [REF:PHASE1-SETUP]

### 1.1 Repository Structure Creation
**Task:** Create complete project directory structure with all subdirectories
**Command for Copilot:**
```
Create the following directory structure for Tastefully Stained:
tastefully-stained/
├── backend/
│   ├── watermark_engine/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── dct_processor.py
│   │   │   ├── dwt_processor.py
│   │   │   └── hybrid_algorithm.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   ├── models.py
│   │   │   └── middleware.py
│   │   ├── blockchain/
│   │   │   ├── __init__.py
│   │   │   ├── ethereum_anchor.py
│   │   │   └── ipfs_handler.py
│   │   ├── c2pa/
│   │   │   ├── __init__.py
│   │   │   ├── manifest_builder.py
│   │   │   └── validation.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── image_loader.py
│   │       ├── logger.py
│   │       └── config.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_dct.py
│   │   ├── test_dwt.py
│   │   ├── test_hybrid.py
│   │   ├── test_api.py
│   │   ├── test_blockchain.py
│   │   └── test_c2pa.py
│   ├── requirements.txt
│   ├── setup.py
│   ├── Dockerfile
│   └── main.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── WatermarkUploader.tsx
│   │   │   ├── VerificationDashboard.tsx
│   │   │   └── BlockchainExplorer.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Upload.tsx
│   │   │   └── Verify.tsx
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── blockchain.ts
│   │   ├── styles/
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .dockerignore
├── contracts/
│   ├── WatermarkRegistry.sol
│   ├── ContentProvenanceToken.sol
│   └── Migrations.sol
├── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── test.yml
│       ├── build.yml
│       └── deploy.yml
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── C2PA_SPECIFICATION.md
├── .gitignore
├── README.md
└── PROJECT_SPEC.md
```

Create all directories and initialization files.
```

**Copilot Execution:** Generate all directories and empty `__init__.py` files with appropriate structure

### 1.2 Python Backend Dependencies
**Task:** Set up Python environment with all required packages
**File:** `backend/requirements.txt`
**Copilot Instruction:**
```
Create a comprehensive requirements.txt for the Tastefully Stained watermarking backend with:
- FastAPI==0.104.1
- Uvicorn[standard]==0.24.0
- Pillow==10.1.0
- NumPy==1.26.3
- SciPy==1.11.4
- OpenCV-python==4.8.1.78
- PyWavelets==1.5.0 (for DWT)
- Web3==6.11.1 (for blockchain)
- python-dotenv==1.0.0
- pydantic==2.5.0
- pytest==7.4.3
- pytest-asyncio==0.21.1
- requests==2.31.0
- cryptography==41.0.7
- PyJWT==2.8.1
- httpx==0.25.2
- python-multipart==0.0.6

Include all transitive dependencies with pinned versions for reproducibility.
```

**Copilot Execution:** Generate requirements.txt with exact versions and comments

### 1.3 Docker Infrastructure
**Task:** Create Docker configuration for containerized deployment
**Files to Generate:**
1. `backend/Dockerfile`
2. `frontend/Dockerfile`
3. `docker-compose.yml`

**Copilot Instruction:**
```
Create production-ready Dockerfile for Python backend with:
- Base image: python:3.11-slim
- Working directory: /app
- Copy requirements and install with pip cache optimization
- Expose port 8000
- Health check endpoint at /health
- Non-root user execution
- Multi-stage build for reduced image size
- Comprehensive error handling and logging

Then create Dockerfile for Node/React frontend with:
- Build stage: node:18-alpine with build commands
- Runtime stage: nginx:alpine with optimized configuration
- Health checks
- Volume mounts for configuration
- Port 3000 exposure

Finally, create docker-compose.yml orchestrating:
- Backend service (port 8000)
- Frontend service (port 3000)
- PostgreSQL database (if needed)
- Redis cache (for performance)
- Network configuration for inter-service communication
- Environment variable management
- Volume persistence
```

**Copilot Execution:** Generate all Docker files with production best practices

### 1.4 GitHub Actions CI/CD Pipeline
**Task:** Set up automated testing, building, and deployment workflows
**Files to Generate:**
1. `.github/workflows/test.yml`
2. `.github/workflows/build.yml`
3. `.github/workflows/deploy.yml`

**Copilot Instruction:**
```
Create GitHub Actions workflows with:

test.yml:
- Trigger on: push to main/develop, pull_requests
- Python 3.11 matrix testing
- Install dependencies from requirements.txt
- Run pytest with coverage reporting
- Lint with flake8/black
- Security scanning with bandit
- Upload coverage to codecov

build.yml:
- Trigger on: test.yml success
- Build Docker images for backend and frontend
- Tag with git hash and semantic versioning
- Push to container registry (if configured)
- Scan for vulnerabilities with trivy

deploy.yml:
- Trigger on: build.yml success AND main branch
- Deploy via docker-compose
- Run database migrations
- Health checks
- Rollback on failure
- Slack notifications
```

**Copilot Execution:** Generate all workflow files with comprehensive CI/CD logic

---

## PHASE 2: CORE WATERMARKING ENGINE [REF:PHASE2-WATERMARK]

### 2.1 DCT (Discrete Cosine Transform) Implementation
**File:** `backend/watermark_engine/core/dct_processor.py`
**Copilot Instruction:**
```
Create a production-grade DCT watermarking module with:

Class: DCTWatermarker
Methods:
- __init__(strength: float = 0.5, block_size: int = 8)
- embed_watermark(image: np.ndarray, watermark_data: bytes) -> np.ndarray
- extract_watermark(image: np.ndarray) -> bytes
- _divide_into_blocks(image: np.ndarray) -> list
- _apply_dct_to_block(block: np.ndarray) -> np.ndarray
- _embed_in_dc_component(block: np.ndarray, bit: int) -> np.ndarray
- _inverse_dct(dct_block: np.ndarray) -> np.ndarray
- _quantize_for_jpeg(image: np.ndarray) -> np.ndarray

Features:
- JPEG compression resistant watermarking
- Bit-by-bit embedding in frequency domain
- Error correction using Reed-Solomon codes
- Adaptive strength based on image content
- Full documentation and type hints
- Comprehensive error handling
- Logging for debug/production use
```

**Copilot Execution:** Generate complete DCT module with scipy.fftpack integration

### 2.2 DWT (Discrete Wavelet Transform) Implementation
**File:** `backend/watermark_engine/core/dwt_processor.py`
**Copilot Instruction:**
```
Create a production-grade DWT watermarking module with:

Class: DWTWatermarker
Methods:
- __init__(wavelet: str = 'db4', level: int = 3, strength: float = 0.3)
- embed_watermark(image: np.ndarray, watermark_data: bytes) -> np.ndarray
- extract_watermark(image: np.ndarray) -> bytes
- _apply_multilevel_dwt(image: np.ndarray) -> dict
- _embed_in_high_freq_bands(coefficients: dict, data: bytes) -> dict
- _inverse_dwt(coefficients: dict) -> np.ndarray
- _calculate_embedding_strength(original: np.ndarray) -> float

Features:
- Multi-level wavelet decomposition (Daubechies-4)
- Embedding in high-frequency bands for invisibility
- Robustness against scaling and rotation
- Perceptual quality metrics (SSIM, PSNR)
- Supports color and grayscale images
- Full logging and error recovery
- Type hints throughout
```

**Copilot Execution:** Generate complete DWT module using PyWavelets library

### 2.3 Hybrid Algorithm Selection & Optimization
**File:** `backend/watermark_engine/core/hybrid_algorithm.py`
**Copilot Instruction:**
```
Create hybrid watermarking orchestrator with:

Class: HybridWatermarkOrchestrator
Methods:
- __init__(dct_watermarker: DCTWatermarker, dwt_watermarker: DWTWatermarker)
- embed_robust_watermark(image: np.ndarray, watermark_data: bytes, strategy: str = 'auto') -> np.ndarray
- extract_watermark(image: np.ndarray) -> tuple[bytes, float, str]
- _analyze_image_characteristics(image: np.ndarray) -> dict
- _select_optimal_strategy(characteristics: dict) -> str
- _embed_dct_primary(image: np.ndarray, data: bytes) -> np.ndarray
- _embed_dwt_secondary(image: np.ndarray, data: bytes) -> np.ndarray
- _attempt_recovery_on_failure(image: np.ndarray, data: bytes) -> np.ndarray

Strategy Selection Logic:
- DCT-primary for photographic content with high frequency variation
- DWT-primary for artistic/text content with geometric features
- Hybrid dual-embedding for maximum robustness
- Confidence scoring based on extraction success

Features:
- Automatic strategy selection based on image analysis
- Redundant embedding for recovery robustness
- Confidence metrics for extraction quality
- Fallback strategies on failure
- Performance optimization (caching, vectorization)
```

**Copilot Execution:** Generate complete hybrid orchestrator with intelligent selection logic

---

## PHASE 3: C2PA INTEGRATION & MANIFEST MANAGEMENT [REF:PHASE3-C2PA]

### 3.1 C2PA Manifest Builder
**File:** `backend/watermark_engine/c2pa/manifest_builder.py`
**Copilot Instruction:**
```
Create C2PA manifest building system with:

Class: C2PAManifestBuilder
Methods:
- __init__(creator_identity: str, organization: str)
- create_manifest(image_path: str, watermark_metadata: dict) -> dict
- add_watermark_claim(manifest: dict, algorithm: str, strength: float, embedding_time: str) -> dict
- add_blockchain_anchor_claim(manifest: dict, tx_hash: str, block_number: int) -> dict
- add_provenance_chain(manifest: dict, source_history: list) -> dict
- sign_manifest(manifest: dict, private_key: str) -> dict
- validate_manifest(manifest: dict) -> tuple[bool, list[str]]
- export_manifest_json(manifest: dict, output_path: str) -> str

C2PA Specification Compliance:
- Version 2.0 spec implementation
- Required fields: dcterms:created, dcterms:creator, dcterms:title
- Claim structure with assertion containers
- Signature verification
- Hash computation for integrity
- Support for multiple claim types

Features:
- Automatic timestamp generation (ISO 8601)
- Digital signature integration
- Blockchain reference embedding
- Comprehensive validation
- JSON serialization with proper formatting
```

**Copilot Execution:** Generate C2PA manifest builder following specification

### 3.2 Blockchain Anchoring System
**File:** `backend/watermark_engine/blockchain/ethereum_anchor.py`
**Copilot Instruction:**
```
Create Ethereum blockchain anchoring system with:

Class: EthereumAnchor
Methods:
- __init__(contract_address: str, private_key: str, web3_provider: str)
- anchor_watermark(watermark_hash: str, metadata: dict) -> dict
- retrieve_anchor(tx_hash: str) -> dict
- _compute_watermark_hash(watermark_data: bytes) -> str
- _build_anchor_transaction(hash: str, metadata: dict) -> dict
- _execute_transaction(tx: dict) -> str
- _verify_transaction_confirmation(tx_hash: str, confirmations: int = 12) -> bool
- get_anchor_proof(tx_hash: str) -> dict

Smart Contract Interaction:
- WatermarkRegistry contract calls
- Gas estimation and optimization
- Transaction receipt monitoring
- Error handling for failed transactions
- Automatic retry with exponential backoff

Features:
- Keccak-256 hash computation
- Metadata JSON encoding
- Transaction cost optimization
- Confirmation waiting (12 blocks = ~3 minutes)
- Proof generation for verification
- Event logging for audit trails
```

**Copilot Execution:** Generate Ethereum anchoring with Web3.py integration

### 3.3 IPFS Integration for Distributed Storage
**File:** `backend/watermark_engine/blockchain/ipfs_handler.py`
**Copilot Instruction:**
```
Create IPFS integration for decentralized proof storage with:

Class: IPFSHandler
Methods:
- __init__(ipfs_api_url: str = "http://localhost:5001")
- store_watermark_proof(proof_data: dict) -> str
- retrieve_watermark_proof(ipfs_hash: str) -> dict
- store_manifest(manifest: dict) -> str
- retrieve_manifest(ipfs_hash: str) -> dict
- _pin_to_ipfs(data: bytes) -> str
- _retrieve_from_ipfs(ipfs_hash: str) -> bytes
- _verify_ipfs_connectivity() -> bool
- get_ipfs_gateway_url(ipfs_hash: str) -> str

Features:
- Pin management for persistence
- JSON serialization/deserialization
- Error handling and connectivity checks
- Gateway URL generation for public access
- Timeout handling
- Retry logic for failed requests
- Support for both local and public IPFS nodes
```

**Copilot Execution:** Generate IPFS handler with ipfshttpclient library

---

## PHASE 4: REST API & BUSINESS LOGIC [REF:PHASE4-API]

### 4.1 FastAPI Application Structure
**File:** `backend/watermark_engine/api/routes.py`
**Copilot Instruction:**
```
Create FastAPI REST API with the following endpoints:

Endpoint Structure:

POST /api/v1/watermark/embed
- Body: {image_file, watermark_data, algorithm, strength}
- Response: {watermarked_image_url, watermark_id, c2pa_manifest}
- Rate limit: 100/hour
- Authentication: API key required

POST /api/v1/watermark/embed-batch
- Body: {files: [file list], watermark_data, settings}
- Response: {job_id, estimated_completion}
- Asynchronous processing with job tracking
- Rate limit: 10/hour

GET /api/v1/watermark/verify/{image_id}
- Response: {is_watermarked, algorithm, confidence, metadata}
- Rate limit: 500/hour (public)

POST /api/v1/watermark/extract
- Body: {image_file}
- Response: {extracted_data, confidence, provenance_chain}

GET /api/v1/blockchain/anchor/{tx_hash}
- Response: {block_number, timestamp, metadata}
- Public endpoint

GET /api/v1/c2pa/manifest/{watermark_id}
- Response: {manifest_json, signature, validation_status}

POST /api/v1/pricing/estimate
- Body: {image_count, resolution, algorithm, batch_size}
- Response: {cost_usd, processing_time_seconds}

GET /api/v1/health
- Response: {status, backend_ok, blockchain_ok, storage_ok}

Features:
- Comprehensive error handling with standardized error codes
- Request validation with Pydantic models
- Async/await for non-blocking operations
- Detailed logging
- CORS configuration
- Rate limiting middleware
- Authentication/authorization layer
```

**Copilot Execution:** Generate FastAPI application with all endpoints

### 4.2 Data Models & Validation
**File:** `backend/watermark_engine/api/models.py`
**Copilot Instruction:**
```
Create Pydantic models for request/response validation:

Models:
- WatermarkRequest (image_file, watermark_data, algorithm, strength)
- WatermarkResponse (watermarked_image_url, watermark_id, c2pa_manifest)
- VerificationRequest (image_file)
- VerificationResponse (is_watermarked, algorithm, confidence, metadata)
- ExtractionRequest (image_file)
- ExtractionResponse (extracted_data, confidence, provenance_chain)
- BlockchainAnchorRequest (watermark_hash, metadata)
- BlockchainAnchorResponse (tx_hash, block_number, confirmation_status)
- PricingEstimateRequest (image_count, resolution, algorithm, batch_size)
- PricingEstimateResponse (cost_usd, processing_time_seconds)
- ErrorResponse (error_code, message, details, timestamp)
- HealthCheckResponse (status, components: dict)

Features:
- Field validation with constraints
- Documentation strings
- Example values
- Type hints throughout
- Custom validators where needed
- Serialization/deserialization support
```

**Copilot Execution:** Generate all Pydantic models with validation

### 4.3 Authentication & Authorization
**File:** `backend/watermark_engine/api/middleware.py`
**Copilot Instruction:**
```
Create authentication and authorization middleware:

Components:
- APIKeyAuth (header-based API key validation)
- JWTAuth (JWT token validation for premium tier)
- RateLimitMiddleware (token bucket algorithm)
- RequestLoggingMiddleware (structured logging)
- CORSMiddleware (cross-origin configuration)
- RequestValidationMiddleware (input sanitization)

Features:
- API key tier system (free, premium, enterprise)
- JWT with RSA-256 signatures
- Rate limiting per API key
- Quota tracking (daily/monthly)
- Request/response logging
- Error response standardization
- Timing/performance metrics
```

**Copilot Execution:** Generate middleware with production security practices

---

## PHASE 5: TESTING & QUALITY ASSURANCE [REF:PHASE5-TESTING]

### 5.1 Unit Tests for Core Components
**Files to Generate:**
1. `backend/tests/test_dct.py`
2. `backend/tests/test_dwt.py`
3. `backend/tests/test_hybrid.py`

**Copilot Instruction:**
```
Create comprehensive unit tests for watermarking components:

test_dct.py:
- Test watermark embedding with various image sizes
- Test watermark extraction accuracy
- Test robustness against JPEG compression (70%, 85%, 95% quality)
- Test with different image types (photo, art, text)
- Test bit-error rate with various bit depths
- Test edge cases (very small/large images, extreme values)
- Parametrized tests for different strengths (0.1 to 1.0)
- Performance benchmarking

test_dwt.py:
- Test multi-level decomposition
- Test watermark invisibility (SSIM > 0.95)
- Test robustness against scaling (50%, 200%)
- Test robustness against rotation (±15 degrees)
- Test edge cases with different wavelets
- Compare quality metrics across strategies
- Performance profiling

test_hybrid.py:
- Test strategy selection logic
- Test dual-embedding robustness
- Test recovery mechanisms
- Test confidence scoring accuracy
- Test hybrid performance vs individual methods

All tests:
- Fixture-based test data (sample images)
- Mock external dependencies (blockchain, IPFS)
- Coverage target: >95%
- Performance benchmarks
```

**Copilot Execution:** Generate all test files with pytest framework

### 5.2 API Integration Tests
**File:** `backend/tests/test_api.py`
**Copilot Instruction:**
```
Create FastAPI integration tests with:

Test Scenarios:
- Test all endpoints with valid/invalid inputs
- Test authentication (valid/invalid API keys)
- Test rate limiting behavior
- Test error handling with proper status codes
- Test batch processing workflows
- Test concurrent requests
- Test database/blockchain call interactions (mocked)
- Test file upload handling
- Test response schema validation

Features:
- TestClient from fastapi.testclient
- Async test support with pytest-asyncio
- Fixture-based test data
- Mock external services
- Performance assertions
- Coverage reporting
```

**Copilot Execution:** Generate API integration tests

### 5.3 Security & Vulnerability Testing
**File:** `backend/tests/test_security.py`
**Copilot Instruction:**
```
Create security-focused tests:

Test Categories:
- Input validation and sanitization
- API key/JWT token validation
- SQL injection prevention (if using DB)
- File upload security (size, type, content)
- Rate limiting enforcement
- CORS policy validation
- Error message information disclosure
- Dependency vulnerability scanning (bandit)

Features:
- Negative test cases
- Boundary testing
- Fuzzing with randomized inputs
```

**Copilot Execution:** Generate security test suite

---

## PHASE 6: FRONTEND DEVELOPMENT [REF:PHASE6-FRONTEND]

### 6.1 React Component Architecture
**Files to Generate:**
1. `frontend/src/components/WatermarkUploader.tsx`
2. `frontend/src/components/VerificationDashboard.tsx`
3. `frontend/src/components/BlockchainExplorer.tsx`

**Copilot Instruction:**
```
Create React components with TypeScript:

WatermarkUploader Component:
- Drag-and-drop file upload interface
- Algorithm selection (DCT, DWT, Hybrid)
- Strength slider (0.1-1.0)
- Preview of original image
- Progress bar during processing
- Result display with watermarked image preview
- C2PA manifest viewer
- Error handling with user-friendly messages
- Cost estimation display before processing

VerificationDashboard Component:
- Image upload/paste from clipboard
- Watermark detection status
- Extracted watermark data display
- Algorithm confidence metrics
- Blockchain verification link
- Provenance chain visualization
- Export options (JSON, PDF)

BlockchainExplorer Component:
- Transaction hash input
- Blockchain confirmation status
- Block number and timestamp
- Metadata display
- IPFS link to proof
- Transaction cost information
- Verification badge

Features for all components:
- Loading states with spinners
- Error boundary implementation
- Toast notifications for user feedback
- Responsive design (mobile/tablet/desktop)
- Accessibility features (ARIA labels, keyboard navigation)
- LocalStorage for user preferences
- TypeScript strict mode
```

**Copilot Execution:** Generate all React components with Tailwind CSS styling

### 6.2 Page Components
**Files to Generate:**
1. `frontend/src/pages/Home.tsx`
2. `frontend/src/pages/Upload.tsx`
3. `frontend/src/pages/Verify.tsx`

**Copilot Instruction:**
```
Create page-level components:

Home.tsx:
- Welcome section with feature overview
- Quick stats (total watermarks, blockchain anchors)
- Getting started guide
- Feature showcase with animations
- API documentation link
- Sign-up/login prompts

Upload.tsx:
- Full-page watermark embedding interface
- Use WatermarkUploader component
- Pricing calculator
- FAQ section
- API usage examples

Verify.tsx:
- Full-page verification interface
- Use VerificationDashboard component
- Batch verification option
- Historical verification results

Features:
- Routing integration with React Router
- Component composition
- State management (React Context or Redux)
```

**Copilot Execution:** Generate all page components

### 6.3 API Service Layer
**File:** `frontend/src/services/api.ts`
**Copilot Instruction:**
```
Create TypeScript API service layer with:

Class: WatermarkAPIClient
Methods:
- embedWatermark(image: File, config: WatermarkConfig): Promise<WatermarkResult>
- verifyWatermark(image: File): Promise<VerificationResult>
- extractWatermark(image: File): Promise<ExtractionResult>
- estimatePrice(params: PricingParams): Promise<PriceEstimate>
- getWatermarkStatus(watermarkId: string): Promise<WatermarkStatus>
- getBlockchainAnchor(txHash: string): Promise<BlockchainAnchor>
- getC2PAManifest(watermarkId: string): Promise<C2PAManifest>
- healthCheck(): Promise<HealthStatus>

Features:
- Axios HTTP client with interceptors
- Error handling with typed errors
- Request/response transformation
- Retry logic with exponential backoff
- Timeout handling
- API key management
- Request logging
- Type-safe responses
```

**Copilot Execution:** Generate API service with axios integration

---

## PHASE 7: SMART CONTRACTS & BLOCKCHAIN [REF:PHASE7-BLOCKCHAIN]

### 7.1 Watermark Registry Smart Contract
**File:** `contracts/WatermarkRegistry.sol`
**Copilot Instruction:**
```
Create Solidity smart contract for watermark registry:

Contract: WatermarkRegistry
Features:
- Store watermark metadata on-chain
- Owner verification
- Event logging for watermark creation/verification
- Access control (OpenZeppelin)
- Gas optimization

Main Functions:
- registerWatermark(bytes32 watermarkHash, string memory metadata) -> uint256
- getWatermarkInfo(uint256 registryId) -> (address, uint256, string)
- verifyWatermark(bytes32 hash) -> bool
- getWatermarkCount() -> uint256
- transferWatermarkOwnership(uint256 registryId, address newOwner)

Events:
- WatermarkRegistered(indexed bytes32 hash, indexed address owner, uint256 timestamp)
- WatermarkVerified(indexed bytes32 hash, uint256 timestamp)
- OwnershipTransferred(indexed uint256 registryId, indexed address newOwner)

Features:
- Transparent upgrade pattern
- Batch operations
- Pausable mechanism for emergencies
```

**Copilot Execution:** Generate Solidity contract following best practices

### 7.2 Content Provenance Token (ERC-721)
**File:** `contracts/ContentProvenanceToken.sol`
**Copilot Instruction:**
```
Create ERC-721 NFT contract for content provenance:

Contract: ContentProvenanceToken (ERC721Enumerable)
Features:
- Mint NFTs for watermarked content
- Store metadata URI pointing to IPFS
- Owner-based access control
- Royalty support

Main Functions:
- mintProvenanceNFT(address creator, string memory ipfsURI) -> uint256
- getContentProvenance(uint256 tokenId) -> (address, string, uint256)
- setRoyalty(uint256 tokenId, uint256 percentage)
- transferWithProof(address to, uint256 tokenId, bytes proof)

Features:
- Metadata storage on IPFS
- Creator rewards mechanism
- Batch minting capability
```

**Copilot Execution:** Generate ERC-721 contract with Openzeppelin standards

---

## PHASE 8: DEPLOYMENT & MONITORING [REF:PHASE8-DEPLOYMENT]

### 8.1 Production Deployment Configuration
**File:** `deployment/docker-compose.prod.yml`
**Copilot Instruction:**
```
Create production docker-compose configuration with:

Services:
- Backend service with resource limits
- Frontend service with caching
- PostgreSQL database with persistent volumes
- Redis cache for session/rate-limiting
- Prometheus for metrics
- Grafana for dashboards
- Elasticsearch for logging (optional)
- Nginx reverse proxy

Configuration:
- Health checks for all services
- Resource limits (CPU, memory)
- Log rotation
- Backup strategies
- Network isolation
- SSL/TLS configuration
- Environment variable management
- Secrets management (not in compose)

Features:
- Production-grade security
- High availability setup (if scaling)
- Monitoring integration
```

**Copilot Execution:** Generate production docker-compose with best practices

### 8.2 Monitoring & Alerting
**File:** `deployment/monitoring-setup.md`
**Copilot Instruction:**
```
Create comprehensive monitoring setup with:

Metrics to Track:
- API response times (p50, p95, p99)
- Watermark embedding success rate
- Blockchain transaction confirmation times
- Error rates by endpoint
- Resource utilization (CPU, memory, disk)
- Active user connections
- Queue depth for batch processing

Alerting Rules:
- Alert on >5% error rate
- Alert on response time p95 > 2 seconds
- Alert on blockchain transaction failures
- Alert on low disk space
- Alert on service restarts

Dashboards:
- System health overview
- API performance metrics
- Blockchain transaction status
- User activity trends
- Revenue/cost analysis

Tools:
- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for notifications
```

**Copilot Execution:** Generate monitoring configuration with Prometheus/Grafana

### 8.3 Log Aggregation & Analysis
**File:** `deployment/logging-setup.md`
**Copilot Instruction:**
```
Create centralized logging system:

Components:
- Structured JSON logging from backend
- Request ID tracking across services
- Log levels (DEBUG, INFO, WARN, ERROR)
- Separate logs for business logic vs infrastructure
- Search and filtering capabilities

Tools Options:
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Or: Loki + Grafana
- Or: CloudWatch (if AWS)

Features:
- Centralized log aggregation
- Full-text search
- Time-series analysis
- Alert on error patterns
- Retention policies (90 days)
```

**Copilot Execution:** Generate logging infrastructure setup

---

## PHASE 9: REVENUE OPTIMIZATION & BUSINESS LOGIC [REF:PHASE9-REVENUE]

### 9.1 Pricing Engine Implementation
**File:** `backend/watermark_engine/business/pricing_engine.py`
**Copilot Instruction:**
```
Create dynamic pricing engine with:

Class: PricingEngine
Methods:
- calculate_watermark_cost(image_resolution: tuple, algorithm: str, batch_size: int) -> float
- calculate_blockchain_cost(network: str = 'ethereum') -> float
- calculate_total_cost(watermark_cost: float, blockchain_cost: float, user_tier: str) -> float
- get_pricing_tiers() -> dict
- apply_volume_discount(quantity: int, tier: str) -> float
- estimate_blockchain_gas(algorithm: str) -> float

Pricing Strategy:
- Base price: $0.05 per watermark
- Blockchain anchor: $0.10 per transaction (covers gas)
- DWT algorithm: +20% premium
- Hybrid algorithm: +35% premium
- Volume discounts: 10% @ 50, 25% @ 500, 40% @ 5000+
- API tier multipliers: Free (public limit), Premium (2x), Enterprise (custom)

Features:
- Gas price estimation (ETH)
- Volume-based pricing
- Tier-based pricing
- Historical cost tracking
- Profitability analysis
```

**Copilot Execution:** Generate pricing engine with cost modeling

### 9.2 Payment Processing Integration
**File:** `backend/watermark_engine/business/payment_processor.py`
**Copilot Instruction:**
```
Create payment processing system with:

Class: StripePaymentProcessor
Methods:
- create_payment_intent(amount_cents: int, metadata: dict) -> dict
- verify_payment(payment_intent_id: str) -> bool
- process_subscription(user_id: str, plan_tier: str) -> dict
- issue_refund(payment_intent_id: str, reason: str) -> dict
- get_payment_status(payment_intent_id: str) -> dict

Features:
- Stripe API integration
- Webhook handling for payment confirmations
- Subscription management
- Invoice generation
- Refund processing
- Payment retry logic
- PCI compliance (no card handling)
```

**Copilot Execution:** Generate Stripe payment integration

### 9.3 Usage Tracking & Billing
**File:** `backend/watermark_engine/business/usage_tracker.py`
**Copilot Instruction:**
```
Create usage tracking and billing system:

Class: UsageTracker
Methods:
- record_watermark_usage(user_id: str, algorithm: str, image_size: int)
- record_blockchain_usage(user_id: str, tx_cost: float)
- get_monthly_usage(user_id: str) -> dict
- calculate_monthly_bill(user_id: str) -> float
- generate_invoice(user_id: str, month: str) -> Invoice
- check_quota_exceeded(user_id: str) -> bool

Features:
- Per-user usage tracking
- Monthly billing cycles
- Usage alerts (80%, 100% of quota)
- Invoice generation (PDF)
- Usage history/analytics
- Quota enforcement
```

**Copilot Execution:** Generate usage tracking system

---

## PHASE 10: DOCUMENTATION & DEPLOYMENT GUIDE [REF:PHASE10-DOCS]

### 10.1 Technical Documentation
**File:** `docs/TECHNICAL_ARCHITECTURE.md`
**Copilot Instruction:**
```
Generate comprehensive technical documentation covering:

Sections:
1. System Architecture Overview
   - High-level diagram
   - Component interactions
   - Data flow

2. API Documentation
   - All endpoints with examples
   - Request/response schemas
   - Error codes
   - Rate limiting

3. Database Schema
   - Tables and relationships
   - Indexing strategy
   - Backup procedures

4. Watermarking Algorithms
   - DCT deep dive
   - DWT deep dive
   - Hybrid strategy
   - Performance benchmarks

5. Blockchain Integration
   - Smart contract addresses
   - Transaction flow
   - Gas optimization
   - Mainnet/testnet details

6. Security Considerations
   - API key management
   - JWT tokens
   - File upload security
   - Dependency scanning

7. Performance Tuning
   - Database optimization
   - Caching strategies
   - Image processing optimization
   - API response time targets

8. Troubleshooting Guide
   - Common issues and solutions
   - Log analysis
   - Health checks
```

**Copilot Execution:** Generate comprehensive documentation

### 10.2 Deployment Guide
**File:** `docs/DEPLOYMENT.md`
**Copilot Instruction:**
```
Create step-by-step deployment guide:

Pre-Deployment Checklist:
- [ ] All tests passing
- [ ] Code review completed
- [ ] Security audit passed
- [ ] Environment variables configured
- [ ] Database backups ready
- [ ] Kubernetes manifests prepared (if using K8s)

Deployment Steps:
1. Pre-deployment validations
2. Database migrations
3. Smart contract deployment (if updates)
4. Backend service deployment
5. Frontend deployment
6. Health check verification
7. Smoke testing
8. Monitoring verification
9. Rollback plan if needed

Rollback Procedures:
- Version control for all components
- Database rollback scripts
- API contract versioning
- Traffic shifting strategy

Post-Deployment:
- Monitor error rates
- Check response times
- Verify blockchain transactions
- User feedback channels
```

**Copilot Execution:** Generate deployment documentation

### 10.3 API Usage Examples
**File:** `docs/API_EXAMPLES.md`
**Copilot Instruction:**
```
Create comprehensive API usage examples in:

Languages:
- Python (requests library)
- JavaScript (fetch API)
- cURL
- Postman collection export

Examples for Each Endpoint:
- Watermark embedding with image upload
- Verification workflow
- Blockchain anchor retrieval
- C2PA manifest access
- Batch processing
- Error handling
- Webhook handling

Include:
- Complete code samples
- Expected responses
- Common error scenarios
- Performance tips
```

**Copilot Execution:** Generate detailed API examples

---

## IMPLEMENTATION WORKFLOW

### Starting Development in VS Code with GitHub Copilot

**1. Initial Setup (Copilot Instructions)**

```
Create Tastefully Stained repository structure. Follow these exact instructions in order:

Step 1: Create directory structure
Step 2: Generate requirements.txt
Step 3: Create Docker configuration
Step 4: Set up GitHub Actions workflows
Step 5: Generate configuration files (.env.example, config.yaml)

After each step, verify the generated files match the specifications. Ask me to review before moving to the next step.
```

**2. Core Engine Development**

```
Implement the watermarking engine following this sequence:

Step 1: DCT Watermarker (backend/watermark_engine/core/dct_processor.py)
- Generate complete implementation with full type hints
- Include comprehensive docstrings
- Add error handling and logging
- Coverage target: >95%

Step 2: DWT Watermarker (same structure)

Step 3: Hybrid Orchestrator (same structure)

After each module:
- Ask me to review the code
- Generate corresponding unit tests
- Run tests to verify functionality
- Add docstring examples
```

**3. API Development**

```
Build REST API following this approach:

Step 1: Create data models (models.py)
- Validate with example data before moving on

Step 2: Implement routes (routes.py)
- Start with /health endpoint
- Add /watermark/embed endpoint
- Add /watermark/verify endpoint
- Add /watermark/extract endpoint
- Add blockchain/C2PA endpoints last

Step 3: Add middleware and auth

Step 4: Integration test

Ask for approval at each milestone.
```

**4. Frontend Development**

```
Build React components progressively:

Step 1: Create component folder structure
Step 2: WatermarkUploader component
Step 3: VerificationDashboard component
Step 4: API service layer
Step 5: Page components
Step 6: Styling and responsiveness

Test each component before moving to the next.
```

**5. Testing & Quality**

```
Run comprehensive tests:

Step 1: Unit tests for all core modules (target >95% coverage)
Step 2: API integration tests
Step 3: Security testing
Step 4: Performance benchmarking
Step 5: Load testing

Generate coverage reports after each step.
```

**6. Deployment Preparation**

```
Prepare for production:

Step 1: Review and optimize Docker builds
Step 2: Verify CI/CD pipelines work end-to-end
Step 3: Database schema and migrations
Step 4: Monitoring setup
Step 5: Documentation review
```

---

## SUCCESS METRICS & CHECKPOINTS

### Development Checkpoints

| Checkpoint | Deliverable | Review Criteria |
|-----------|------------|-----------------|
| **Phase 1** | Repository + Infrastructure | All directories created, Docker builds successfully, CI/CD pipelines trigger |
| **Phase 2** | Watermarking Engine | All algorithms implemented, >95% test coverage, performance benchmarks met |
| **Phase 3** | C2PA + Blockchain | Manifests validate against spec, blockchain anchors recorded, IPFS retrieval works |
| **Phase 4** | REST API | All endpoints functional, proper error handling, rate limiting works, API keys authenticate |
| **Phase 5** | Testing Suite | >95% code coverage, all tests passing, security tests included, performance assertions pass |
| **Phase 6** | Frontend | All components render, API integration works, responsive design verified, accessibility checked |
| **Phase 7** | Smart Contracts | Contracts deploy to testnet, functions callable, events logged correctly |
| **Phase 8** | Deployment | Docker images build, compose stack starts, health checks pass, monitoring active |
| **Phase 9** | Revenue System | Pricing calculated correctly, payments process, usage tracked, invoices generate |
| **Phase 10** | Documentation | All components documented, deployment guide complete, examples working |

### Production Readiness Criteria

- [ ] All tests passing with >95% coverage
- [ ] Security audit completed (OWASP Top 10 covered)
- [ ] Performance benchmarks met (API response time p99 < 2s)
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan documented
- [ ] Deployment automation verified
- [ ] Documentation complete and reviewed
- [ ] Load testing passed (1000+ concurrent users)
- [ ] Blockchain transactions verified on testnet
- [ ] Payment processing tested end-to-end

---

## QUICK REFERENCE FOR COPILOT COMMANDS

### Start New Implementation Phase
```
I'm beginning Phase [N]: [PHASE_NAME]

Follow the exact specifications from the Master Action Plan for Tastefully Stained. 
Generate [FILE_NAME] with [KEY_REQUIREMENTS].

After generation, I'll review and provide feedback before the next step.
```

### Request Code Review
```
Please review the implementation of [COMPONENT] against these criteria:
1. All required methods implemented
2. Type hints throughout
3. Comprehensive docstrings
4. Error handling for edge cases
5. Logging for debugging
6. Performance optimizations

Highlight any gaps or improvements needed.
```

### Generate Tests
```
Generate comprehensive unit tests for [COMPONENT] with:
- Coverage target: >95%
- Test fixtures for sample data
- Parametrized tests for different scenarios
- Edge case testing
- Performance benchmarks

Use pytest framework and include type hints.
```

### Request Optimization
```
Optimize [COMPONENT] for production with:
- Performance profiling
- Memory efficiency
- Caching strategies
- Batch processing where applicable
- Concurrent execution support

Provide before/after performance metrics.
```

---

## Notes for GitHub Copilot

**Conversation Management:**
- Maintain context of the current phase and components
- Reference previous implementations to ensure consistency
- Ask for clarification if specifications are ambiguous
- Provide progress updates at each major checkpoint

**Code Quality Standards:**
- All code must have comprehensive type hints (Python, TypeScript)
- Docstrings on all public methods and classes
- Comments for complex algorithms
- Error handling for all external calls
- Logging at debug/info/warning/error levels
- >95% test coverage target

**Production Standards:**
- Security-first approach to all API endpoints
- Input validation and sanitization
- Rate limiting and authentication
- Comprehensive error messages
- Structured logging
- Performance optimization from the start

**Documentation:**
- Generate docstrings as code is written
- Include usage examples in docstrings
- Create README for each component
- Update master documentation incrementally

---

## Start Implementation

**You are now ready to begin development. To start:**

1. Copy this entire Master Action Plan into your GitHub Copilot conversation in VS Code
2. Confirm you've read and understood all requirements
3. Wait for approval to begin Phase 1
4. Start with: "Begin Phase 1: Environment & Infrastructure Setup"
5. Follow checkpoint reviews before advancing to next phase

**Expected Outcome:** A fully functional, production-ready Tastefully Stained system implemented iteratively with maximum code quality, comprehensive testing, and continuous review.
