"""Tests for engine/safety/escalation.py."""

from engine.contracts import SafetyCategory, SafetyInfo
from engine.safety.escalation import build_escalation_message, should_escalate


def test_should_escalate_true_when_flagged():
    info = SafetyInfo(escalate=True, technician_only=True, reason_category=SafetyCategory.FIRE_OR_SMOKE.value)
    assert should_escalate(info) is True


def test_should_escalate_false_when_not_flagged():
    info = SafetyInfo(escalate=False, technician_only=False)
    assert should_escalate(info) is False


def test_escalation_message_matches_category():
    info = SafetyInfo(escalate=True, technician_only=True, reason_category=SafetyCategory.BATTERY_HAZARD.value)
    message = build_escalation_message(info)
    assert "battery" in message.lower()


def test_escalation_message_empty_when_not_escalating():
    info = SafetyInfo(escalate=False, technician_only=True, reason_category=SafetyCategory.TECHNICIAN_ONLY_PROCEDURE.value)
    assert build_escalation_message(info) == ""


def test_escalation_message_falls_back_to_default_for_unknown_category():
    info = SafetyInfo(escalate=True, technician_only=True, reason_category="some_future_category")
    message = build_escalation_message(info)
    assert message  # non-empty fallback, never blank when escalate=True