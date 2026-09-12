"""
Escalation decision + user-facing escalation messaging.

Kept as a distinct module from safety_rules.py deliberately: safety_rules
answers "does this text describe a hazard" (classification); this module
answers "what does the product tell the user to do about it" (response).
Separating them means the messaging can be refined per category later
without touching the classification rules that drive escalation itself.
"""

from engine.contracts import SafetyCategory, SafetyInfo

_ESCALATION_MESSAGES = {
    SafetyCategory.FIRE_OR_SMOKE.value: (
        "Stop immediately. If you notice smoke, a burning smell, or fire, "
        "disconnect power only if it is safe to do so, evacuate the area, "
        "and contact emergency services and a qualified technician."
    ),
    SafetyCategory.ELECTRICAL_HAZARD.value: (
        "This involves a high-voltage or internal electrical hazard. Do not "
        "open the unit or attempt further checks yourself. Contact a "
        "qualified electrician or the manufacturer's authorized service."
    ),
    SafetyCategory.BATTERY_HAZARD.value: (
        "Battery swelling or leakage can be hazardous. Do not touch or "
        "disturb the battery. Contact a qualified technician for safe handling."
    ),
    SafetyCategory.REPEATED_FAULT.value: (
        "A fault that keeps recurring after following the manual's steps "
        "should be treated as a hardware issue. Contact a qualified "
        "technician rather than repeating the same checks."
    ),
}

_DEFAULT_ESCALATION_MESSAGE = (
    "This issue may involve a safety hazard. Contact a qualified technician "
    "before proceeding further."
)


def should_escalate(safety: SafetyInfo) -> bool:
    return bool(safety.escalate)


def build_escalation_message(safety: SafetyInfo) -> str:
    """Returns "" when escalation isn't triggered — callers should check
    should_escalate() rather than inferring escalation from a non-empty
    message string."""
    if not safety.escalate:
        return ""
    return _ESCALATION_MESSAGES.get(safety.reason_category or "", _DEFAULT_ESCALATION_MESSAGE)