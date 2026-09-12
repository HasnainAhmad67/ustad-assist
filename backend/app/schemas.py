"""
Pydantic models that define the public API contract.

This file is the single source of truth for the API's request/response
shapes. The frontend's TypeScript types (frontend/src/types/api.ts, built
in a later phase) should mirror this file — not the other way around.

Phase 1 only needs the catalog and health shapes. Troubleshoot/vision
request/response schemas are intentionally not added yet; they belong to
the phases that implement retrieval, grounding, and vision.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CatalogModelOut(BaseModel):
    """One supported exact model within a manufacturer."""

    # Pydantic v2 reserves the "model_" field-name prefix for its own
    # methods (model_dump, etc.) and warns on fields like `model_aliases`.
    # These are legitimate domain field names, not accidental collisions,
    # so the protected-namespace check is disabled for this schema only.
    model_config = ConfigDict(protected_namespaces=())

    model: str
    model_aliases: List[str] = Field(default_factory=list)


class CatalogManufacturerOut(BaseModel):
    """One supported manufacturer within an equipment category."""

    manufacturer: str
    models: List[CatalogModelOut]


class CatalogCategoryOut(BaseModel):
    """One supported equipment category."""

    equipment_category: str
    manufacturers: List[CatalogManufacturerOut]


class CatalogResponse(BaseModel):
    """
    Response for GET /api/catalog. Derived live from the verified
    knowledge base — never a hardcoded list — so the frontend's dropdowns
    can never drift out of sync with what's actually supported.
    """

    categories: List[CatalogCategoryOut]
    total_supported_models: int


class HealthResponse(BaseModel):
    """Response for GET /health — basic liveness + dataset sanity check."""

    status: str
    environment: str
    dataset_name: Optional[str] = None
    dataset_version: Optional[str] = None
    total_records: int
    verified_records: int