"""
Gemini Vision/OCR call — produces structured detection CANDIDATES only.

This module never calls the troubleshooting engine and never returns
troubleshooting content. Vision is explicitly not a knowledge source:
it only reads what's visible in the photo.

Confirmed candidates re-enter the system through POST /api/troubleshoot,
exactly like P0 typed input — see vision/confirmation.py.

The actual network call is isolated behind an injectable `call_fn`, so
this module can be unit-tested without network access or a real API key.
"""

from typing import Callable, Optional

from config.settings import get_settings
from vision.contracts import VisionExtractionResult
from vision.response_contract import (
    RESPONSE_JSON_SCHEMA_DESCRIPTION,
    VisionResponseContractError,
    parse_vision_candidates,
)


# Gemini model used for vision/image understanding.
DEFAULT_VISION_MODEL_NAME = "gemini-3.6-flash"


# (api_key, model_name, image_bytes, mime_type) -> raw_text
VisionCallFn = Callable[[str, str, bytes, str], str]


_PROMPT = f"""
You are reading a photograph of a Solar Inverter or UPS nameplate, label,
or display screen.

Your ONLY task is to identify information that is visibly legible in the
image.

Do NOT troubleshoot the equipment.
Do NOT provide repair instructions.
Do NOT provide causes, solutions, or recommendations.
Do NOT invent missing information.

Only return structured detection candidates based on text that can actually
be seen in the image.

{RESPONSE_JSON_SCHEMA_DESCRIPTION}
""".strip()


class VisionExtractionError(Exception):
    """
    Uniform failure type for any Vision call/parse problem:
    missing API key, network/API error, or a response that fails
    schema validation.
    """


class VisionExtractor:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_VISION_MODEL_NAME,
        call_fn: Optional[VisionCallFn] = None,
    ):
        settings = get_settings()

        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name
        self._call_fn: VisionCallFn = call_fn or _default_vision_call_fn

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
    ) -> VisionExtractionResult:

        if not self._api_key:
            raise VisionExtractionError(
                "GEMINI_API_KEY is not configured. Set it in the environment "
                "before requesting vision extraction."
            )

        try:
            raw_text = self._call_fn(
                self._api_key,
                self._model_name,
                image_bytes,
                mime_type,
            )

        except Exception as exc:  # noqa: BLE001
            raise VisionExtractionError(
                f"Vision API call failed: {exc}"
            ) from exc

        try:
            candidates = parse_vision_candidates(raw_text)

        except VisionResponseContractError as exc:
            raise VisionExtractionError(
                f"Vision response failed validation: {exc}"
            ) from exc

        if not candidates:
            return VisionExtractionResult(
                status="no_candidates",
                candidates=[],
                message=(
                    "No legible equipment information was detected "
                    "in the image."
                ),
            )

        return VisionExtractionResult(
            status="candidates_found",
            candidates=candidates,
            message=f"{len(candidates)} candidate(s) detected.",
        )


def _default_vision_call_fn(
    api_key: str,
    model_name: str,
    image_bytes: bytes,
    mime_type: str,
) -> str:
    """
    Real Gemini Vision API call using the current google-genai SDK.

    This replaces the old `google.generativeai` SDK.
    """

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    response = client.models.generate_content(
        model=model_name,
        contents=[
            _PROMPT,
            image_part,
        ],
        config=types.GenerateContentConfig(
            # This is a label/display read, not a reasoning task — low
            # thinking keeps the call fast and, more importantly, keeps
            # the model from padding its answer with commentary that
            # would break the strict JSON parse below.
            thinking_config=types.ThinkingConfig(thinking_level="low"),
            # Enforce JSON at the API level instead of relying on the
            # model to voluntarily follow the "respond with ONLY JSON"
            # instruction in the prompt text.
            response_mime_type="application/json",
        ),
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text