"""
Query construction and the engine's public entrypoints.

This module is called identically whether the raw input came from a typed
P0 form or (in a later phase) a confirmed P1 image detection — both
produce the same kind of raw fields, and only this one path evaluates the
equipment allow-list, then retrieval, then (via run_troubleshoot) grounding
and validation. This is the concrete mechanism that makes "one
troubleshooting engine, not two" an enforced fact rather than just a
diagram.

Two entrypoints are provided:

  - run_troubleshoot_query(): allow-list + retrieval only. Kept from
    Phase 2 so its existing tests and callers keep working unchanged.
  - run_troubleshoot(): the full pipeline — allow-list -> retrieval ->
    Gemini grounding -> citation/safety validation -> TroubleshootResult.
    This is what a later API route should call.
"""

from dataclasses import dataclass
from typing import Optional

from engine.contracts import (
    EvidenceBundle,
    GroundedAnswer,
    Query,
    TroubleshootResult,
    TroubleshootStatus,
)
from engine.grounding.gemini_client import GeminiClient, GeminiGenerationError
from engine.grounding.prompt_builder import build_prompt
from engine.kb_loader import KnowledgeBase
from engine.retrieval.evidence_assembler import retrieve_evidence
from engine.validation.output_validator import validate_output


@dataclass(frozen=True)
class EngineResult:
    status: TroubleshootStatus
    evidence_bundle: Optional[EvidenceBundle]
    message: str


def build_query(
    equipment_category: str,
    manufacturer: str,
    model: str,
    code: Optional[str] = None,
    symptom: Optional[str] = None,
    source: str = "manual",
) -> Query:
    """
    Normalizes raw input fields into a canonical Query.

    Deliberately does NOT validate against the catalog here — "is this a
    well-formed query" and "is this equipment supported" are different
    questions with different failure states, and only the second one
    belongs to run_troubleshoot_query / run_troubleshoot.
    """
    stripped_code = code.strip() if code else ""
    stripped_symptom = symptom.strip() if symptom else ""
    return Query(
        equipment_category=equipment_category.strip(),
        manufacturer=manufacturer.strip(),
        model=model.strip(),
        code=stripped_code or None,
        symptom=stripped_symptom or None,
        source=source,
    )


def _is_supported(kb: KnowledgeBase, equipment_category: str, manufacturer: str, model: str) -> bool:
    """
    Checks the query's equipment identity against the live catalog derived
    from verified records (kb.catalog()) — never against a hardcoded list.
    Matches on canonical model name OR a known alias.
    """
    target_model = model.strip().lower()
    target_category = equipment_category.strip().lower()
    target_manufacturer = manufacturer.strip().lower()

    for entry in kb.catalog():
        if (
            entry.equipment_category.strip().lower() == target_category
            and entry.manufacturer.strip().lower() == target_manufacturer
            and (
                entry.model.strip().lower() == target_model
                or any(alias.strip().lower() == target_model for alias in entry.model_aliases)
            )
        ):
            return True
    return False


def run_troubleshoot_query(
    kb: KnowledgeBase,
    query: Query,
    semantic_matcher=None,
) -> EngineResult:
    """
    Allow-list check -> retrieval only (exact -> scoped semantic). Does
    NOT call Gemini or run validation — VERIFIED_RESULT here means
    "verified evidence was found," not "a fully validated, grounded
    response is ready." Kept from Phase 2 for its existing callers/tests.

    `semantic_matcher` is forwarded to retrieve_evidence() so callers
    (including tests) can inject a fake matcher and avoid requiring
    network access / a downloaded embedding model when the exact-match
    path already covers what's being tested.
    """
    if not _is_supported(kb, query.equipment_category, query.manufacturer, query.model):
        return EngineResult(
            status=TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED,
            evidence_bundle=None,
            message=(
                f"'{query.manufacturer} {query.model}' is not yet a supported "
                f"{query.equipment_category} in the verified knowledge base."
            ),
        )

    retrieval_result = retrieve_evidence(kb, query, semantic_matcher=semantic_matcher)
    return EngineResult(
        status=retrieval_result.status,
        evidence_bundle=retrieval_result.evidence_bundle,
        message=retrieval_result.reason,
    )


def _build_evidence_only_answer(evidence: EvidenceBundle) -> GroundedAnswer:
    """Build a strictly evidence-derived answer when Gemini is unavailable."""
    record = evidence.matched_records[0]
    return GroundedAnswer(
        issue_summary=record.issue_title or record.code,
        meaning_explanation=record.meaning or "Not stated in manual",
        cause_explanations=list(record.possible_causes),
        safe_check_guidance=list(record.safe_user_checks),
        technician_only_guidance=list(record.technician_only_checks),
        next_action=(
            " ".join(record.troubleshooting_steps)
            if record.troubleshooting_steps
            else "Not stated in manual. Contact a qualified technician."
        ),
    )


def run_troubleshoot(
    kb: KnowledgeBase,
    query: Query,
    gemini_client: Optional[GeminiClient] = None,
    semantic_matcher=None,
) -> TroubleshootResult:
    """
    The full P0/P1-shared pipeline:

        allow-list -> retrieval -> Gemini grounding -> validation

    Gemini is only ever reached if retrieval already returned
    VERIFIED_RESULT with a populated EvidenceBundle — an unsupported
    equipment identity or a retrieval miss short-circuits before this
    function ever builds a prompt or constructs a GeminiClient, which is
    the concrete enforcement of "no generation without verified evidence."

    `semantic_matcher` is forwarded through to retrieval, same as in
    run_troubleshoot_query — lets tests exercise the full pipeline without
    requiring a real embedding model / network access.
    """
    retrieval_outcome = run_troubleshoot_query(kb, query, semantic_matcher=semantic_matcher)

    if retrieval_outcome.status != TroubleshootStatus.VERIFIED_RESULT:
        return TroubleshootResult(
            status=retrieval_outcome.status,
            message=retrieval_outcome.message,
            evidence=retrieval_outcome.evidence_bundle,
            grounded_answer=None,
            safety=None,
        )

    evidence = retrieval_outcome.evidence_bundle
    assert evidence is not None  # guaranteed by VERIFIED_RESULT above

    prompt = build_prompt(evidence)
    client = gemini_client or GeminiClient()

    grounded_answer: Optional[GroundedAnswer] = None
    used_evidence_fallback = False
    try:
        grounded_answer = client.generate(prompt)
    except GeminiGenerationError:
        # The manual evidence is already verified and contains all fields
        # needed for a safe structured response. Use it directly rather than
        # turning a missing optional Gemini service into a blank error screen.
        grounded_answer = _build_evidence_only_answer(evidence)
        used_evidence_fallback = True

    validated = validate_output(evidence, grounded_answer)
    message = validated.message
    if used_evidence_fallback and validated.status == TroubleshootStatus.VERIFIED_RESULT:
        message = "Response prepared directly from verified manual evidence; grounded generation was unavailable."

    return TroubleshootResult(
        status=validated.status,
        message=message,
        evidence=evidence,
        grounded_answer=grounded_answer,
        safety=validated.safety,
    )
