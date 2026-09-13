"""
Deterministic exact-match retrieval.

Stage (1) "exact retrieval first" and stage (2) "exact manufacturer/model
filtering before semantic fallback" from architecture doc v2 section 8.3
both live here, since they are the same underlying filter operation at two
levels of specificity: the first also constrains by `code`, the second
does not (it produces the candidate pool semantic fallback is allowed to
search within).

No embeddings, no scoring, no fuzzy matching happen anywhere in this
module. Everything here is a plain, deterministic comparison — which is
what makes it unit-testable without any ML dependency.
"""

import re
from typing import List, Optional

from engine.contracts import NormalizedRecord


def _model_matches(record: NormalizedRecord, model: str) -> bool:
    """
    A query's `model` value matches a record if it equals the record's
    canonical model name OR one of its known aliases (e.g. a user or a
    dropdown might use "MIN 3000TL-X" while the canonical name is
    "MIN 3000 TL-X"). Comparison is case-insensitive and whitespace-
    trimmed, but still exact — never a partial/fuzzy match.
    """
    target = model.strip().lower()
    if record.model.strip().lower() == target:
        return True
    return any(alias.strip().lower() == target for alias in record.model_aliases)


def filter_by_equipment_identity(
    records: List[NormalizedRecord],
    equipment_category: str,
    manufacturer: str,
    model: str,
) -> List[NormalizedRecord]:
    """
    Stage (2): narrows `records` down to those matching
    category + manufacturer + exact model only — `code` is ignored here.

    This is the ONLY function that is allowed to hand a candidate pool to
    semantic retrieval. Semantic search must never be run against the full
    verified record set irrespective of equipment identity.
    """
    category_key = equipment_category.strip().lower()
    manufacturer_key = manufacturer.strip().lower()
    return [
        record
        for record in records
        if record.equipment_category.strip().lower() == category_key
        and record.manufacturer.strip().lower() == manufacturer_key
        and _model_matches(record, model)
    ]


def find_exact_match(
    records: List[NormalizedRecord],
    equipment_category: str,
    manufacturer: str,
    model: str,
    code: str,
    symptom: Optional[str] = None,
) -> Optional[NormalizedRecord]:
    """
    Stage (1): category -> manufacturer -> exact model -> exact code.
    Deterministic. If a code is used by multiple manual rows, a symptom is
    required to disambiguate them; this prevents returning the first row and
    silently showing the wrong diagnosis. Never falls back to semantic
    matching itself — that is a separate later stage.
    """
    if not code or not code.strip():
        return None

    code_key = code.strip().lower()
    candidates = filter_by_equipment_identity(records, equipment_category, manufacturer, model)

    exact_code_candidates = [
        record for record in candidates if record.code.strip().lower() == code_key
    ]
    if not exact_code_candidates:
        return None
    if len(exact_code_candidates) == 1:
        return exact_code_candidates[0]

    query_tokens = _tokens(symptom or "")
    if not query_tokens:
        return None
    ranked = sorted(
        (
            (_symptom_score(record, query_tokens), index, record)
            for index, record in enumerate(exact_code_candidates)
        ),
        key=lambda item: (item[0], -item[1]),
        reverse=True,
    )
    best_score, _, best_record = ranked[0]
    if best_score <= 0:
        return None
    if len(ranked) > 1 and best_score == ranked[1][0]:
        return None
    return best_record


def _tokens(value: str) -> set[str]:
    """Return simple alphanumeric tokens for deterministic symptom matching."""
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if len(token) > 1
    }


def _symptom_score(record: NormalizedRecord, query_tokens: set[str]) -> int:
    searchable = " ".join(
        [record.issue_title, record.meaning, " ".join(record.possible_causes)]
    )
    return len(query_tokens & _tokens(searchable))
