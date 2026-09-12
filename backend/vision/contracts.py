"""
Data contracts for the vision (P1 image input) pipeline.

Shapes only — no logic, no I/O. Mirrors the style of engine/contracts.py:
every other vision module imports its vocabulary from here.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class VisionCandidate:
    """
    One detected equipment/error identification guess read from an
    uploaded image. This is a CANDIDATE for the user to confirm or edit —
    never troubleshooting content, and never treated as verified evidence
    on its own.
    """

    equipment_category: Optional[str]
    manufacturer: Optional[str]
    model: Optional[str]
    code: Optional[str]
    confidence: float  # 0.0-1.0, self-reported by the vision model — advisory only, never trusted alone
    raw_model_text: Optional[str] = None  # the literal nameplate/label text read, shown to the user for review


@dataclass(frozen=True)
class ImageQualityCheck:
    """Result of the pre-Vision-call quality check in vision/image_intake.py."""

    usable: bool
    reason: Optional[str] = None  # "too_blurry" | "too_dark" | "too_bright_or_glare" | "unreadable_file"


@dataclass(frozen=True)
class VisionExtractionResult:
    """
    What vision/vision_extract.py hands back. `status` is one of:
    "candidates_found" | "no_candidates" | "error". Never a troubleshooting
    result — only detection candidates for confirmation.
    """

    status: str
    candidates: List[VisionCandidate] = field(default_factory=list)
    message: str = ""