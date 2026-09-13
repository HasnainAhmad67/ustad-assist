"""
Maps internal engine dataclasses (engine/contracts.py) onto the public API
response schema (app/schemas.py).

Kept as its own explicit module rather than folded into the route handler:
per the architecture doc's design note, the engine's internal contract and
the public API contract are deliberately allowed to diverge over time
(e.g. once the dataset gains real verified_by/verified_at metadata) without
one forcing a change onto the other. This is the one seam where that
translation happens.
"""

from typing import Optional

from app.schemas import (
    EvidenceOut,
    GroundedAnswerOut,
    SafetyOut,
    SourceCitationOut,
    TroubleshootResponse,
)
from engine.contracts import TroubleshootResult


def to_troubleshoot_response(result: TroubleshootResult) -> TroubleshootResponse:
    evidence_out: Optional[EvidenceOut] = None
    if result.evidence is not None and result.evidence.matched_records:
        record = result.evidence.matched_records[0]
        evidence_out = EvidenceOut(
            equipment_category=record.equipment_category,
            manufacturer=record.manufacturer,
            model=record.model,
            code=record.code,
            issue_title=record.issue_title,
            meaning=record.meaning,
            possible_causes=record.possible_causes,
            troubleshooting_steps=record.troubleshooting_steps,
            safe_user_checks=record.safe_user_checks,
            technician_only_checks=record.technician_only_checks,
            source=SourceCitationOut(
                manual_title=record.source.manual_title,
                manual_document_number=record.source.manual_document_number,
                page=record.source.page,
                official_url=record.source.official_url,
            ),
            retrieval_method=result.evidence.retrieval_method,
            detailed_note=record.verification_notes,
        )

    grounded_answer_out: Optional[GroundedAnswerOut] = None
    if result.grounded_answer is not None:
        grounded_answer_out = GroundedAnswerOut(
            issue_summary=result.grounded_answer.issue_summary,
            meaning_explanation=result.grounded_answer.meaning_explanation,
            cause_explanations=result.grounded_answer.cause_explanations,
            safe_check_guidance=result.grounded_answer.safe_check_guidance,
            technician_only_guidance=result.grounded_answer.technician_only_guidance,
            next_action=result.grounded_answer.next_action,
        )

    safety_out: Optional[SafetyOut] = None
    if result.safety is not None:
        safety_out = SafetyOut(
            escalate=result.safety.escalate,
            technician_only=result.safety.technician_only,
            warning_text=result.safety.warning_text,
            reason_category=result.safety.reason_category,
        )

    return TroubleshootResponse(
        status=result.status.value,
        message=result.message,
        evidence=evidence_out,
        grounded_answer=grounded_answer_out,
        safety=safety_out,
    )
