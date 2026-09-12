"""
Query construction and the engine's single public entrypoint.

This module is called identically whether the raw input came from a typed
P0 form or (in a later phase) a confirmed P1 image detection — both
produce the same kind of raw fields, and only this one path evaluates the
equipment allow-list and then retrieval. This is the concrete mechanism
that makes "one troubleshooting engine, not two" an enforced fact rather
than just a diagram.

Gemini grounding, citation validation, and safety validation are NOT
called here yet — reserved for later phases. In this phase,
TroubleshootStatus.VERIFIED_RESULT means "verified evidence was found for
this query," not "a fully validated, grounded response is ready."
"""

from dataclasses import dataclass
from typing import Optional

from engine.contracts import EvidenceBundle, Query, TroubleshootStatus
from engine.kb_loader import KnowledgeBase
from engine.retrieval.evidence_assembler import retrieve_evidence


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
    belongs to run_troubleshoot_query.
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


def run_troubleshoot_query(kb: KnowledgeBase, query: Query) -> EngineResult:
    """
    The engine's single public entrypoint. Sequence:

        allow-list check -> retrieval (exact -> scoped semantic) -> result

    An unsupported equipment identity short-circuits before retrieval ever
    runs, exactly as required by the architecture's P0 flow.
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

    retrieval_result = retrieve_evidence(kb, query)
    return EngineResult(
        status=retrieval_result.status,
        evidence_bundle=retrieval_result.evidence_bundle,
        message=retrieval_result.reason,
    )