"""
POST /api/troubleshoot

The single workflow endpoint for both P0 (typed input) and, once vision
exists, confirmed P1 image input — both produce the same request shape and
are handled identically here. All "is this equipment supported" and "is
there verified evidence" logic lives inside the engine; this route is a
thin HTTP adapter, not a place for business logic.
"""

from fastapi import APIRouter, Depends

from app.deps import get_gemini_client_dep, get_kb_dep
from app.mappers import to_troubleshoot_response
from app.schemas import TroubleshootRequest, TroubleshootResponse
from engine.grounding.gemini_client import GeminiClient
from engine.kb_loader import KnowledgeBase
from engine.query_builder import build_query, run_troubleshoot

router = APIRouter(prefix="/api", tags=["troubleshoot"])


@router.post("/troubleshoot", response_model=TroubleshootResponse)
def troubleshoot(
    request: TroubleshootRequest,
    kb: KnowledgeBase = Depends(get_kb_dep),
    gemini_client: GeminiClient = Depends(get_gemini_client_dep),
) -> TroubleshootResponse:
    query = build_query(
        equipment_category=request.equipment_category,
        manufacturer=request.manufacturer,
        model=request.model,
        code=request.code,
        symptom=request.symptom,
        source=request.source,
    )
    result = run_troubleshoot(kb, query, gemini_client=gemini_client)
    return to_troubleshoot_response(result)