"""
Thin wrapper around the Gemini API for grounded text generation.

This module contains NO retrieval or prompt-construction logic — it only
sends an already-built prompt and parses the result. Any failure (missing
key, network/API error, invalid response shape) surfaces as one uniform
GeminiGenerationError so the caller can map it to
TroubleshootStatus.ERROR without inspecting exception subtypes.

The actual network call is isolated behind an injectable `call_fn` so this
module can be unit-tested without network access or a real API key — the
default implementation is the real google-generativeai SDK, imported
lazily so importing this module never requires the package to be
installed unless generate() is actually called with no override.
"""

from typing import Callable, Optional

from config.settings import get_settings
from engine.contracts import GroundedAnswer
from engine.grounding.response_contract import ResponseContractError, parse_grounded_answer

DEFAULT_MODEL_NAME = "gemini-3.6-flash"

CallFn = Callable[[str, str, str], str]  # (api_key, model_name, prompt) -> raw_text


class GeminiGenerationError(Exception):
    """
    Raised for any failure to obtain a valid grounded answer: a missing
    API key, a network/API error, or a response that fails
    response_contract.py's shape validation. Callers should treat every
    instance of this uniformly as "generation failed."
    """


class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = DEFAULT_MODEL_NAME,
        call_fn: Optional[CallFn] = None,
    ):
        settings = get_settings()
        self._api_key = api_key or settings.gemini_api_key
        self._model_name = model_name
        self._call_fn: CallFn = call_fn or _default_call_fn

    def generate(self, prompt: str) -> GroundedAnswer:
        if not self._api_key:
            raise GeminiGenerationError(
                "GEMINI_API_KEY is not configured. Set it in the environment "
                "before requesting grounded generation."
            )

        try:
            raw_text = self._call_fn(self._api_key, self._model_name, prompt)
        except Exception as exc:  # noqa: BLE001 — any SDK/network failure is uniformly a generation failure
            raise GeminiGenerationError(f"Gemini API call failed: {exc}") from exc

        try:
            return parse_grounded_answer(raw_text)
        except ResponseContractError as exc:
            raise GeminiGenerationError(f"Gemini response failed validation: {exc}") from exc


def _default_call_fn(api_key: str, model_name: str, prompt: str) -> str:
    """The real Gemini SDK call. Imported lazily so this module can be
    imported, and GeminiClient constructed, without the package installed
    unless generate() is actually invoked with the default call_fn."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text