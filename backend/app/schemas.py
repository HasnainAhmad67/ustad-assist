"""
Pydantic models that define the public API contract.

This file is the single source of truth for the API's request/response
shapes. The frontend's TypeScript types (frontend/src/types/api.ts, built
in a later phase) should mirror this file — not the other way around.

Phase 1 only needs the catalog and health shapes. Troubleshoot/vision
request/response schemas are intentionally not added yet; they belong to
the phases that implement retrieval, grounding, and vision.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CatalogModelOut(BaseModel):
    """One supported exact model within a manufacturer."""

    # Pydantic v2 reserves the "model_" field-name prefix for its own
    # methods (model_dump, etc.) and warns on fields like `model_aliases`.
    # These are legitimate domain field names, not accidental collisions,
    # so the protected-namespace check is disabled for this schema only.
    model_config = ConfigDict(protected_namespaces=())

    model: str
    model_aliases: List[str] = Field(default_factory=list)


class CatalogManufacturerOut(BaseModel):
    """One supported manufacturer within an equipment category."""

    manufacturer: str
    models: List[CatalogModelOut]


class CatalogCategoryOut(BaseModel):
    """One supported equipment category."""

    equipment_category: str
    manufacturers: List[CatalogManufacturerOut]


class CatalogResponse(BaseModel):
    """
    Response for GET /api/catalog. Derived live from the verified
    knowledge base — never a hardcoded list — so the frontend's dropdowns
    can never drift out of sync with what's actually supported.
    """

    categories: List[CatalogCategoryOut]
    total_supported_models: int


class HealthResponse(BaseModel):
    """Response for GET /health — basic liveness + dataset sanity check."""

    status: str
    environment: str
    dataset_name: Optional[str] = None
    dataset_version: Optional[str] = None
    total_records: int
    verified_records: int


class TroubleshootRequest(BaseModel):
    """
    Request for POST /api/troubleshoot. Identical shape whether the caller
    is the P0 typed-input form or (once vision exists) a confirmed P1
    image detection — `source` records which one, but every field below is
    otherwise the same.
    """

    equipment_category: str
    manufacturer: str
    model: str
    code: Optional[str] = None
    symptom: Optional[str] = None
    source: str = "manual"  # "manual" | "image"


class SourceCitationOut(BaseModel):
    manual_title: str
    manual_document_number: Optional[str] = None
    page: Optional[str] = None
    official_url: Optional[str] = None


class EvidenceOut(BaseModel):
    """
    The verified evidence backing a result — always sourced from
    EvidenceBundle, never from anything Gemini produced. Present only when
    status == "verified_result" or "error" (evidence was found, but
    generation failed).
    """

    equipment_category: str
    manufacturer: str
    model: str
    code: str
    issue_title: str
    meaning: str
    possible_causes: List[str] = Field(default_factory=list)
    troubleshooting_steps: List[str] = Field(default_factory=list)
    safe_user_checks: List[str] = Field(default_factory=list)
    technician_only_checks: List[str] = Field(default_factory=list)
    source: SourceCitationOut
    retrieval_method: Optional[str] = None  # "exact" | "semantic"


class GroundedAnswerOut(BaseModel):
    """Gemini's plain-language explanation of the evidence. Present only
    when status == "verified_result"."""

    issue_summary: str
    meaning_explanation: str
    cause_explanations: List[str] = Field(default_factory=list)
    safe_check_guidance: List[str] = Field(default_factory=list)
    technician_only_guidance: List[str] = Field(default_factory=list)
    next_action: str


class SafetyOut(BaseModel):
    """
    The deterministic safety decision — structured fields, not prose to be
    parsed, so the frontend can render a consistent SafetyCard by
    branching on `escalate`/`technician_only` rather than scanning text.
    """

    escalate: bool
    technician_only: bool
    warning_text: Optional[str] = None
    reason_category: Optional[str] = None


class TroubleshootResponse(BaseModel):
    """
    Response for POST /api/troubleshoot. `status` is the field the
    frontend should branch on to decide which screen to render —
    never infer trust from the presence/absence of other fields alone.

    status values: "verified_result" | "issue_not_verified" |
    "equipment_not_supported" | "error"
    """

    status: str
    message: str
    evidence: Optional[EvidenceOut] = None
    grounded_answer: Optional[GroundedAnswerOut] = None
    safety: Optional[SafetyOut] = None