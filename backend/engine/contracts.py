"""
Shared data contracts for the Ustad Assist troubleshooting engine.

This module defines shapes only — no logic, no I/O, no API calls. Every
other engine module imports its vocabulary from here so that P0 (typed
input) and P1 (confirmed image input) can be guaranteed to produce and
consume identical types, which is what makes "one troubleshooting engine"
an enforceable fact rather than just an intention.

Phase 1 note: `Query`, `SafetyInfo`, and `EvidenceBundle` are defined now
so the contract is fixed before retrieval/grounding are implemented in
later phases, but nothing in this codebase populates them yet. Only
`NormalizedRecord`, `SourceCitation`, and `CatalogModel` are actually
produced by Phase 1 code (engine/kb_loader.py).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EquipmentCategory(str, Enum):
    SOLAR_INVERTER = "solar_inverter"
    UPS = "ups"


class VerificationStatus(str, Enum):
    """Mirrors the verification statuses defined in PRD Section 16."""

    VERIFIED = "verified"
    PARTIALLY_VERIFIED = "partially_verified"
    NOT_VERIFIED = "not_verified"
    DUPLICATE = "duplicate"
    UNSUPPORTED = "unsupported"


class TroubleshootStatus(str, Enum):
    """
    The status field every /api/troubleshoot response carries (architecture
    §5 / §10). Not produced by any code yet in Phase 1 — reserved for the
    engine orchestration phase.
    """

    VERIFIED_RESULT = "verified_result"
    ISSUE_NOT_VERIFIED = "issue_not_verified"
    EQUIPMENT_NOT_SUPPORTED = "equipment_not_supported"
    NEEDS_CONFIRMATION = "needs_confirmation"
    ERROR = "error"


@dataclass(frozen=True)
class SourceCitation:
    """
    Citation metadata for a single piece of evidence. Populated directly
    from the verified dataset's `source` block — never invented.
    """

    manual_title: str
    manual_document_number: Optional[str] = None
    page: Optional[str] = None
    official_url: Optional[str] = None
    # Not present in the current dataset (see architecture §0's schema
    # findings). Left as explicit None rather than fabricated — will be
    # populated once the manuals are re-verified per PRD Section 52.
    section: Optional[str] = None
    pdf_page: Optional[str] = None


@dataclass(frozen=True)
class NormalizedRecord:
    """
    The canonical, normalized shape every entry in
    backend/data/verified_records.json is converted into by
    engine/kb_loader.py. No other module should read the raw dataset
    file's field names (which differ between Growatt and Eaton records)
    directly — everything downstream consumes this shape only.
    """

    record_id: str
    equipment_category: str
    manufacturer: str
    model: str
    model_aliases: List[str]
    model_family: List[str]
    manual_title: str
    manual_version: Optional[str]
    manual_language: str
    code: str
    issue_type: Optional[str]
    issue_title: str
    meaning: str
    possible_causes: List[str]
    troubleshooting_steps: List[str]
    safe_user_checks: List[str]
    technician_only_checks: List[str]
    safety_warning: str
    global_safety_notes: List[str]
    source: SourceCitation
    verification_status: str
    verification_notes: Optional[str]


@dataclass(frozen=True)
class CatalogModel:
    """One supported (equipment_category, manufacturer, model) combination,
    derived from verified records — never hand-maintained."""

    equipment_category: str
    manufacturer: str
    model: str
    model_aliases: List[str]


@dataclass(frozen=True)
class Query:
    """
    The canonical troubleshooting query shape, produced identically
    whether the request originated from typed P0 input or a confirmed P1
    image detection. Not yet consumed by any logic in Phase 1 — defined
    here so the contract exists before engine/query_builder.py and
    retrieval are implemented.
    """

    equipment_category: str
    manufacturer: str
    model: str
    code: Optional[str] = None
    symptom: Optional[str] = None
    source: str = "manual"  # "manual" | "image"


@dataclass(frozen=True)
class SafetyInfo:
    """Structured safety decision, independent of Gemini's wording."""

    escalate: bool
    technician_only: bool
    warning_text: Optional[str] = None
    reason_category: Optional[str] = None


@dataclass(frozen=True)
class EvidenceBundle:
    """
    The only object allowed to cross from retrieval into Gemini grounding.
    Not populated by any logic in Phase 1 — defined here so the retrieval
    and grounding phases have a fixed target shape.
    """

    query: Query
    matched_records: List[NormalizedRecord] = field(default_factory=list)
    retrieval_method: Optional[str] = None  # "exact" | "semantic"


class SafetyCategory(str, Enum):
    """
    Fixed hazard/procedure categories used by engine/safety/safety_rules.py
    for deterministic classification. Stored as plain strings in
    SafetyInfo.reason_category so SafetyInfo's shape never had to change
    when this enum was introduced.
    """

    NONE = "none"
    FIRE_OR_SMOKE = "fire_or_smoke"
    ELECTRICAL_HAZARD = "electrical_hazard"
    BATTERY_HAZARD = "battery_hazard"
    REPEATED_FAULT = "repeated_fault"
    TECHNICIAN_ONLY_PROCEDURE = "technician_only_procedure"


@dataclass(frozen=True)
class GroundedAnswer:
    """
    The structured explanation Gemini is allowed to produce, per
    engine/grounding/response_contract.py.

    Deliberately excludes citation fields (manual title, document number,
    page, official URL) and any safety/verification classification —
    those are never Gemini's to originate. Citation always comes from
    EvidenceBundle; safety classification always comes from
    engine/safety/.
    """

    issue_summary: str
    meaning_explanation: str
    cause_explanations: List[str]
    safe_check_guidance: List[str]
    technician_only_guidance: List[str]
    next_action: str


@dataclass(frozen=True)
class TroubleshootResult:
    """
    The final, fully validated result of the P0/P1-shared engine pipeline
    (allow-list -> retrieval -> grounding -> validation). This is what a
    later API route (Phase 4) will serialize into the public response
    schema.
    """

    status: TroubleshootStatus
    message: str
    evidence: Optional[EvidenceBundle]
    grounded_answer: Optional[GroundedAnswer]
    safety: Optional[SafetyInfo]