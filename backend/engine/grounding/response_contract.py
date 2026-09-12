"""
The structured shape Gemini's output must fill, and the strict rules for
what it's allowed to contain.

engine/contracts.py::GroundedAnswer is the actual dataclass. This module
owns two things: the JSON schema description given to Gemini as part of
the prompt, and strict parsing/validation of Gemini's raw text response
into a GroundedAnswer.

Gemini is allowed to fill in: issue_summary, meaning_explanation,
cause_explanations, safe_check_guidance, technician_only_guidance,
next_action.

Gemini is NEVER allowed to originate (and this schema provides no field
for it): manual name, document number, page number, official URL,
verification status, or any safety escalation decision. Those come from
EvidenceBundle and engine/safety/ only, never from parsed model output.
"""

import json
from typing import Any, Dict, List

from engine.contracts import GroundedAnswer

RESPONSE_JSON_SCHEMA_DESCRIPTION = """
Respond with ONLY a single JSON object (no markdown fences, no commentary
before or after it) matching exactly this shape:

{
  "issue_summary": "<one sentence, plain language, restating the confirmed issue>",
  "meaning_explanation": "<plain-language explanation of what the evidence's documented meaning means for the user>",
  "cause_explanations": ["<cause 1 explained in plain language>", "..."],
  "safe_check_guidance": ["<plain-language guidance for each documented safe user check, or [] if none were provided>"],
  "technician_only_guidance": ["<plain-language note for each documented technician-only check, or [] if none were provided>"],
  "next_action": "<one short, concrete sentence on what the user should do next>"
}

Rules:
- Do NOT invent any cause, check, step, manual name, page number, or
  safety instruction that is not present in the evidence given to you.
- Do NOT include a manual name, document number, page number, or source
  URL anywhere in your response — that is handled separately by the
  system, not by you.
- If the evidence's possible causes, safe user checks, or technician-only
  checks are empty, return an empty list for that field — do not fill it
  in with your own suggestions.
- If you are not confident an explanation is fully supported by the
  evidence given, keep your wording close to the evidence rather than
  adding detail of your own.
""".strip()


class ResponseContractError(ValueError):
    """
    Raised when Gemini's raw output cannot be parsed into a valid
    GroundedAnswer. The caller must treat this as a generation failure —
    never patch in defaults for a missing required field.
    """


def _as_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _strip_markdown_fence(raw_text: str) -> str:
    cleaned = raw_text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    # The prompt forbids markdown fences, but strip one defensively if the
    # model adds one anyway, rather than failing on an otherwise-valid response.
    cleaned = cleaned.strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:]
    return cleaned.strip()


def parse_grounded_answer(raw_text: str) -> GroundedAnswer:
    """
    Parses and validates Gemini's raw text output into a GroundedAnswer.
    Raises ResponseContractError on any structural problem — invalid JSON,
    or a missing/empty required field — rather than returning a partially
    invented object.
    """
    cleaned = _strip_markdown_fence(raw_text)

    try:
        data: Dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ResponseContractError(f"Gemini response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ResponseContractError("Gemini response JSON was not an object.")

    required_string_fields = ["issue_summary", "meaning_explanation", "next_action"]
    for field_name in required_string_fields:
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ResponseContractError(f"Missing or empty required field: '{field_name}'")

    return GroundedAnswer(
        issue_summary=data["issue_summary"].strip(),
        meaning_explanation=data["meaning_explanation"].strip(),
        cause_explanations=_as_str_list(data.get("cause_explanations")),
        safe_check_guidance=_as_str_list(data.get("safe_check_guidance")),
        technician_only_guidance=_as_str_list(data.get("technician_only_guidance")),
        next_action=data["next_action"].strip(),
    )