"""
Shared FastAPI dependencies.

Route handlers should depend on these functions rather than importing
`get_settings()` / `get_knowledge_base()` directly, so that tests can
override them cleanly via FastAPI's dependency_overrides mechanism later.
"""

from config.settings import Settings, get_settings
from engine.kb_loader import KnowledgeBase, get_knowledge_base


def get_settings_dep() -> Settings:
    return get_settings()


def get_kb_dep() -> KnowledgeBase:
    return get_knowledge_base()