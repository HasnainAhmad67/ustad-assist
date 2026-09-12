"""
Shared FastAPI dependencies.

Route handlers should depend on these functions rather than importing
`get_settings()` / `get_knowledge_base()` / constructing a `GeminiClient`
directly, so that tests can override them cleanly via FastAPI's
dependency_overrides mechanism.
"""

from config.settings import Settings, get_settings
from engine.grounding.gemini_client import GeminiClient
from engine.kb_loader import KnowledgeBase, get_knowledge_base


def get_settings_dep() -> Settings:
    return get_settings()


def get_kb_dep() -> KnowledgeBase:
    return get_knowledge_base()


def get_gemini_client_dep() -> GeminiClient:
    """
    Returns a real GeminiClient, configured from settings.gemini_api_key.
    Tests override this dependency with a fake client (injected call_fn)
    rather than needing network access or a real API key.
    """
    return GeminiClient()