"""
Tests for engine/retrieval/exact_match.py.

Covers PRD Section 44 Test 1 (supported model + verified error) and
Test 8 (same code across different models -> exact filtering must not
cross models), plus the alias-matching behavior added during
normalization.
"""

from pathlib import Path

from engine.kb_loader import KnowledgeBase
from engine.retrieval.exact_match import filter_by_equipment_identity, find_exact_match

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def test_growatt_error_201_exact_match():
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )
    assert hit is not None
    assert hit.manufacturer == "Growatt"
    assert hit.model == "MIN 3000 TL-X"
    assert hit.code == "201"
    assert hit.source.page == "37"


def test_growatt_model_alias_matches():
    """The catalog lists 'MIN 3000TL-X' as an alias of 'MIN 3000 TL-X'."""
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000TL-X",  # alias form, not the canonical form
        code="201",
    )
    assert hit is not None
    assert hit.model == "MIN 3000 TL-X"


def test_eaton_battery_mode_exact_match():
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="Battery mode",
    )
    assert hit is not None
    assert hit.manufacturer == "Eaton"
    assert hit.source.page == "35"


def test_wrong_manufacturer_is_rejected():
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Eaton",  # wrong manufacturer for a Growatt code
        model="MIN 3000 TL-X",
        code="201",
    )
    assert hit is None


def test_wrong_model_is_rejected_even_with_matching_code():
    """
    A code that exists for one model must never match a different model,
    even within the same manufacturer/category — this is the exact-model
    filtering guarantee.
    """
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 6000 TL-X",  # a real family member, but not a KB-supported model
        code="201",
    )
    assert hit is None


def test_missing_code_returns_none():
    kb = _kb()
    hit = find_exact_match(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="",
    )
    assert hit is None


def test_filter_by_equipment_identity_scopes_to_one_model_only():
    kb = _kb()
    growatt_pool = filter_by_equipment_identity(
        kb.verified_records(),
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
    )
    assert len(growatt_pool) > 0
    assert all(r.manufacturer == "Growatt" and r.model == "MIN 3000 TL-X" for r in growatt_pool)

    eaton_pool = filter_by_equipment_identity(
        kb.verified_records(),
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
    )
    assert len(eaton_pool) > 0
    assert all(r.manufacturer == "Eaton" for r in eaton_pool)

    # The two pools must never overlap.
    assert not set(r.record_id for r in growatt_pool) & set(r.record_id for r in eaton_pool)