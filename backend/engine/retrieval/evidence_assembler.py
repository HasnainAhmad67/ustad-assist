"""
Evidence assembly — orchestrates the ordered, gated retrieval pipeline
from architecture doc v2 section 8.3:

  (1) exact retrieval first
  (2) exact manufacturer/model filtering before semantic fallback
  (3) semantic retrieval fallback, scoped to (2)'s subset only
  (4) verified-record-only evidence — enforced upstream by
      KnowledgeBase.verified_records(), not re-checked ad hoc here
  (5) EvidenceBundle assembly
  (6) no generation without verified evidence — this module NEVER calls
      Gemini (which doesn't exist yet in this phase); it only ever
      returns an EvidenceBundle or a "not verified" result. Reaching a
      populated EvidenceBundle is the only way a later phase's grounding
      step becomes reachable at all.
"""

from dataclasses import dataclass
from typing import Optional

from engine.contracts import EvidenceBundle, Query, TroubleshootStatus
from engine.kb_loader import KnowledgeBase
from engine.retrieval.exact_match import filter_by_equipment_identity, find_exact_match
from engine.retrieval.semantic_match import SemanticMatcher


@dataclass(frozen=True)
class RetrievalResult:
    """
    What retrieval hands back to its caller (engine/query_builder.py).

    `status` is one of:
      - TroubleshootStatus.VERIFIED_RESULT    -> evidence_bundle is populated
      - TroubleshootStatus.ISSUE_NOT_VERIFIED -> evidence_bundle is None

    TroubleshootStatus.EQUIPMENT_NOT_SUPPORTED is decided one layer up, in
    query_builder.py, before retrieval ever runs — this module assumes the
    equipment identity has already been confirmed supported.
    """

    status: TroubleshootStatus
    evidence_bundle: Optional[EvidenceBundle]
    reason: str


def retrieve_evidence(
    kb: KnowledgeBase,
    query: Query,
    semantic_matcher: Optional[SemanticMatcher] = None,
) -> RetrievalResult:
    verified_records = kb.verified_records()  # stage (4)

    # Stage (1): exact retrieval first — attempted whenever a code was given.
    if query.code:
        exact_hit = find_exact_match(
            verified_records,
            query.equipment_category,
            query.manufacturer,
            query.model,
            query.code,
        )
        if exact_hit is not None:
            bundle = EvidenceBundle(
                query=query,
                matched_records=[exact_hit],
                retrieval_method="exact",
            )
            return RetrievalResult(
                status=TroubleshootStatus.VERIFIED_RESULT,
                evidence_bundle=bundle,
                reason="Exact code match found within the confirmed manufacturer/model.",
            )

    # Stage (2): narrow to the confirmed manufacturer+model BEFORE any
    # semantic search — the FAISS index is only ever built over this
    # subset, never the full verified record set.
    model_scoped_candidates = filter_by_equipment_identity(
        verified_records, query.equipment_category, query.manufacturer, query.model
    )

    if not model_scoped_candidates:
        return RetrievalResult(
            status=TroubleshootStatus.ISSUE_NOT_VERIFIED,
            evidence_bundle=None,
            reason="No verified records exist for this manufacturer/model at all.",
        )

    # Stage (3): semantic fallback, scoped to stage (2)'s subset only.
    search_text = query.code or query.symptom or ""
    matcher = semantic_matcher or SemanticMatcher()
    hits = matcher.search(search_text, model_scoped_candidates)

    if not hits:
        return RetrievalResult(
            status=TroubleshootStatus.ISSUE_NOT_VERIFIED,
            evidence_bundle=None,
            reason=(
                "Model is supported, but neither an exact code match nor a "
                "semantic match above threshold was found for this issue."
            ),
        )

    # Stage (5): EvidenceBundle assembly. Only the top semantic hit is used
    # as evidence — a multi-record bundle is a possible future refinement,
    # not required by the validated Colab behavior (which tested single
    # best-match retrieval).
    top_hit = hits[0]
    bundle = EvidenceBundle(
        query=query,
        matched_records=[top_hit.record],
        retrieval_method="semantic",
    )
    return RetrievalResult(
        status=TroubleshootStatus.VERIFIED_RESULT,
        evidence_bundle=bundle,
        reason=f"Semantic match found (similarity={top_hit.score:.3f}).",
    )