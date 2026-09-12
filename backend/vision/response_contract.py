"""
The structured shape Gemini Vision's output must fill, and strict parsing
of its response into VisionCandidate objects.

Gemini Vision is allowed to: read the equipment category/manufacturer/
model information printed on a nameplate/label, and any error code or
alarm text visible on a display.

Gemini Vision is NEVER allowed to: diagnose the problem, suggest a cause,
recommend a fix, or invent a manufacturer/model that isn't legible in the
photo. This schema has no field for any of that — it is structurally
impossible for parsed output to carry a diagnosis, by construction, not
just by prompt instruction.
"""

import json
from typing import Any, Dict, List

from vision.contracts import VisionCandidate

RESPONSE_JSON_SCHEMA_DESCRIPTION = """
Respond with ONLY a single JSON object (no markdown fences, no commentary
before or after it) matching exactly this shape:

{
  "candidates": [
    {
      "equipment_category": "solar_inverter" or "ups" or null,
      "manufacturer": "<manufacturer name as printed, or null if illegible>",
      "model": "<model name/number as printed, or null if illegible>",
      "code": "<any error code, alarm text, or fault code visible on a display or label, or null>",
      "confidence": <a number between 0.0 and 1.0>,
      "raw_model_text": "<the literal nameplate/label text you read for the model, or null>"
    }
  ]
}

Rules:
- Only report what is actually visible and legible in the image. If a
  field is not visible or you are not confident, use null for that field
  rather than guessing.
- Do NOT diagnose the problem, suggest a cause, or recommend any fix — you
  are only reading labels and displays, not troubleshooting.
- If more than one plausible reading is visible (e.g. a partially
  obscured label with two possible model numbers), return multiple
  candidate objects rather than picking one arbitrarily.
- If nothing legible is visible at all, return {"candidates": []}.
""".strip()


class VisionResponseContractError(ValueError):
    """
    Raised when Gemini Vision's raw output cannot be parsed into valid
    candidates. The caller must treat this as an extraction failure, never
    patch in a guessed candidate.
    """


def _clamp_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _strip_markdown_fence(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    cleaned = cleaned.strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:]
    return cleaned.strip()


def parse_vision_candidates(raw_text: str) -> List[VisionCandidate]:
    cleaned = _strip_markdown_fence(raw_text)

    try:
        data: Dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise VisionResponseContractError(f"Vision response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict) or "candidates" not in data:
        raise VisionResponseContractError("Vision response JSON is missing the 'candidates' field.")

    raw_candidates = data["candidates"]
    if not isinstance(raw_candidates, list):
        raise VisionResponseContractError("'candidates' must be a list.")

    candidates: List[VisionCandidate] = []
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        candidates.append(
            VisionCandidate(
                equipment_category=item.get("equipment_category") or None,
                manufacturer=item.get("manufacturer") or None,
                model=item.get("model") or None,
                code=item.get("code") or None,
                confidence=_clamp_confidence(item.get("confidence")),
                raw_model_text=item.get("raw_model_text") or None,
            )
        )
    return candidates