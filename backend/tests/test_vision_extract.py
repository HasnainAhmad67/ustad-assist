"""
Tests for vision/vision_extract.py.

Uses an injected fake `call_fn` throughout — no network access or real API
key is used or required. This verifies VisionExtractor's error handling
and response-parsing wiring, NOT the real Gemini Vision API's actual
detection accuracy, which cannot be tested from this environment.
"""

import json

import pytest

from vision.vision_extract import VisionExtractionError, VisionExtractor


def test_extract_returns_candidates_on_success():
    def fake_call_fn(api_key, model_name, image_bytes, mime_type):
        assert api_key == "test-key"
        assert mime_type == "image/jpeg"
        return json.dumps(
            {
                "candidates": [
                    {"equipment_category": "ups", "manufacturer": "Eaton", "model": "5PX1500IRT2UG2", "code": None, "confidence": 0.8}
                ]
            }
        )

    extractor = VisionExtractor(api_key="test-key", call_fn=fake_call_fn)
    result = extractor.extract(b"fake-image-bytes", mime_type="image/jpeg")

    assert result.status == "candidates_found"
    assert len(result.candidates) == 1
    assert result.candidates[0].manufacturer == "Eaton"


def test_extract_returns_no_candidates_status_when_list_is_empty():
    extractor = VisionExtractor(api_key="test-key", call_fn=lambda *a, **k: json.dumps({"candidates": []}))
    result = extractor.extract(b"fake-image-bytes")
    assert result.status == "no_candidates"
    assert result.candidates == []


def test_extract_raises_when_api_key_missing():
    extractor = VisionExtractor(api_key=None, call_fn=lambda *a, **k: json.dumps({"candidates": []}))
    extractor._api_key = None
    with pytest.raises(VisionExtractionError, match="not configured"):
        extractor.extract(b"fake-image-bytes")


def test_extract_wraps_network_errors():
    def failing_call_fn(*args, **kwargs):
        raise TimeoutError("upstream timed out")

    extractor = VisionExtractor(api_key="test-key", call_fn=failing_call_fn)
    with pytest.raises(VisionExtractionError, match="Vision API call failed"):
        extractor.extract(b"fake-image-bytes")


def test_extract_wraps_invalid_json_response():
    extractor = VisionExtractor(api_key="test-key", call_fn=lambda *a, **k: "not valid json")
    with pytest.raises(VisionExtractionError, match="failed validation"):
        extractor.extract(b"fake-image-bytes")