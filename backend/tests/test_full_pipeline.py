"""
End-to-end tests for engine/query_builder.py::run_troubleshoot — the full
allow-list -> retrieval -> grounding -> validation pipeline.

A fake GeminiClient (constructed with an injected call_fn) is used
throughout so these tests run without network access or a real API key.
This validates PIPELINE WIRING, not the real Gemini API's output quality —
see the Phase 3 handoff notes for what still needs a real key to confirm.
"""

import json
from pathlib import Path

from engine.grounding.gemini_client import GeminiClient, GeminiGenerationError
from engine.kb_loader import KnowledgeBase
from engine.query_builder import build_query, run_troubleshoot
from engine.contracts import TroubleshootStatus

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def _fake_gemini_client(raw_response: str) -> GeminiClient:
    return GeminiClient(api_key="test-key", call_fn=lambda api_key, model_name, prompt: raw_response)


def _valid_raw_response(next_action="Restart the inverter.") -> str:
    return json.dumps(
        {
            "issue_summary": "Leakage current too high.",
            "meaning_explanation": "More current than expected is leaking to ground.",
            "cause_explanations": ["Could be wiring or insulation related."],
            "safe_check_guidance": [],
            "technician_only_guidance": ["A qualified electrician should inspect the wiring."],
            "next_action": next_action,
        }
    )


def test_full_pipeline_verified_result_for_growatt_201():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )
    client = _fake_gemini_client(_valid_raw_response())

    result = run_troubleshoot(kb, query, gemini_client=client)

    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    assert result.evidence is not None
    assert result.evidence.retrieval_method == "exact"
    assert result.grounded_answer is not None
    assert result.grounded_answer.issue_summary == "Leakage current too high."
    # The Growatt 201 record's own safety_warning mentions high voltage,
    # so the final combined safety must escalate regardless of how calmly
    # Gemini worded its explanation.
    assert result.safety.escalate is True


def test_full_pipeline_equipment_not_supported_never_calls_gemini():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="SomeOtherBrand",
        model="XYZ-1000",
        code="201",
    )

    class _ExplodingClient:
        def generate(self, prompt):
            raise AssertionError("Gemini must never be called for unsupported equipment")

    result = run_troubleshoot(kb, query, gemini_client=_ExplodingClient())

    assert result.status == TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED
    assert result.grounded_answer is None
    assert result.safety is None


def test_full_pipeline_no_evidence_never_calls_gemini():
    kb = _kb()
    query = build_query(
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="Totally Nonexistent Code",
    )

    class _ExplodingClient:
        def generate(self, prompt):
            raise AssertionError("Gemini must never be called when no evidence was retrieved")

    class _NoHitMatcher:
        """Stands in for the real embedding-based matcher so this test
        doesn't require network access — it deliberately returns no hits,
        exercising the 'no exact and no semantic match' branch."""

        def search(self, *args, **kwargs):
            return []

    result = run_troubleshoot(
        kb, query, gemini_client=_ExplodingClient(), semantic_matcher=_NoHitMatcher()
    )

    assert result.status == TroubleshootStatus.ISSUE_NOT_VERIFIED
    assert result.grounded_answer is None


def test_full_pipeline_gemini_failure_returns_error_not_fabricated_success():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )

    class _FailingClient:
        def generate(self, prompt):
            raise GeminiGenerationError("simulated API outage")

    result = run_troubleshoot(kb, query, gemini_client=_FailingClient())

    assert result.status == TroubleshootStatus.ERROR
    assert result.grounded_answer is None
    # Evidence-level safety must still be present even though generation failed.
    assert result.evidence is not None
    assert result.safety is not None
    assert result.safety.escalate is True


def test_full_pipeline_malformed_gemini_response_returns_error():
    kb = _kb()
    query = build_query(
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="Battery mode",
    )
    client = _fake_gemini_client("not valid json at all")

    result = run_troubleshoot(kb, query, gemini_client=client)

    assert result.status == TroubleshootStatus.ERROR
    assert result.grounded_answer is None