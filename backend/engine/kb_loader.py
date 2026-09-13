"""
Knowledge base loader and normalizer.

This is the ONLY module in the entire backend that reads
backend/data/verified_records.json directly. Every other module consumes
the normalized `NormalizedRecord` shape from engine/contracts.py.

Normalization decisions implemented here (see architecture §0 for the full
reasoning behind each one — nothing here is arbitrary):

1. Canonical code field: Growatt records use `error_code_or_warning`, Eaton
   records use `error_code_or_alarm`. Both are mapped to one field: `code`.
2. `type` field: present for Growatt records, absent for Eaton records.
   Where absent, a display-only label is inferred. This label is NEVER
   used as a filtering/matching key — only `code` is.
3. `possible_causes` / `safe_user_checks` / `technician_only_checks`:
   inconsistently typed in the raw dataset (string for some records, list
   for others; placeholder strings like "Not stated in manual" for others).
   All three are normalized to `List[str]`, with placeholder-only values
   normalized to an empty list rather than kept as literal placeholder
   text — an empty list means "the manual does not state this," which is
   the true meaning, not "the manual says the literal words 'not stated'."
4. `page`: an int for some Growatt records, a string for Eaton records.
   Always normalized to `Optional[str]`.
5. `record_id`: does not exist in the raw dataset. A stable synthetic ID is
   derived (never random) from equipment identity, code, issue title, and
   source page because the expanded dataset can contain multiple manual rows
   with the same displayed code.
6. `model_aliases` / `model_family`: only present at the `manual_metadata`
   level in the raw dataset, not per record. Resolved here via a join on
   (equipment_category, model).
7. `manual_version`: the raw dataset has no such field; `manual_document_number`
   is used as the version identifier — no data is missing, only the PRD's
   field name differs from the dataset's.
8. `verification.verified_by` / `verification.verified_at`: the PRD's
   Section 17 schema expects these; the raw dataset does not have them.
   They are NOT fabricated. Only the fields that actually exist
   (`verification_status`, `verification_notes`) are carried through.
9. Manufacturer legal name vs. brand name: `manual_metadata`'s
   `manufacturer` field ("Shenzhen Growatt New Energy CO.,LTD") is NOT
   used for matching — only the per-record `manufacturer` field ("Growatt")
   is, since that's what every record and the intended UI actually use.
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config.settings import get_settings
from engine.contracts import CatalogError, CatalogModel, NormalizedRecord, SourceCitation, VerificationStatus

# Substrings (checked case-insensitively) that mark a raw string value as a
# placeholder meaning "the manual does not state this" rather than actual
# content. Anything matching one of these becomes an empty list, not a
# literal one-item list containing the placeholder text.
_PLACEHOLDER_MARKERS = (
    "not stated in manual",
    "not explicitly classified",
    "not applicable",
)


def _is_placeholder(value: Optional[str]) -> bool:
    if not value:
        return True
    lowered = value.strip().lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _normalize_string_or_list_field(value) -> List[str]:
    """
    Normalizes a field that may arrive as a string, a list of strings, or
    be missing, into a clean List[str] with placeholder values dropped.
    """
    if value is None:
        return []
    if isinstance(value, list):
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text and not _is_placeholder(text):
                cleaned.append(text)
        return cleaned
    if isinstance(value, str):
        text = value.strip()
        if not text or _is_placeholder(text):
            return []
        return [text]
    # Unexpected type (number, dict, etc.) — do not guess; drop rather than
    # silently misrepresent the data.
    return []


def _normalize_steps(value) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _make_record_id(
    equipment_category: str,
    manufacturer: str,
    model: str,
    code: str,
    issue_title: str,
    page: Optional[str],
) -> str:
    """
    Deterministic, stable synthetic ID. Same inputs always produce the same
    ID, so it stays stable across reloads without needing to persist it
    anywhere.
    """
    raw = (
        f"{equipment_category}|{manufacturer}|{model}|{code}|"
        f"{issue_title}|{page or ''}"
    ).strip().lower()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _infer_issue_type(raw_record: dict) -> Optional[str]:
    """
    Display-only label. Growatt records already have a `type` field
    ("error"). Eaton records don't — for those, infer a reasonable display
    label from context. This value must NEVER be used for retrieval
    filtering; `code` is the only matching key.
    """
    if raw_record.get("type"):
        return str(raw_record["type"]).strip().lower()
    # Eaton UPS records without an explicit `type` are status/alarm
    # conditions (e.g. "Battery mode", "Battery test failed") rather than
    # numbered fault codes — "alarm" is the accurate display label.
    return "alarm"


class KnowledgeBase:
    """
    Loads backend/data/verified_records.json once and exposes a normalized,
    read-only view of it. Safe to hold as a singleton for the process
    lifetime — see get_knowledge_base() below.
    """

    def __init__(self, data_path: Path):
        self.data_path = data_path
        self._raw: dict = {}
        self._records: List[NormalizedRecord] = []
        self._manual_metadata_by_key: Dict[Tuple[str, str], dict] = {}
        self._global_safety: Dict[str, List[str]] = {}
        self._loaded = False

    def load(self) -> None:
        """Idempotent — safe to call more than once; only loads from disk once."""
        if self._loaded:
            return

        if not self.data_path.exists():
            raise FileNotFoundError(
                f"Verified knowledge base not found at '{self.data_path}'. "
                "Ustad Assist cannot start without data/verified_records.json."
            )

        with self.data_path.open("r", encoding="utf-8") as f:
            self._raw = json.load(f)

        self._global_safety = {
            str(manufacturer).lower(): [str(note) for note in (notes or [])]
            for manufacturer, notes in (self._raw.get("global_safety") or {}).items()
        }

        self._manual_metadata_by_key = {}
        for meta in self._raw.get("manual_metadata", []) or []:
            key = (meta.get("equipment_category"), meta.get("model"))
            self._manual_metadata_by_key[key] = meta

        normalized: List[NormalizedRecord] = []
        for raw_record in self._raw.get("records", []) or []:
            normalized.append(self._normalize_record(raw_record))

        self._records = normalized
        self._loaded = True

    def _normalize_record(self, raw: dict) -> NormalizedRecord:
        equipment_category = str(raw.get("equipment_category", "")).strip()
        manufacturer = str(raw.get("manufacturer", "")).strip()
        model = str(raw.get("model", "")).strip()

        # Decision 1: canonical code field.
        code = raw.get("error_code_or_warning")
        if code is None:
            code = raw.get("error_code_or_alarm")
        code = str(code).strip() if code is not None else ""

        # Decision 2: display-only issue type.
        issue_type = _infer_issue_type(raw)

        # Decision 3: causes/checks normalized to List[str].
        possible_causes = _normalize_string_or_list_field(raw.get("possible_causes"))
        safe_user_checks = _normalize_string_or_list_field(raw.get("safe_user_checks"))
        technician_only_checks = _normalize_string_or_list_field(raw.get("technician_only_checks"))
        troubleshooting_steps = _normalize_steps(raw.get("troubleshooting_steps"))

        # Decision 4: page always a string.
        source_raw = raw.get("source") or {}
        raw_page = source_raw.get("page")
        page = str(raw_page).strip() if raw_page is not None else None

        source = SourceCitation(
            manual_title=str(source_raw.get("manual_title") or raw.get("manual_title") or "").strip(),
            manual_document_number=(
                source_raw.get("manual_document_number") or raw.get("manual_document_number")
            ),
            page=page,
            official_url=source_raw.get("official_url") or raw.get("official_source_url"),
            section=None,  # not present in the current dataset (architecture §0)
            pdf_page=None,  # not present in the current dataset (architecture §0)
        )

        # Decision 6: alias/family resolution via join on (category, model).
        meta = self._manual_metadata_by_key.get((equipment_category, model), {})
        model_aliases = [str(a) for a in (meta.get("model_aliases") or [])]
        model_family = [str(m) for m in (meta.get("model_family") or [])]

        safety_warning = str(raw.get("safety_warning") or "").strip()
        global_safety_notes = list(self._global_safety.get(manufacturer.lower(), []))

        # Decision 8: only carry through fields that actually exist.
        verification_status = raw.get("verification_status") or VerificationStatus.NOT_VERIFIED.value
        verification_notes = raw.get("verification_notes")

        issue_title = str(raw.get("issue_title") or "").strip()
        record_id = _make_record_id(
            equipment_category, manufacturer, model, code, issue_title, page
        )

        return NormalizedRecord(
            record_id=record_id,
            equipment_category=equipment_category,
            manufacturer=manufacturer,
            model=model,
            model_aliases=model_aliases,
            model_family=model_family,
            manual_title=source.manual_title,
            manual_version=source.manual_document_number,  # Decision 7
            manual_language="English",
            code=code,
            issue_type=issue_type,
            issue_title=issue_title,
            meaning=str(raw.get("meaning") or "").strip(),
            possible_causes=possible_causes,
            troubleshooting_steps=troubleshooting_steps,
            safe_user_checks=safe_user_checks,
            technician_only_checks=technician_only_checks,
            safety_warning=safety_warning,
            global_safety_notes=global_safety_notes,
            source=source,
            verification_status=str(verification_status),
            verification_notes=verification_notes,
        )

    @property
    def records(self) -> List[NormalizedRecord]:
        self.load()
        return list(self._records)

    def verified_records(self) -> List[NormalizedRecord]:
        """
        Only records with verification_status == "verified" are eligible to
        serve as troubleshooting evidence, per PRD Section 16. This is the
        enforcement point referenced throughout the architecture doc as
        "verified-record-only evidence."
        """
        return [
            r for r in self.records if r.verification_status == VerificationStatus.VERIFIED.value
        ]

    def catalog(self) -> List[CatalogModel]:
        """
        The supported-equipment catalog, derived directly from verified
        records. This is deliberately NOT a hardcoded allow-list anywhere
        in config/constants.py — the knowledge base remains the single
        source of truth for what is "supported."
        """
        seen: Dict[Tuple[str, str, str], CatalogModel] = {}
        errors_by_model: Dict[Tuple[str, str, str], List[CatalogError]] = {}
        for record in self.verified_records():
            key = (record.equipment_category, record.manufacturer, record.model)
            option = CatalogError(
                code=record.code,
                label=record.issue_title or record.meaning or record.code,
                error_type=record.issue_type,
            )
            current = errors_by_model.setdefault(key, [])
            if not any(
                item.code == option.code
                and item.label == option.label
                and item.error_type == option.error_type
                for item in current
            ):
                current.append(option)

        # The expanded dataset contains officially documented catalog models
        # for which no page-verified troubleshooting row was available. They
        # are supported identities, but not evidence-bearing fault records.
        # Include them in the catalog without inventing a troubleshooting
        # record; retrieval will correctly return issue_not_verified when no
        # verified issue matches.
        for model_meta in self._raw.get("models", []) or []:
            equipment_category = str(model_meta.get("equipment_category") or "").strip()
            manufacturer = str(model_meta.get("manufacturer") or "").strip()
            model = str(model_meta.get("model") or "").strip()
            if not equipment_category or not manufacturer or not model:
                continue
            key = (equipment_category, manufacturer, model)
            seen[key] = CatalogModel(
                equipment_category=equipment_category,
                manufacturer=manufacturer,
                model=model,
                model_aliases=[
                    str(alias).strip()
                    for alias in (model_meta.get("model_aliases") or [])
                    if str(alias).strip()
                ],
                error_options=sorted(
                    errors_by_model.get(key, []),
                    key=lambda option: (option.code, option.label),
                ),
            )

        for record in self.verified_records():
            key = (record.equipment_category, record.manufacturer, record.model)
            if key not in seen:
                seen[key] = CatalogModel(
                    equipment_category=record.equipment_category,
                    manufacturer=record.manufacturer,
                    model=record.model,
                    model_aliases=record.model_aliases,
                    error_options=sorted(
                        errors_by_model.get(key, []),
                        key=lambda option: (option.code, option.label),
                    ),
                )
        return sorted(
            seen.values(),
            key=lambda c: (c.equipment_category, c.manufacturer, c.model),
        )

    def stats(self) -> dict:
        """Lightweight summary used by the /health endpoint."""
        records = self.records
        verified = self.verified_records()
        return {
            "dataset_name": self._raw.get("dataset_name"),
            "dataset_version": self._raw.get("dataset_version"),
            "total_records": len(records),
            "verified_records": len(verified),
            "manufacturers": sorted({r.manufacturer for r in records}),
            "equipment_categories": sorted({r.equipment_category for r in records}),
        }


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    """
    Process-lifetime singleton. Loaded once at FastAPI startup, not
    reloaded per request.
    """
    settings = get_settings()
    kb = KnowledgeBase(settings.verified_records_path)
    kb.load()
    return kb
