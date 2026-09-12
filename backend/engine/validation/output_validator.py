"""
Orchestrates the full post-retrieval validation sequence: citation check ->
safety check (evidence text + generated text) -> final status decision.

This is the ONLY module allowed to decide whether a generated response is
shown to the user as verified, downgraded, or treated as an error — and it
never trusts Gemini's own claims about itself, only the EvidenceBundle
(via citation_validator.py) and the deterministic safety rules (via
engine/safety/).
"""

from dataclasses import dataclass
from typing import Optional

from engine.contracts import EvidenceBundle, GroundedAnswer, SafetyInfo, TroubleshootStatus
from engine.safety.safety_rules import combine_safety, evaluate_evidence_safety, evaluate_text_safety
from engine.validation.citation_validator import validate_citation


@dataclass(frozen=True)
class ValidatedResult:
    status: TroubleshootStatus
    message: str
    safety: SafetyInfo


def _generated_text_for_safety_scan(answer: GroundedAnswer) -> str:
    return " ".join(
        [
            answer.issue_summary,
            answer.meaning_explanation,
            *answer.cause_explanations,
            *answer.safe_check_guidance,
            *answer.technician_only_guidance,
            answer.next_action,
        ]
    )


def validate_output(
    evidence: Optional[EvidenceBundle],
    grounded_answer: Optional[GroundedAnswer],
) -> ValidatedResult:
    citation_check = validate_citation(evidence)
    if not citation_check.valid:
        return ValidatedResult(
            status=TroubleshootStatus.ISSUE_NOT_VERIFIED,
            message=f"Evidence could not be verified: {citation_check.reason}",
            safety=SafetyInfo(escalate=False, technician_only=False),
        )

    # citation_check.valid implies evidence and evidence.matched_records are non-empty.
    record = evidence.matched_records[0]  # type: ignore[union-attr]
    evidence_safety = evaluate_evidence_safety(record)

    if grounded_answer is None:
        # Generation failed upstream, but the evidence itself is still
        # verified — surface this as an explicit error, never as a
        # fabricated success, while still carrying the evidence-level
        # safety info forward so a hazard is never lost just because
        # Gemini failed to respond.
        return ValidatedResult(
            status=TroubleshootStatus.ERROR,
            message="Evidence was found and verified, but grounded generation failed.",
            safety=evidence_safety,
        )

    generated_text_safety = evaluate_text_safety(_generated_text_for_safety_scan(grounded_answer))
    final_safety = combine_safety(evidence_safety, generated_text_safety)

    return ValidatedResult(
        status=TroubleshootStatus.VERIFIED_RESULT,
        message="Response validated against retrieved evidence.",
        safety=final_safety,
    )