"""
Static, non-dataset configuration constants for Ustad Assist.

IMPORTANT — single source of truth rule:
The supported equipment/manufacturer/model list is intentionally NOT defined
here as a hardcoded allow-list. Per the approved architecture, the verified
knowledge base (backend/data/verified_records.json, via
engine/kb_loader.py::KnowledgeBase.catalog()) is the single source of truth
for what is "supported." Hardcoding a second list here would create a
conflicting second source of truth, which the architecture explicitly
forbids. If you need the supported catalog, call:

    from engine.kb_loader import get_knowledge_base
    get_knowledge_base().catalog()

This module only holds constants that are genuinely independent of the
dataset content.
"""

from engine.contracts import EquipmentCategory, VerificationStatus

# Equipment categories the product is architected to support. This is a
# product-scope constant (P0 = solar_inverter + ups per the PRD), not a
# model allow-list — it does not say which manufacturers/models within
# these categories are supported; that still comes only from the KB.
SUPPORTED_EQUIPMENT_CATEGORIES = [c.value for c in EquipmentCategory]

# PRD Section 8: a model is only considered "release-gated supported" once
# at least this many records for it have passed verification. Not enforced
# yet in Phase 1 (no retrieval/verification-gate logic exists yet) —
# reserved for the phase that implements the release gate.
MIN_VERIFIED_RECORDS_PER_MODEL = 5

# Verification statuses considered eligible to serve as troubleshooting
# evidence. Mirrors PRD Section 16's status list — only "verified" records
# may be used as confirmed evidence.
EVIDENCE_ELIGIBLE_VERIFICATION_STATUSES = [VerificationStatus.VERIFIED.value]

# All verification statuses the dataset may legally contain, per PRD
# Section 16. Used later for validating unexpected values in the raw file
# rather than silently accepting anything.
KNOWN_VERIFICATION_STATUSES = [status.value for status in VerificationStatus]