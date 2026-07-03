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

import base64
import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

# NOTE: importing this as `backend.main` (not bare `main`) is deliberate and
# load-bearing. The repo root also contains an unrelated top-level
# `main.py` (the stained-glass CLI entry point) with no `app` attribute.
# `pyproject.toml` sets `testpaths = ["backend/tests"]` and pytest's default
# "prepend" import mode walks up through `backend/__init__.py` to the first
# __init__.py-less directory -- the repo root -- and prepends *that* to
# sys.path (confirmed: it appears twice, once for CWD and once for rootdir,
# ahead of anything else). A bare `from main import app` therefore resolves
# to the repo-root decoy, not backend/main.py, regardless of whether pytest
# is invoked from the repo root or from backend/. Qualifying the import as
# `backend.main` makes it resolve to the real module unambiguously from
# either invocation directory.
from backend.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the API."""
    return TestClient(app)


def _make_test_png(width: int = 512, height: int = 512, seed: int = 42) -> bytes:
    """
    Build a real PNG file's bytes: smooth gradient + mild noise, matching
    the "natural" fixture style used by test_hybrid.py/test_dct.py. Large
    enough (512x512) to comfortably clear DCT/DWT capacity requirements for
    a short watermark payload, and a real Pillow-encoded PNG (not raw
    pixels) since these tests exercise the full UploadFile -> ImageLoader
    decode path over real HTTP, not just in-process numpy arrays.
    """
    rng = np.random.default_rng(seed)
    y_idx, x_idx = np.mgrid[0:height, 0:width]
    gradient = (128 + 60 * np.sin(x_idx / 40) + 40 * np.cos(y_idx / 55)).astype(np.float32)
    noise = rng.integers(-10, 10, (height, width, 3)).astype(np.float32)
    array = np.clip(gradient[..., None] + noise, 0, 255).astype(np.uint8)

    buffer = io.BytesIO()
    Image.fromarray(array, mode="RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def _decode_data_url(data_url: str) -> bytes:
    """Extract raw bytes from a `data:image/...;base64,...` URL."""
    assert data_url.startswith("data:"), f"Expected a data URL, got: {data_url[:40]!r}"
    _, _, b64_payload = data_url.partition(",")
    return base64.b64decode(b64_payload)


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

    def test_embed_success_returns_watermarked_image(self, client: TestClient) -> None:
        """A real image + real watermark text should embed successfully."""
        png_bytes = _make_test_png(seed=1)
        files = {"image": ("test.png", png_bytes, "image/png")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "Tastefully Stained QA", "strategy": "hybrid"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["watermarked_image_url"] is not None
        assert data["watermarked_image_url"].startswith("data:image/")
        assert data["watermark_id"] is not None
        assert data["processing_time_ms"] > 0
        # C2PA/blockchain are separate out-of-scope stub subsystems for this
        # phase -- the response must not fabricate values for them.
        assert data["c2pa_manifest_url"] is None
        assert data["blockchain_tx_hash"] is None

        # The returned image must actually decode and actually be watermarked
        # -- round-trip it back through extract to prove it, rather than
        # just checking the response shape.
        watermarked_bytes = _decode_data_url(data["watermarked_image_url"])
        Image.open(io.BytesIO(watermarked_bytes)).verify()  # raises if not a valid image

    def test_embed_auto_strategy_default(self, client: TestClient) -> None:
        """Default strategy (auto) should also succeed without an explicit value."""
        png_bytes = _make_test_png(seed=2)
        files = {"image": ("test.png", png_bytes, "image/png")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "auto strategy test"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_embed_rejects_empty_watermark_data(self, client: TestClient) -> None:
        """Empty/whitespace watermark_data is a validation error, not a 500."""
        png_bytes = _make_test_png(seed=3)
        files = {"image": ("test.png", png_bytes, "image/png")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "   "},
        )

        assert response.status_code == 422

    def test_embed_rejects_invalid_strategy(self, client: TestClient) -> None:
        """An unrecognized strategy string is a validation error, not a 500."""
        png_bytes = _make_test_png(seed=4)
        files = {"image": ("test.png", png_bytes, "image/png")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "test", "strategy": "quantum_flux"},
        )

        assert response.status_code == 422

    def test_embed_rejects_non_image_upload(self, client: TestClient) -> None:
        """A non-image upload must fail cleanly (400), not with a raw 500 traceback."""
        files = {"image": ("test.txt", b"this is not an image, just text bytes", "text/plain")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "test"},
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "traceback" not in detail.lower()

    def test_embed_rejects_empty_upload(self, client: TestClient) -> None:
        """A zero-byte upload must fail cleanly (400)."""
        files = {"image": ("empty.png", b"", "image/png")}

        response = client.post(
            "/api/v1/watermark/embed",
            files=files,
            data={"watermark_data": "test"},
        )

        assert response.status_code == 400


class TestWatermarkExtractEndpoint:
    """Test watermark extraction endpoint."""

    def test_extract_round_trip_recovers_original_data(self, client: TestClient) -> None:
        """Embed via HTTP, then extract via HTTP, and recover the exact payload."""
        png_bytes = _make_test_png(seed=5)
        embed_response = client.post(
            "/api/v1/watermark/embed",
            files={"image": ("test.png", png_bytes, "image/png")},
            data={"watermark_data": "round-trip-payload-123", "strategy": "hybrid"},
        )
        assert embed_response.status_code == 200
        watermarked_bytes = _decode_data_url(embed_response.json()["watermarked_image_url"])

        extract_response = client.post(
            "/api/v1/watermark/extract",
            files={"image": ("watermarked.png", watermarked_bytes, "image/png")},
        )

        assert extract_response.status_code == 200
        data = extract_response.json()
        assert data["success"] is True
        assert data["watermark_data"] == "round-trip-payload-123"
        assert data["confidence"] > 0.0
        assert data["strategy_detected"] in ("dct", "dwt", "hybrid")

    def test_extract_no_watermark_returns_404(self, client: TestClient) -> None:
        """A real, valid, but never-watermarked image must 404, not 500."""
        png_bytes = _make_test_png(seed=6)

        response = client.post(
            "/api/v1/watermark/extract",
            files={"image": ("plain.png", png_bytes, "image/png")},
        )

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "traceback" not in detail.lower()

    def test_extract_rejects_non_image_upload(self, client: TestClient) -> None:
        """A non-image upload must fail cleanly (400), not with a raw 500 traceback."""
        files = {"image": ("test.txt", b"not an image", "text/plain")}

        response = client.post("/api/v1/watermark/extract", files=files)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "traceback" not in detail.lower()


class TestWatermarkVerifyEndpoint:
    """Test watermark verification endpoint."""

    def test_verify_watermarked_image_is_valid(self, client: TestClient) -> None:
        """A genuinely watermarked image should verify as valid."""
        png_bytes = _make_test_png(seed=7)
        embed_response = client.post(
            "/api/v1/watermark/embed",
            files={"image": ("test.png", png_bytes, "image/png")},
            data={"watermark_data": "verify-me", "strategy": "hybrid"},
        )
        assert embed_response.status_code == 200
        watermarked_bytes = _decode_data_url(embed_response.json()["watermarked_image_url"])

        response = client.post(
            "/api/v1/watermark/verify",
            files={"image": ("watermarked.png", watermarked_bytes, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert data["confidence"] > 0.0

    def test_verify_unwatermarked_image_is_invalid_not_an_error(self, client: TestClient) -> None:
        """
        A real, decodable, but unwatermarked image is a *normal* verification
        outcome (is_valid=False), not an error -- unlike /extract, /verify's
        entire purpose is answering the valid/invalid question, so this
        returns 200, never 404/500.
        """
        png_bytes = _make_test_png(seed=8)

        response = client.post(
            "/api/v1/watermark/verify",
            files={"image": ("plain.png", png_bytes, "image/png")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert data["is_authentic"] is False

    def test_verify_rejects_non_image_upload(self, client: TestClient) -> None:
        """A non-image upload must fail cleanly (400), not with a raw 500 traceback."""
        files = {"image": ("test.txt", b"not an image", "text/plain")}

        response = client.post("/api/v1/watermark/verify", files=files)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "traceback" not in detail.lower()
