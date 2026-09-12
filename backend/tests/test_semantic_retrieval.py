"""
Tests for engine/retrieval/semantic_match.py.

These tests inject a deterministic, network-free stand-in for
SentenceTransformer so the FAISS index-build/search/threshold logic can be
verified without downloading the real all-MiniLM-L6-v2 model weights.

IMPORTANT: this does NOT test the real embedding model's semantic
accuracy (the 4/4 pass result validated in Colab) — it only tests that
SemanticMatcher wires FAISS IndexFlatIP, normalized embeddings, and the
similarity threshold together correctly. Validating the real model's
accuracy requires running with actual network access to download the
model weights, which this sandbox does not have; do that once on a
machine with normal internet access as part of Phase 2 sign-off.
"""

import numpy as np

from engine.contracts import NormalizedRecord, SourceCitation
from engine.retrieval.semantic_match import SemanticMatcher


def _fake_record(record_id: str, issue_title: str, meaning: str, code: str) -> NormalizedRecord:
    return NormalizedRecord(
        record_id=record_id,
        equipment_category="ups",
        manufacturer="Eaton",
        model="5PX1500IRT2UG2",
        model_aliases=[],
        model_family=[],
        manual_title="Test Manual",
        manual_version="TEST-1",
        manual_language="English",
        code=code,
        issue_type="alarm",
        issue_title=issue_title,
        meaning=meaning,
        possible_causes=[],
        troubleshooting_steps=[],
        safe_user_checks=[],
        technician_only_checks=[],
        safety_warning="",
        global_safety_notes=[],
        source=SourceCitation(manual_title="Test Manual"),
        verification_status="verified",
        verification_notes=None,
    )


class _StubEncoder:
    """
    Deterministic, network-free stand-in for SentenceTransformer. Maps a
    small fixed vocabulary of known texts to fixed vectors so the test can
    assert exact ranking/threshold behavior; anything unrecognized maps to
    a vector orthogonal to all the known ones ("clearly unrelated").
    """

    VOCAB = {
        "battery running low while on battery power battery running low on battery power low battery": np.array(
            [1.0, 0.0, 0.0], dtype="float32"
        ),
        "ups running on battery power ups running on battery power battery mode battery mode": np.array(
            [0.9, 0.1, 0.0], dtype="float32"
        ),
        "internal temperature too high internal temperature too high overheating overtemp": np.array(
            [0.0, 0.0, 1.0], dtype="float32"
        ),
        "battery running low on battery power": np.array([1.0, 0.0, 0.0], dtype="float32"),
    }

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        vectors = []
        for text in texts:
            key = text.strip().lower()
            vec = self.VOCAB.get(key, np.array([0.0, 1.0, 0.0], dtype="float32"))
            if normalize_embeddings:
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
            vectors.append(vec)
        return np.vstack(vectors).astype("float32")


def _matcher_with_stub() -> SemanticMatcher:
    matcher = SemanticMatcher()
    matcher._model = _StubEncoder()  # skip real model load entirely
    return matcher


def test_semantic_search_returns_best_match_above_threshold():
    records = [
        _fake_record(
            "r1",
            "Battery running low while on battery power",
            "Battery running low on battery power",
            "Low battery",
        ),
        _fake_record(
            "r2",
            "UPS running on battery power",
            "UPS running on battery power battery mode",
            "Battery mode",
        ),
        _fake_record(
            "r3",
            "Internal temperature too high",
            "Internal temperature too high overheating",
            "Overtemp",
        ),
    ]

    matcher = _matcher_with_stub()
    hits = matcher.search(
        "battery running low on battery power",
        records,
        top_k=3,
        similarity_threshold=0.5,
    )

    assert len(hits) >= 1
    assert hits[0].record.record_id == "r1"
    assert hits[0].score > 0.9


def test_semantic_search_returns_empty_below_threshold():
    records = [
        _fake_record(
            "r3",
            "Internal temperature too high",
            "Internal temperature too high overheating",
            "Overtemp",
        ),
    ]
    matcher = _matcher_with_stub()

    hits = matcher.search(
        "battery running low on battery power",
        records,
        similarity_threshold=0.9,
    )
    assert hits == []


def test_semantic_search_empty_query_returns_empty():
    matcher = _matcher_with_stub()
    records = [_fake_record("r1", "x", "y", "z")]
    assert matcher.search("", records) == []
    assert matcher.search("   ", records) == []


def test_semantic_search_empty_candidates_returns_empty():
    matcher = _matcher_with_stub()
    assert matcher.search("battery running low", []) == []


def test_semantic_search_never_raises_on_no_hits():
    """A no-hit result must be an empty list, not an exception — the
    retrieval pipeline depends on this to produce 'issue_not_verified'."""
    records = [_fake_record("r1", "Unrelated", "Totally unrelated meaning", "X")]
    matcher = _matcher_with_stub()
    hits = matcher.search("battery running low on battery power", records, similarity_threshold=0.99)
    assert hits == []