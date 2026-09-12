"""
GET /api/catalog

Returns the equipment categories, manufacturers, and exact models the
system currently supports — derived live from the verified knowledge base
(engine/kb_loader.py::KnowledgeBase.catalog()), never from a hardcoded
list. This is what the frontend's input-form dropdowns are populated from,
so an unsupported model can never appear as a selectable option.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from fastapi import APIRouter, Depends

from app.deps import get_kb_dep
from app.schemas import (
    CatalogCategoryOut,
    CatalogManufacturerOut,
    CatalogModelOut,
    CatalogResponse,
)
from engine.contracts import CatalogModel
from engine.kb_loader import KnowledgeBase

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog(kb: KnowledgeBase = Depends(get_kb_dep)) -> CatalogResponse:
    catalog_models: List[CatalogModel] = kb.catalog()

    # Group flat CatalogModel entries into category -> manufacturer -> [models]
    grouped: Dict[str, Dict[str, List[CatalogModel]]] = defaultdict(lambda: defaultdict(list))
    for item in catalog_models:
        grouped[item.equipment_category][item.manufacturer].append(item)

    categories_out: List[CatalogCategoryOut] = []
    for equipment_category in sorted(grouped.keys()):
        manufacturers_out: List[CatalogManufacturerOut] = []
        manufacturers = grouped[equipment_category]
        for manufacturer in sorted(manufacturers.keys()):
            models_out = [
                CatalogModelOut(model=m.model, model_aliases=m.model_aliases)
                for m in sorted(manufacturers[manufacturer], key=lambda m: m.model)
            ]
            manufacturers_out.append(
                CatalogManufacturerOut(manufacturer=manufacturer, models=models_out)
            )
        categories_out.append(
            CatalogCategoryOut(
                equipment_category=equipment_category,
                manufacturers=manufacturers_out,
            )
        )

    return CatalogResponse(
        categories=categories_out,
        total_supported_models=len(catalog_models),
    )