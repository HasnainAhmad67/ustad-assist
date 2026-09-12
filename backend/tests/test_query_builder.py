"""
Tests for engine/query_builder.py — the allow-list check and the engine's
single public entrypoint (run_troubleshoot_query).
"""

from pathlib import Path

from engine.contracts import TroubleshootStatus
from engine.kb_loader import KnowledgeBase
from engine.query_builder import build_query, run_troubleshoot_query

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def test_build_query_normalizes_whitespace():
    query = build_query(
        equipment_category="  solar_inverter  ",
        manufacturer=" Growatt ",
        model=" MIN 3000 TL-X ",
        code=" 201 ",
    )
    assert query.equipment_category == "solar_inverter"
    assert query.manufacturer == "Growatt"
    assert query.model == "MIN 3000 TL-X"
    assert query.code == "201"
    assert query.source == "manual"


def test_build_query_blank_code_becomes_none():
    query = build_query(
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="   ",
    )
    assert query.code is None


def test_supported_model_with_exact_code_returns_verified_result():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )
    result = run_troubleshoot_query(kb, query)

    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    assert result.evidence_bundle is not None
    assert result.evidence_bundle.retrieval_method == "exact"


def test_supported_model_via_alias_is_accepted():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000TL-X",  # alias form
        code="201",
    )
    result = run_troubleshoot_query(kb, query)
    assert result.status == TroubleshootStatus.VERIFIED_RESULT


def test_unsupported_manufacturer_returns_equipment_not_supported():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="SomeOtherBrand",
        model="XYZ-1000",
        code="201",
    )
    result = run_troubleshoot_query(kb, query)

    assert result.status == TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED
    assert result.evidence_bundle is None


def test_unsupported_model_for_a_supported_manufacturer_returns_equipment_not_supported():
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 9999 TL-X",  # not one of the KB-supported models
        code="201",
    )
    result = run_troubleshoot_query(kb, query)

    assert result.status == TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED


def test_wrong_equipment_category_for_a_real_manufacturer_model_pair_is_not_supported():
    """Eaton's 5PX1500IRT2UG2 is a UPS, not a solar_inverter — the identity
    must match on all three fields together, not just manufacturer+model."""
    kb = _kb()
    query = build_query(
        equipment_category="solar_inverter",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="Battery mode",
    )
    result = run_troubleshoot_query(kb, query)

    assert result.status == TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED