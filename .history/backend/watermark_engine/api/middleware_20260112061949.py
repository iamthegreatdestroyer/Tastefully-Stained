"""
API Middleware Module
=====================

FastAPI middleware for request handling, logging, and security.

This module provides middleware components for:
- Request/response logging
- CORS configuration
- Rate limiting
- Error handling
- Request validation

Copyright (c) 2024-2026 Tastefully Stained
All rights reserved.
"""

from __future__ import annotations

import logging
import time
from typing import Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.
    
    Logs request method, path, processing time, and response status.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log timing information.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
        
        Returns:
            HTTP response
        """
        request_id = str(uuid4())[:8]
        start_time = time.perf_counter()
        
        # Add request ID to state for tracing
        request.state.request_id = request_id
        
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started"
        )
        
        try:
            response = await call_next(request)
            
            process_time = (time.perf_counter() - start_time) * 1000
            
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Time: {process_time:.2f}ms"
            )
            
            # Add timing header
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            process_time = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- Error: {str(e)} - Time: {process_time:.2f}ms"
            )
            raise


def setup_middleware(app: FastAPI) -> None:
    """
    Configure all middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    
    Example:
        >>> from fastapi import FastAPI
        >>> from watermark_engine.api.middleware import setup_middleware
        >>> 
        >>> app = FastAPI()
        >>> setup_middleware(app)
    """
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure properly in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    logger.info("Middleware configured successfully")


def create_rate_limiter(
    requests_per_minute: int = 60
) -> Callable:
    """
    Create a rate limiting middleware.
    
    Args:
        requests_per_minute: Maximum requests allowed per minute
    
    Returns:
        Rate limiting middleware function
    
    Note:
        This is a placeholder. Full implementation will use Redis
        for distributed rate limiting in Phase 4.
    """
    # TODO: Implement Redis-based rate limiting in Phase 4
    async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
        # Placeholder - implement with Redis in production
        return await call_next(request)
    
    return rate_limit_middleware
