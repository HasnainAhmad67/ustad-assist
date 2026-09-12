"""
Deterministic safety classification — independent of Gemini's wording.

Runs against both raw evidence text (safety_warning + global_safety_notes)
and any generated explanation text, using fixed keyword/category rules
rather than asking a model to self-assess. This is what makes a safety
escalation impossible to skip via rephrasing: the same fixed rules apply
to Gemini's output as to the manual's own text, and a hazard found in
either pass is never dropped by the other.
"""

from typing import Iterable, List, Tuple

from engine.contracts import SafetyCategory, SafetyInfo

# Checked in order; the first matching category is used as the "primary"
# escalation reason. All hazard categories always escalate — none of them
# are soft warnings.
_ESCALATE_RULES: List[Tuple[SafetyCategory, List[str]]] = [
    (
        SafetyCategory.FIRE_OR_SMOKE,
        ["smoke", "fire", "burning smell", "burnt smell", "charring", "flames"],
    ),
    (
        SafetyCategory.ELECTRICAL_HAZARD,
        [
            "high voltage",
            "high-voltage",
            "energized",
            "live wire",
            "live circuit",
            "internal servicing",
            "bypass protection",
            "bypassing protection",
            "defeat the safety",
            "defeating the safety",
            "remove the cover",
            "damaged cable",
            "damaged wiring",
            "exposed wiring",
            "shock hazard",
        ],
    ),
    (
        SafetyCategory.BATTERY_HAZARD,
        [
            "battery swelling",
            "swollen battery",
            "swelling",
            "battery leakage",
            "leaking battery",
            "battery leak",
            "electrolyte",
        ],
    ),
    (
        SafetyCategory.REPEATED_FAULT,
        ["repeated trip", "keeps tripping", "trips repeatedly", "recurring fault"],
    ),
]

_TECHNICIAN_ONLY_HINTS = [
    "qualified personnel",
    "qualified electrician",
    "qualified technician",
    "licensed technician",
    "authorized service",
    "internal component",
    "open the enclosure",
    "disassemble",
    "servicing by qualified",
    "electrically qualified persons",
]

_ESCALATION_WARNING_TEXT = (
    "This condition may involve a safety hazard described in the official "
    "manual. Do not attempt further troubleshooting yourself — disconnect "
    "power only if it is safe to do so, and contact a qualified technician."
)

_TECHNICIAN_ONLY_WARNING_TEXT = (
    "The manual reserves this check for qualified service personnel. Do not "
    "attempt it yourself."
)


def _contains_any(text: str, phrases: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def evaluate_text_safety(*texts: str) -> SafetyInfo:
    """
    Scans one or more free-text strings for the fixed hazard/technician
    keyword patterns above. Used both for raw evidence text and for
    Gemini's generated explanation text — the same rules, applied the same
    way, regardless of which text produced them.
    """
    combined = " \n ".join(text for text in texts if text)
    if not combined.strip():
        return SafetyInfo(escalate=False, technician_only=False, reason_category=SafetyCategory.NONE.value)

    for category, phrases in _ESCALATE_RULES:
        if _contains_any(combined, phrases):
            return SafetyInfo(
                escalate=True,
                technician_only=True,
                warning_text=_ESCALATION_WARNING_TEXT,
                reason_category=category.value,
            )

    if _contains_any(combined, _TECHNICIAN_ONLY_HINTS):
        return SafetyInfo(
            escalate=False,
            technician_only=True,
            warning_text=_TECHNICIAN_ONLY_WARNING_TEXT,
            reason_category=SafetyCategory.TECHNICIAN_ONLY_PROCEDURE.value,
        )

    return SafetyInfo(escalate=False, technician_only=False, reason_category=SafetyCategory.NONE.value)


def evaluate_evidence_safety(record) -> SafetyInfo:
    """
    Convenience wrapper: evaluates a NormalizedRecord's own safety text
    (safety_warning + global_safety_notes) — meant to run BEFORE
    generation, per architecture doc v2 section 10 ("evaluated twice,
    independently of Gemini's involvement").
    """
    texts = [record.safety_warning, *record.global_safety_notes]
    return evaluate_text_safety(*texts)


def combine_safety(*infos: SafetyInfo) -> SafetyInfo:
    """
    Merges multiple SafetyInfo evaluations (e.g. evidence-level +
    generated-text-level) conservatively: escalate/technician_only are
    OR'd together. A hazard found by only one of the two passes is never
    dropped because the other pass didn't also find it.
    """
    if not infos:
        return SafetyInfo(escalate=False, technician_only=False, reason_category=SafetyCategory.NONE.value)

    escalate = any(info.escalate for info in infos)
    technician_only = any(info.technician_only for info in infos)

    reason = next((info.reason_category for info in infos if info.escalate and info.reason_category), None)
    if reason is None:
        reason = next(
            (info.reason_category for info in infos if info.technician_only and info.reason_category),
            None,
        )

    warning_text = next((info.warning_text for info in infos if info.escalate and info.warning_text), None)
    if warning_text is None:
        warning_text = next(
            (info.warning_text for info in infos if info.technician_only and info.warning_text),
            None,
        )

    return SafetyInfo(
        escalate=escalate,
        technician_only=technician_only,
        warning_text=warning_text,
        reason_category=reason or SafetyCategory.NONE.value,
    )