"""
Tests for POST /api/vision/extract.

The image_unclear branch uses a real synthetic bad image and a fake
extractor that raises if called — proving the quality check genuinely
short-circuits before any Vision API call, not just asserting it. The
candidates_found/error branches use dependency_overrides to inject a fake
VisionExtractor, same pattern as test_api_troubleshoot.py.
"""

import json
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.deps import get_vision_extractor_dep
from app.main import app
from vision.vision_extract import VisionExtractionError


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _dark_png_bytes() -> bytes:
    array = np.full((200, 200), 10, dtype="uint8")
    image = Image.fromarray(array, mode="L")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _usable_png_bytes() -> bytes:
    rng = np.random.default_rng(seed=1)
    array = rng.integers(low=60, high=200, size=(200, 200), dtype="uint8")
    image = Image.fromarray(array, mode="L")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class _ExplodingExtractor:
    def extract(self, image_bytes, mime_type="image/jpeg"):
        raise AssertionError("Vision API must not be called for an unusable image")


def test_dark_image_returns_image_unclear_without_calling_vision():
    app.dependency_overrides[get_vision_extractor_dep] = lambda: _ExplodingExtractor()
    client = TestClient(app)

    response = client.post(
        "/api/vision/extract",
        files={"file": ("nameplate.png", _dark_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "image_unclear"
    assert body["reason"] == "too_dark"
    assert body["candidates"] == []


def test_usable_image_returns_candidates():
    class _FakeExtractor:
        def extract(self, image_bytes, mime_type="image/jpeg"):
            from vision.contracts import VisionCandidate, VisionExtractionResult

            return VisionExtractionResult(
                status="candidates_found",
                candidates=[
                    VisionCandidate(
                        equipment_category="solar_inverter",
                        manufacturer="Growatt",
                        model="MIN 3000 TL-X",
                        code="201",
                        confidence=0.9,
                        raw_model_text="MIN 3000TL-X",
                    )
                ],
                message="1 candidate(s) detected.",
            )

    app.dependency_overrides[get_vision_extractor_dep] = lambda: _FakeExtractor()
    client = TestClient(app)

    response = client.post(
        "/api/vision/extract",
        files={"file": ("nameplate.png", _usable_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "candidates_found"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0]["manufacturer"] == "Growatt"


def test_vision_extraction_error_returns_error_status_not_500():
    class _FailingExtractor:
        def extract(self, image_bytes, mime_type="image/jpeg"):
            raise VisionExtractionError("simulated Vision API outage")

    app.dependency_overrides[get_vision_extractor_dep] = lambda: _FailingExtractor()
    client = TestClient(app)

    response = client.post(
        "/api/vision/extract",
        files={"file": ("nameplate.png", _usable_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["candidates"] == []


def test_missing_file_returns_422():
    client = TestClient(app)
    response = client.post("/api/vision/extract")
    assert response.status_code == 422