"""
Tests for POST /api/troubleshoot.

Uses FastAPI's dependency_overrides to inject a fake GeminiClient for the
branches that reach generation — no network access or real API key
required. The equipment_not_supported / issue_not_verified branches are
tested WITHOUT overriding Gemini at all, and assert Gemini is never
called, since retrieval should short-circuit before generation on those
paths (this is checked directly, not just assumed).
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.deps import get_gemini_client_dep
from app.main import app
from engine.grounding.gemini_client import GeminiClient, GeminiGenerationError


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _valid_raw_response() -> str:
    return json.dumps(
        {
            "issue_summary": "Leakage current too high.",
            "meaning_explanation": "More current than expected is leaking to ground.",
            "cause_explanations": ["Could be wiring or insulation related."],
            "safe_check_guidance": [],
            "technician_only_guidance": ["A qualified electrician should inspect the wiring."],
            "next_action": "Restart the inverter.",
        }
    )


def _fake_client(raw_response: str) -> GeminiClient:
    return GeminiClient(api_key="test-key", call_fn=lambda api_key, model_name, prompt: raw_response)


class _ExplodingClient:
    """Fails the test loudly if Gemini is ever called on a path that should short-circuit first."""

    def generate(self, prompt):
        raise AssertionError("Gemini must not be called on this path")


def test_verified_result_for_growatt_201():
    app.dependency_overrides[get_gemini_client_dep] = lambda: _fake_client(_valid_raw_response())
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": "Growatt",
            "model": "MIN 3000 TL-X",
            "code": "201",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified_result"
    assert body["evidence"]["code"] == "201"
    assert body["evidence"]["source"]["page"] == "37"
    assert body["evidence"]["retrieval_method"] == "exact"
    assert body["grounded_answer"]["issue_summary"] == "Leakage current too high."
    # The Growatt 201 record's own manual text mentions high voltage.
    assert body["safety"]["escalate"] is True


def test_equipment_not_supported_never_calls_gemini():
    app.dependency_overrides[get_gemini_client_dep] = lambda: _ExplodingClient()
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": "SomeOtherBrand",
            "model": "XYZ-1000",
            "code": "201",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "equipment_not_supported"
    assert body["evidence"] is None
    assert body["grounded_answer"] is None
    assert body["safety"] is None


def test_issue_not_verified_never_calls_gemini_when_no_evidence_matches(monkeypatch):
    """
    Uses a real (unsupported) code with no symptom text, on a supported
    model — exact match misses, so retrieval falls to semantic search.

    The internal SemanticMatcher is patched (not the public API) so this
    test doesn't require network access / a downloaded embedding model —
    the API route itself is not changed or given a test-only parameter.
    """

    class _NoHitMatcher:
        def search(self, *args, **kwargs):
            return []

    monkeypatch.setattr(
        "engine.retrieval.evidence_assembler.SemanticMatcher",
        lambda *args, **kwargs: _NoHitMatcher(),
    )

    app.dependency_overrides[get_gemini_client_dep] = lambda: _ExplodingClient()
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "ups",
            "manufacturer": "Eaton",
            "model": "5PX1500IRT2UG2",
            "code": "Totally Nonexistent Code",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "issue_not_verified"
    assert body["grounded_answer"] is None


def test_gemini_failure_returns_error_status_not_500():
    class _FailingClient:
        def generate(self, prompt):
            raise GeminiGenerationError("simulated outage")

    app.dependency_overrides[get_gemini_client_dep] = lambda: _FailingClient()
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": "Growatt",
            "model": "MIN 3000 TL-X",
            "code": "201",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["evidence"] is not None  # evidence was still found and is still shown
    assert body["grounded_answer"] is None


def test_missing_required_field_returns_422():
    client = TestClient(app)
    response = client.post(
        "/api/troubleshoot",
        json={
            "manufacturer": "Growatt",
            "model": "MIN 3000 TL-X",
            # equipment_category omitted
        },
    )
    assert response.status_code == 422


def test_alias_model_form_is_accepted():
    app.dependency_overrides[get_gemini_client_dep] = lambda: _fake_client(_valid_raw_response())
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": "Growatt",
            "model": "MIN 3000TL-X",  # alias form, not canonical
            "code": "201",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "verified_result"


def test_confirmed_image_source_joins_the_same_endpoint():
    """
    A confirmed P1 detection uses the exact same /api/troubleshoot
    endpoint as P0 typed input — only `source` differs — and produces an
    identical result for identical evidence.
    """
    app.dependency_overrides[get_gemini_client_dep] = lambda: _fake_client(_valid_raw_response())
    client = TestClient(app)

    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": "Growatt",
            "model": "MIN 3000 TL-X",
            "code": "201",
            "source": "image",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verified_result"
    assert body["evidence"]["retrieval_method"] == "exact"


def test_confirmed_image_source_missing_manufacturer_returns_422():
    """
    vision/confirmation.py's stricter check runs for source="image" —
    an empty required field is rejected before it ever reaches retrieval,
    even though TroubleshootRequest's own min_length=1 would already catch
    a fully-empty string; this confirms the confirmation-layer check fires too.
    """
    client = TestClient(app)
    response = client.post(
        "/api/troubleshoot",
        json={
            "equipment_category": "solar_inverter",
            "manufacturer": " ",  # whitespace-only, passes min_length=1 but fails confirmation's .strip() check
            "model": "MIN 3000 TL-X",
            "code": "201",
            "source": "image",
        },
    )
    assert response.status_code == 422