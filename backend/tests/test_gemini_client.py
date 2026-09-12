"""
Tests for engine/grounding/gemini_client.py.

Uses an injected fake `call_fn` throughout — no network access or real API
key is used or required. This verifies GeminiClient's error handling and
response-parsing wiring, NOT the real Gemini API's actual output quality,
which cannot be tested from this environment (see the Phase 3 handoff
notes for what to verify manually with a real key).
"""

import json

import pytest

from engine.grounding.gemini_client import GeminiClient, GeminiGenerationError


def _valid_raw_response() -> str:
    return json.dumps(
        {
            "issue_summary": "Battery mode is active.",
            "meaning_explanation": "Utility power failed and the UPS is running on battery.",
            "cause_explanations": ["A utility failure occurred."],
            "safe_check_guidance": [],
            "technician_only_guidance": [],
            "next_action": "Wait for utility power to return.",
        }
    )


def test_generate_returns_grounded_answer_on_success():
    def fake_call_fn(api_key, model_name, prompt):
        assert api_key == "test-key"
        assert "EVIDENCE" in prompt
        return _valid_raw_response()

    client = GeminiClient(api_key="test-key", call_fn=fake_call_fn)
    answer = client.generate("some prompt containing EVIDENCE section")

    assert answer.issue_summary == "Battery mode is active."


def test_generate_raises_when_api_key_missing():
    client = GeminiClient(api_key=None, call_fn=lambda *a, **k: _valid_raw_response())
    # Force settings.gemini_api_key to also be unset for this test by
    # explicitly passing an empty string rather than relying on env state.
    client._api_key = None
    with pytest.raises(GeminiGenerationError, match="not configured"):
        client.generate("prompt")


def test_generate_wraps_network_errors():
    def failing_call_fn(api_key, model_name, prompt):
        raise TimeoutError("upstream timed out")

    client = GeminiClient(api_key="test-key", call_fn=failing_call_fn)
    with pytest.raises(GeminiGenerationError, match="Gemini API call failed"):
        client.generate("prompt")


def test_generate_wraps_invalid_json_response():
    client = GeminiClient(api_key="test-key", call_fn=lambda *a, **k: "not valid json")
    with pytest.raises(GeminiGenerationError, match="failed validation"):
        client.generate("prompt")


def test_generate_wraps_incomplete_response():
    incomplete = json.dumps({"issue_summary": "only this field"})
    client = GeminiClient(api_key="test-key", call_fn=lambda *a, **k: incomplete)
    with pytest.raises(GeminiGenerationError, match="failed validation"):
        client.generate("prompt")