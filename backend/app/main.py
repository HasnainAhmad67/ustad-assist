"""
FastAPI application entrypoint.

Phase 1 scope: app setup, CORS, KB startup loading, catalog route, and a
health check. No troubleshooting, vision, or Gemini routes are registered
yet — those are added in later phases.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import catalog, troubleshoot, vision
from app.schemas import HealthResponse
from config.settings import get_settings
from engine.kb_loader import get_knowledge_base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Load and normalize the knowledge base once, at process start — not
    per-request. Failing fast here (rather than on the first API call) is
    intentional: a missing or malformed dataset should surface immediately
    when the backend starts, not silently on a user's first request.
    """
    get_knowledge_base()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Ustad Assist backend API — safety-first troubleshooting copilot "
        "for Solar Inverters and UPS systems. Phase 4: full P0 "
        "troubleshoot workflow (retrieval -> Gemini grounding -> "
        "citation/safety validation), served over HTTP."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(troubleshoot.router)
app.include_router(vision.router)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Basic liveness check plus a sanity check that the KB loaded correctly."""
    kb = get_knowledge_base()
    stats = kb.stats()
    return HealthResponse(
        status="ok",
        environment=get_settings().environment,
        dataset_name=stats["dataset_name"],
        dataset_version=stats["dataset_version"],
        total_records=stats["total_records"],
        verified_records=stats["verified_records"],
    )