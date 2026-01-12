#!/usr/bin/env python3
"""
Tastefully Stained - Main Application Entry Point
==================================================

AI Content Provenance & Watermarking Service

This is the main entry point for the Tastefully Stained FastAPI backend.
Run with: `python main.py` or `uvicorn main:app --reload`

Features:
---------
- C2PA-compliant content watermarking
- Hybrid DCT/DWT algorithms for robustness
- Blockchain anchoring for provenance verification
- RESTful API for integration

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from watermark_engine.api.routes import router
from watermark_engine.api.middleware import setup_middleware
from watermark_engine.utils.logger import setup_logging
from watermark_engine.utils.config import get_config

# Initialize logging
config = get_config()
setup_logging(
    level=config.log_level,
    json_output=config.environment.value == "production"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks like:
    - Database connection pool initialization
    - Cache warming
    - Background task scheduling
    """
    # Startup
    logger.info("=" * 60)
    logger.info("Tastefully Stained - Starting up...")
    logger.info(f"Environment: {config.environment.value}")
    logger.info(f"Debug mode: {config.debug}")
    logger.info("=" * 60)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.warning(f"Configuration issue: {error}")
    
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis cache
    # TODO: Initialize blockchain connection
    
    yield  # Application is running
    
    # Shutdown
    logger.info("Tastefully Stained - Shutting down...")
    # TODO: Close database connections
    # TODO: Close cache connections
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Tastefully Stained",
    description=(
        "AI Content Provenance & Watermarking Service. "
        "C2PA-compliant watermarking with blockchain anchoring."
    ),
    version="0.1.0",
    docs_url="/docs" if config.debug else None,
    redoc_url="/redoc" if config.debug else None,
    openapi_url="/openapi.json" if config.debug else None,
    lifespan=lifespan,
)

# Setup middleware
setup_middleware(app)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with service information."""
    return {
        "service": "Tastefully Stained",
        "version": "0.1.0",
        "description": "AI Content Provenance & Watermarking Service",
        "docs": "/docs" if config.debug else "disabled",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.
    
    Logs the error and returns a safe error response.
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if config.debug else None,
        },
    )


def main() -> None:
    """Run the application using uvicorn."""
    logger.info("Starting Tastefully Stained server...")
    
    uvicorn.run(
        "main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=1 if config.api.reload else config.api.workers,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
