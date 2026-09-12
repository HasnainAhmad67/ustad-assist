"""
Builds the Gemini prompt strictly from an EvidenceBundle.

This is the only channel through which any knowledge-base content reaches
Gemini. Gemini never sees the raw dataset file, other manufacturers'
records, or anything not already selected by retrieval for this specific
query.
"""

from typing import Iterable, List

from engine.contracts import EvidenceBundle, NormalizedRecord
from engine.grounding.response_contract import RESPONSE_JSON_SCHEMA_DESCRIPTION


def _format_list(items: List[str], empty_label: str) -> str:
    if not items:
        return f"(none — {empty_label})"
    return "\n".join(f"- {item}" for item in items)


def _build_evidence_block(record: NormalizedRecord) -> str:
    return f"""
Equipment: {record.equipment_category} — {record.manufacturer} {record.model}
Reported issue/code: {record.code}
Issue title (from manual): {record.issue_title}
Documented meaning: {record.meaning}

Documented possible causes:
{_format_list(record.possible_causes, "the manual does not state a cause")}

Documented troubleshooting steps:
{_format_list(record.troubleshooting_steps, "the manual does not state a step")}

Documented safe user checks:
{_format_list(record.safe_user_checks, "the manual does not list a user-safe check")}

Documented technician-only checks:
{_format_list(record.technician_only_checks, "the manual does not list a technician-only check")}
""".strip()


def build_prompt(bundle: EvidenceBundle) -> str:
    """
    Raises ValueError if the bundle has no matched records — a prompt
    should never be built for evidence that doesn't exist; the caller
    (engine/query_builder.py) must not reach this point unless retrieval
    already succeeded.
    """
    if not bundle.matched_records:
        raise ValueError(
            "Cannot build a grounding prompt from an EvidenceBundle with no matched records."
        )

    record = bundle.matched_records[0]
    evidence_block = _build_evidence_block(record)

    return f"""
You are explaining verified equipment manual evidence to a technician or
end user. You must rely ONLY on the evidence below. You are not a source
of technical knowledge yourself — you are explaining evidence that has
already been retrieved and verified by a separate system, and citation
information is handled separately from your response.

EVIDENCE (the only source of truth you may use):
{evidence_block}

{RESPONSE_JSON_SCHEMA_DESCRIPTION}
""".strip()