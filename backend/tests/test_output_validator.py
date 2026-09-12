"""Tests for engine/validation/output_validator.py."""

from pathlib import Path

from engine.contracts import EvidenceBundle, GroundedAnswer, Query, TroubleshootStatus
from engine.kb_loader import KnowledgeBase
from engine.retrieval.exact_match import find_exact_match
from engine.validation.output_validator import validate_output

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def _growatt_bundle() -> EvidenceBundle:
    kb = _kb()
    record = find_exact_match(kb.verified_records(), "solar_inverter", "Growatt", "MIN 3000 TL-X", "201")
    query = Query(equipment_category="solar_inverter", manufacturer="Growatt", model="MIN 3000 TL-X", code="201")
    return EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")


def _benign_answer() -> GroundedAnswer:
    return GroundedAnswer(
        issue_summary="Leakage current too high.",
        meaning_explanation="More current than expected is leaking to ground.",
        cause_explanations=[],
        safe_check_guidance=[],
        technician_only_guidance=["A qualified electrician should inspect the wiring."],
        next_action="Restart the inverter.",
    )


def test_missing_evidence_returns_issue_not_verified():
    result = validate_output(evidence=None, grounded_answer=None)
    assert result.status == TroubleshootStatus.ISSUE_NOT_VERIFIED


def test_generation_failure_with_valid_evidence_returns_error_not_success():
    bundle = _growatt_bundle()
    result = validate_output(evidence=bundle, grounded_answer=None)
    assert result.status == TroubleshootStatus.ERROR
    # Evidence-level safety must still be carried forward even though
    # generation failed — the Growatt 201 record's safety_warning mentions
    # high voltage.
    assert result.safety.escalate is True


def test_valid_evidence_and_answer_returns_verified_result():
    bundle = _growatt_bundle()
    answer = _benign_answer()
    result = validate_output(evidence=bundle, grounded_answer=answer)
    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    # The Growatt 201 evidence itself carries a high-voltage warning, so
    # even a calmly-worded generated answer must still escalate.
    assert result.safety.escalate is True


def test_hazard_introduced_only_in_generated_text_still_escalates():
    """
    Confirms safety is evaluated on BOTH evidence and generated text
    independently — a category not present in the evidence's own safety
    text (here, simulated as absent) but appearing in the generated
    explanation must still trigger escalation.
    """
    bundle = _growatt_bundle()
    answer = GroundedAnswer(
        issue_summary="Leakage current too high.",
        meaning_explanation="More current than expected is leaking to ground.",
        cause_explanations=["We noticed a burning smell during testing."],
        safe_check_guidance=[],
        technician_only_guidance=[],
        next_action="Restart the inverter.",
    )
    result = validate_output(evidence=bundle, grounded_answer=answer)
    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    assert result.safety.escalate is True


def test_incomplete_citation_downgrades_to_issue_not_verified_even_with_a_good_answer():
    from engine.contracts import NormalizedRecord, SourceCitation

    incomplete_record = NormalizedRecord(
        record_id="x",
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        model_aliases=[],
        model_family=[],
        manual_title="",  # missing -> citation check must fail
        manual_version=None,
        manual_language="English",
        code="Battery mode",
        issue_type="alarm",
        issue_title="Test",
        meaning="Test",
        possible_causes=[],
        troubleshooting_steps=[],
        safe_user_checks=[],
        technician_only_checks=[],
        safety_warning="",
        global_safety_notes=[],
        source=SourceCitation(manual_title="", page=None, official_url=None),
        verification_status="verified",
        verification_notes=None,
    )
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[incomplete_record], retrieval_method="exact")

    result = validate_output(evidence=bundle, grounded_answer=_benign_answer())
    assert result.status == TroubleshootStatus.ISSUE_NOT_VERIFIED