"""
API Endpoint Tests
==================

Comprehensive tests for the FastAPI REST API.

Coverage targets:
- All endpoints
- Request validation
- Error handling
- Authentication

Run: pytest backend/tests/test_api.py -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root_returns_service_info(self, client: TestClient) -> None:
        """Test that root endpoint returns service information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Tastefully Stained"
        assert "version" in data


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client: TestClient) -> None:
        """Test health check returns healthy status."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "tastefully-stained"


class TestWatermarkEmbedEndpoint:
    """Test watermark embedding endpoint."""
    
    def test_embed_not_implemented(self, client: TestClient) -> None:
        """Test embed endpoint returns 501 until implemented."""
        # Create a minimal test file
        files = {"image": ("test.jpg", b"fake image data", "image/jpeg")}
        
        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "test"}
        )
        
        assert response.status_code == 501


class TestWatermarkExtractEndpoint:
    """Test watermark extraction endpoint."""
    
    def test_extract_not_implemented(self, client: TestClient) -> None:
        """Test extract endpoint returns 501 until implemented."""
        files = {"image": ("test.jpg", b"fake image data", "image/jpeg")}
        
        response = client.post("/api/v1/watermark/extract", files=files)
        
        assert response.status_code == 501


class TestWatermarkVerifyEndpoint:
    """Test watermark verification endpoint."""
    
    def test_verify_not_implemented(self, client: TestClient) -> None:
        """Test verify endpoint returns 501 until implemented."""
        files = {"image": ("test.jpg", b"fake image data", "image/jpeg")}
        
        response = client.post("/api/v1/watermark/verify", files=files)
        
        assert response.status_code == 501
