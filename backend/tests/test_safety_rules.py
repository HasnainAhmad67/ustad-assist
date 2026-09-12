"""Tests for engine/safety/safety_rules.py."""

from engine.contracts import SafetyCategory
from engine.retrieval.exact_match import find_exact_match
from engine.safety.safety_rules import combine_safety, evaluate_evidence_safety, evaluate_text_safety
from pathlib import Path

from engine.kb_loader import KnowledgeBase

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def test_fire_or_smoke_always_escalates():
    info = evaluate_text_safety("We noticed a burning smell coming from the unit.")
    assert info.escalate is True
    assert info.reason_category == SafetyCategory.FIRE_OR_SMOKE.value


def test_electrical_hazard_escalates():
    info = evaluate_text_safety("Warning: high voltage remains inside even after disconnection.")
    assert info.escalate is True
    assert info.reason_category == SafetyCategory.ELECTRICAL_HAZARD.value


def test_battery_hazard_escalates():
    info = evaluate_text_safety("The battery shows visible swelling.")
    assert info.escalate is True
    assert info.reason_category == SafetyCategory.BATTERY_HAZARD.value


def test_technician_only_without_escalation_keyword():
    info = evaluate_text_safety("This check must be performed by qualified personnel.")
    assert info.escalate is False
    assert info.technician_only is True
    assert info.reason_category == SafetyCategory.TECHNICIAN_ONLY_PROCEDURE.value


def test_benign_text_produces_no_safety_flags():
    info = evaluate_text_safety("Restart the inverter and check the display again.")
    assert info.escalate is False
    assert info.technician_only is False
    assert info.reason_category == SafetyCategory.NONE.value


def test_empty_text_produces_no_safety_flags():
    info = evaluate_text_safety("", None, "   ")
    assert info.escalate is False
    assert info.technician_only is False


def test_growatt_201_evidence_escalates_on_high_voltage_warning():
    """The real Growatt 201 record's safety_warning mentions dangerous high
    voltages and residual charge — this must escalate, not just note
    technician-only guidance."""
    kb = _kb()
    record = find_exact_match(kb.verified_records(), "solar_inverter", "Growatt", "MIN 3000 TL-X", "201")
    info = evaluate_evidence_safety(record)
    assert info.escalate is True


def test_combine_safety_or_logic_never_drops_a_hazard():
    calm = evaluate_text_safety("Everything looks fine.")
    hazardous = evaluate_text_safety("There is a fire risk here.")

    combined = combine_safety(calm, hazardous)
    assert combined.escalate is True
    assert combined.reason_category == SafetyCategory.FIRE_OR_SMOKE.value


def test_combine_safety_with_no_infos_is_safe_default():
    combined = combine_safety()
    assert combined.escalate is False
    assert combined.technician_only is False