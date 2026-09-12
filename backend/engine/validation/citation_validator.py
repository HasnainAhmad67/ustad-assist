"""
Citation validation — confirms the evidence bundle backing a response
actually has real, complete source information before that response can
be shown to the user as verified.

This never re-derives, guesses, or "fixes" an incomplete citation — a
failure here downgrades the overall result (handled by
output_validator.py), it does not patch the citation itself.
"""

from dataclasses import dataclass
from typing import Optional

from engine.contracts import EvidenceBundle


@dataclass(frozen=True)
class CitationCheckResult:
    valid: bool
    reason: str


def validate_citation(bundle: Optional[EvidenceBundle]) -> CitationCheckResult:
    if bundle is None or not bundle.matched_records:
        return CitationCheckResult(valid=False, reason="No evidence bundle to cite.")

    record = bundle.matched_records[0]
    source = record.source

    if not source.manual_title or not source.manual_title.strip():
        return CitationCheckResult(valid=False, reason="Matched record has no manual title.")

    if not source.page and not source.official_url:
        return CitationCheckResult(
            valid=False,
            reason="Matched record has neither a page reference nor an official source URL.",
        )

    if not record.code or not record.code.strip():
        return CitationCheckResult(valid=False, reason="Matched record has no code/alarm identifier.")

    return CitationCheckResult(valid=True, reason="Citation is complete.")