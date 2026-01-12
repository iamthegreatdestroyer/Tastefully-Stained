# =============================================================================
# TASTEFULLY STAINED - BACKEND DOCKERFILE
# =============================================================================
# Multi-stage production-optimized Docker build for FastAPI backend
# Port: 17700 (host) -> 8000 (container)
#
# Copyright (c) 2025 Tastefully Stained. All Rights Reserved.
# =============================================================================

# -----------------------------------------------------------------------------
# STAGE 1: Builder - Install dependencies and compile C extensions
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Build arguments
ARG POETRY_VERSION=1.8.2

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopencv-dev \
    pkg-config \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip wheel setuptools

# Copy requirements file
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install c2pa-python if available (may require manual install)
RUN pip install c2pa-python || echo "c2pa-python not available in PyPI, will need manual installation"

# -----------------------------------------------------------------------------
# STAGE 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# Labels for container identification
LABEL maintainer="Tastefully Stained <admin@tastefullystained.com>" \
    version="0.1.0" \
    description="Tastefully Stained C2PA Watermarking Backend API" \
    org.opencontainers.image.source="https://github.com/iamthegreatdestroyer/Tastefully-Stained"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    # App configuration
    APP_ENV=production \
    APP_MODULE=src.main:app \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    # Uvicorn configuration
    UVICORN_WORKERS=4 \
    UVICORN_LOG_LEVEL=info \
    # Path configuration
    PATH="/opt/venv/bin:$PATH" \
    # Home directory for non-root user
    HOME=/home/appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff6 \
    libwebp7 \
    libopencv-core406 \
    libopencv-imgproc406 \
    libgomp1 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /var/cache/apt/archives/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Create application directories
RUN mkdir -p /app/data /app/logs /app/temp /app/uploads /app/exports \
    && chown -R appuser:appgroup /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application source code
COPY --chown=appuser:appgroup . /app

# Create data directories with proper permissions
RUN mkdir -p \
    /app/data/watermarks \
    /app/data/certificates \
    /app/data/keys \
    /app/logs \
    /app/temp \
    && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

# Default command - production with Gunicorn + Uvicorn workers
CMD ["uvicorn", "src.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "4", \
    "--loop", "uvloop", \
    "--http", "httptools", \
    "--no-access-log", \
    "--proxy-headers", \
    "--forwarded-allow-ips", "*"]
