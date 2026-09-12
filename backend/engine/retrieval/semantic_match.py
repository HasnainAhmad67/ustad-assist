"""
Semantic fallback retrieval — ports the validated Google Colab RAG setup
as-is. See architecture doc v2 section 8.1 for the frozen parameter table
this file implements:

    embedding model:    sentence-transformers "all-MiniLM-L6-v2"
    encoding options:   convert_to_numpy=True, normalize_embeddings=True
    vector index:       FAISS IndexFlatIP
    similarity:         inner product over normalized vectors
                         (cosine-equivalent)

Do NOT change the embedding model, encoding flags, or index type without a
concrete technical reason — this exact combination was already validated
(4/4 pass) before being ported here.

This module is only ever queried against a candidate pool that has already
been narrowed to one manufacturer+model by
engine/retrieval/exact_match.py::filter_by_equipment_identity — never
against the full verified record set.
"""

from dataclasses import dataclass
from typing import List

import numpy as np

from config.settings import get_settings
from engine.contracts import NormalizedRecord

# Minimum cosine-equivalent similarity for a semantic hit to count as
# evidence rather than noise. If your Colab notebook used a specific
# explicit cutoff to get the validated 4/4 pass result, update this
# constant to match that value exactly so behavior stays identical.
DEFAULT_SIMILARITY_THRESHOLD = 0.5

DEFAULT_TOP_K = 3


def _build_search_text(record: NormalizedRecord) -> str:
    """
    The text a record is embedded from for semantic search. Deliberately
    limited to issue_title + meaning + code — the fields closest to what a
    technician would type as a symptom — rather than the full record
    (troubleshooting steps, safety text, etc. would dilute the match and
    were not part of what was embedded during Colab validation).
    """
    parts = [record.issue_title, record.meaning, record.code]
    return " ".join(part for part in parts if part).strip()


@dataclass(frozen=True)
class SemanticHit:
    record: NormalizedRecord
    score: float  # cosine-equivalent similarity (normalized inner product)


class SemanticMatcher:
    """
    Wraps SentenceTransformer("all-MiniLM-L6-v2") + FAISS IndexFlatIP.

    The model is lazy-loaded on first use (not at import time or
    construction time) so that importing this module — or constructing a
    SemanticMatcher — never requires network access or the sentence-
    transformers/faiss packages to be installed unless search() is
    actually called. This keeps kb_loader/exact_match/catalog usable in
    environments that haven't installed the RAG dependencies yet.
    """

    def __init__(self, model_name: str | None = None):
        self._model_name = model_name or get_settings().embedding_model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Exactly the Colab-validated encoding call — same flags, same order."""
        model = self._get_model()
        return model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    def search(
        self,
        query_text: str,
        candidates: List[NormalizedRecord],
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> List[SemanticHit]:
        """
        Builds a fresh FAISS IndexFlatIP over `candidates` only, embeds
        `query_text` with the same model/flags, and returns hits at or
        above `similarity_threshold`, best first.

        Returns an empty list — never an exception — when nothing clears
        the threshold or when inputs are empty. An empty result is what
        the retrieval pipeline (evidence_assembler.py) turns into
        "issue_not_verified."
        """
        if not query_text or not query_text.strip() or not candidates:
            return []

        import faiss  # imported lazily so importing this module doesn't require faiss

        texts = [_build_search_text(candidate) for candidate in candidates]
        document_embeddings = self._encode(texts)

        dimension = document_embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(document_embeddings)

        query_embedding = self._encode([query_text])
        k = min(top_k, len(candidates))
        scores, indices = index.search(query_embedding, k)

        hits: List[SemanticHit] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            if float(score) >= similarity_threshold:
                hits.append(SemanticHit(record=candidates[idx], score=float(score)))

        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits