"""Lightweight semantic fallback for serverless deployments.

Exact code retrieval remains the primary and highest-confidence path. When an
exact code is not found, this module performs deterministic token overlap over
records that were already narrowed to the confirmed manufacturer and model.
It intentionally avoids sentence-transformers, FAISS, NumPy, and PyTorch so
this backend can run within Vercel's function-size limit.
"""

import re
from dataclasses import dataclass
from typing import List

from engine.contracts import NormalizedRecord

DEFAULT_SIMILARITY_THRESHOLD = 0.5
DEFAULT_TOP_K = 3
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall((value or "").lower())
        if len(token) > 1
    }


def _build_search_text(record: NormalizedRecord) -> str:
    parts = [
        record.issue_title,
        record.meaning,
        record.code,
        record.issue_type or "",
        " ".join(record.possible_causes),
    ]
    return " ".join(part for part in parts if part).strip()


@dataclass(frozen=True)
class SemanticHit:
    record: NormalizedRecord
    score: float


class SemanticMatcher:
    """Deterministic keyword fallback scoped to one confirmed model."""

    def __init__(self, model_name: str | None = None):
        # Kept for API compatibility with callers that pass a model name.
        self._model_name = model_name

    def search(
        self,
        query_text: str,
        candidates: List[NormalizedRecord],
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> List[SemanticHit]:
        query_tokens = _tokens(query_text)
        if not query_tokens or not candidates:
            return []

        hits: List[SemanticHit] = []
        for record in candidates:
            record_tokens = _tokens(_build_search_text(record))
            if not record_tokens:
                continue

            overlap = query_tokens.intersection(record_tokens)
            if not overlap:
                continue

            # Query coverage rewards records that explain most of the words
            # supplied by the technician. A small precision bonus prevents a
            # very broad record from winning on one generic word.
            coverage = len(overlap) / len(query_tokens)
            precision = len(overlap) / len(record_tokens)
            score = min(1.0, (coverage * 0.85) + (precision * 0.15))

            if score >= similarity_threshold:
                hits.append(SemanticHit(record=record, score=score))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[: min(top_k, len(hits))]
