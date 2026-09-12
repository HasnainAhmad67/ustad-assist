"""
Validates and normalizes a client-confirmed (or edited) vision detection
into the same canonical Query shape engine/query_builder.py produces for
P0 typed input.

The actual confirm/edit UI interaction lives in the frontend (a later
phase, out of scope for the backend) — this module is the server-side
checkpoint that runs before a confirmed image-derived identity is allowed
into the shared troubleshooting engine. It does not trust the client's
confirmed payload blindly: required-field validation happens here again,
not just in the UI.
"""

from typing import Optional

from engine.contracts import Query
from engine.query_builder import build_query


def build_confirmed_query(
    equipment_category: Optional[str],
    manufacturer: Optional[str],
    model: Optional[str],
    code: Optional[str] = None,
    symptom: Optional[str] = None,
) -> Query:
    """
    Raises ValueError if a required identity field is missing or blank
    after confirmation. The frontend's confirm/edit screen should already
    prevent this, but it is checked again here rather than assumed —
    matching the general principle that the backend never trusts
    client-side validation alone.
    """
    missing = [
        name
        for name, value in (
            ("equipment_category", equipment_category),
            ("manufacturer", manufacturer),
            ("model", model),
        )
        if not value or not value.strip()
    ]
    if missing:
        raise ValueError(
            f"Confirmed vision input is missing required field(s): {', '.join(missing)}"
        )

    return build_query(
        equipment_category=equipment_category,
        manufacturer=manufacturer,
        model=model,
        code=code,
        symptom=symptom,
        source="image",
    )