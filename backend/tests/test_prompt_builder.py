"""Tests for engine/grounding/prompt_builder.py."""

from pathlib import Path

import pytest

from engine.contracts import EvidenceBundle, Query
from engine.grounding.prompt_builder import build_prompt
from engine.kb_loader import KnowledgeBase
from engine.retrieval.exact_match import find_exact_match

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "verified_records.json"


def _kb() -> KnowledgeBase:
    kb = KnowledgeBase(DATA_PATH)
    kb.load()
    return kb


def test_prompt_contains_only_the_matched_records_evidence():
    kb = _kb()
    record = find_exact_match(
        kb.verified_records(), "solar_inverter", "Growatt", "MIN 3000 TL-X", "201"
    )
    assert record is not None

    query = Query(equipment_category="solar_inverter", manufacturer="Growatt", model="MIN 3000 TL-X", code="201")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    prompt = build_prompt(bundle)

    assert "Residual I High" in prompt
    assert "Leakage current too high" in prompt
    assert "201" in prompt
    # No other manufacturer's data should ever leak into a single-record prompt.
    assert "Eaton" not in prompt
    assert "Battery mode" not in prompt


def test_prompt_forbids_inventing_citation_fields():
    kb = _kb()
    record = find_exact_match(
        kb.verified_records(), "ups", "Eaton", "5PX1500IRT2UG2", "Battery mode"
    )
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="Battery mode")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    prompt = build_prompt(bundle)

    assert "Do NOT include a manual name, document number, page number" in prompt
    # The actual page number/manual title must not appear in the prompt's
    # evidence block either, since Gemini has no legitimate use for them.
    assert "614-40094-00" not in prompt
    assert "page 35" not in prompt.lower()


def test_empty_possible_causes_are_labeled_not_stated():
    kb = _kb()
    record = find_exact_match(
        kb.verified_records(), "solar_inverter", "Growatt", "MIN 3000 TL-X", "201"
    )
    query = Query(equipment_category="solar_inverter", manufacturer="Growatt", model="MIN 3000 TL-X", code="201")
    bundle = EvidenceBundle(query=query, matched_records=[record], retrieval_method="exact")

    prompt = build_prompt(bundle)
    assert "the manual does not state a cause" in prompt


def test_raises_on_empty_evidence_bundle():
    query = Query(equipment_category="ups", manufacturer="Eaton", model="5PX1500IRT2UG2", code="X")
    empty_bundle = EvidenceBundle(query=query, matched_records=[], retrieval_method=None)
    with pytest.raises(ValueError):
        build_prompt(empty_bundle)