"""
Tests for engine/retrieval/evidence_assembler.py — the ordered pipeline
that combines exact and semantic retrieval into a single result, scoped
correctly at every stage.

Semantic retrieval is exercised here via a fake SemanticMatcher (no real
model/network needed) so these tests focus purely on the orchestration
logic: which stage fires, in what order, and what result each outcome
produces.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List

from engine.contracts import Query, TroubleshootStatus
from engine.kb_loader import KnowledgeBase
from engine.retrieval.evidence_assembler import retrieve_evidence
from engine.retrieval.semantic_match import SemanticHit

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


@dataclass
class _FakeSemanticMatcher:
    """Returns a fixed, pre-canned list of hits regardless of input —
    used to test evidence_assembler's orchestration in isolation from the
    real embedding/FAISS logic (already tested in test_semantic_retrieval.py)."""

    hits_to_return: List[SemanticHit]

    def search(self, query_text, candidates, top_k=3, similarity_threshold=0.5):
        return self.hits_to_return


def test_exact_hit_short_circuits_before_semantic_is_used():
    kb = _kb()
    query = Query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )
    # A semantic matcher that would raise if called, proving stage (1)
    # short-circuits stage (3) entirely on an exact hit.
    class _ExplodingMatcher:
        def search(self, *args, **kwargs):
            raise AssertionError("Semantic search must not run when an exact match exists")

    result = retrieve_evidence(kb, query, semantic_matcher=_ExplodingMatcher())

    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    assert result.evidence_bundle is not None
    assert result.evidence_bundle.retrieval_method == "exact"
    assert result.evidence_bundle.matched_records[0].code == "201"


def test_semantic_fallback_used_when_no_exact_code_given():
    kb = _kb()
    records = kb.verified_records()
    eaton_battery_mode = next(r for r in records if r.manufacturer == "Eaton" and r.code == "Battery mode")

    query = Query(
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code=None,
        symptom="running on battery after a power cut",
    )
    fake_matcher = _FakeSemanticMatcher(hits_to_return=[SemanticHit(record=eaton_battery_mode, score=0.87)])

    result = retrieve_evidence(kb, query, semantic_matcher=fake_matcher)

    assert result.status == TroubleshootStatus.VERIFIED_RESULT
    assert result.evidence_bundle.retrieval_method == "semantic"
    assert result.evidence_bundle.matched_records[0].record_id == eaton_battery_mode.record_id


def test_no_records_for_model_returns_issue_not_verified_without_calling_semantic():
    kb = _kb()
    query = Query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MODEL THAT DOES NOT EXIST",
        code="201",
    )

    class _ExplodingMatcher:
        def search(self, *args, **kwargs):
            raise AssertionError("Semantic search must not run when the model has zero records")

    result = retrieve_evidence(kb, query, semantic_matcher=_ExplodingMatcher())

    assert result.status == TroubleshootStatus.ISSUE_NOT_VERIFIED
    assert result.evidence_bundle is None


def test_no_exact_and_no_semantic_hit_returns_issue_not_verified():
    kb = _kb()
    query = Query(
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        code="Nonexistent Code",
        symptom="something not in the manual at all",
    )
    fake_matcher = _FakeSemanticMatcher(hits_to_return=[])  # nothing clears the threshold

    result = retrieve_evidence(kb, query, semantic_matcher=fake_matcher)

    assert result.status == TroubleshootStatus.ISSUE_NOT_VERIFIED
    assert result.evidence_bundle is None