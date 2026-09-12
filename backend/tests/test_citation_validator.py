"""Tests for engine/validation/citation_validator.py."""

from pathlib import Path

from engine.contracts import EvidenceBundle, NormalizedRecord, Query, SourceCitation
from engine.kb_loader import KnowledgeBase
from engine.retrieval.exact_match import find_exact_match
from engine.validation.citation_validator import validate_citation

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def _bare_record(**overrides) -> NormalizedRecord:
    base = dict(
        record_id="x",
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        model_aliases=[],
        model_family=[],
        manual_title="Some Manual",
        manual_version="V1",
        manual_language="English",
        code="Battery mode",
        issue_type="alarm",
        issue_title="Test",
        meaning="Test meaning",
        possible_causes=[],
        troubleshooting_steps=[],
        safe_user_checks=[],
        technician_only_checks=[],
        safety_warning="",
        global_safety_notes=[],
        source=SourceCitation(manual_title="Some Manual", page="10"),
        verification_status="verified",
        verification_notes=None,
    )
    base.update(overrides)
    return NormalizedRecord(**base)


def test_real_growatt_record_passes_citation_check():
    kb = _kb()
    record = find_exact_match(kb.verified_records(), "solar_inverter", "Growatt", "MIN 3000 TL-X", "201")
    query = Query(equipment_category="solar_inverter", manufacturer="Growatt", model="MIN 3000 TL-X", code="201")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    result = validate_citation(bundle)
    assert result.valid is True


def test_none_bundle_fails():
    result = validate_citation(None)
    assert result.valid is False


def test_empty_bundle_fails():
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="X")
    bundle = EvidenceBundle(query=query, matched_records=[], retrieval_method=None)
    result = validate_citation(bundle)
    assert result.valid is False


def test_missing_manual_title_fails():
    record = _bare_record(manual_title="", source=SourceCitation(manual_title="", page="10"))
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    result = validate_citation(bundle)
    assert result.valid is False
    assert "manual title" in result.reason.lower()


def test_missing_page_and_url_fails():
    record = _bare_record(source=SourceCitation(manual_title="Some Manual", page=None, official_url=None))
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    result = validate_citation(bundle)
    assert result.valid is False


def test_url_alone_is_sufficient_without_a_page():
    record = _bare_record(
        source=SourceCitation(manual_title="Some Manual", page=None, official_url="https://example.com/manual.pdf")
    )
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    result = validate_citation(bundle)
    assert result.valid is True


def test_missing_code_fails():
    record = _bare_record(code="")
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    result = validate_citation(bundle)
    assert result.valid is False