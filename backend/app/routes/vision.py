"""
POST /api/vision/extract

Image -> quality pre-check -> Gemini Vision/OCR -> structured detection
candidates.

This endpoint NEVER returns troubleshooting content and NEVER calls the
troubleshooting engine. Its output is always a set of candidates for the
user to confirm or edit; the frontend then submits the confirmed identity
to POST /api/troubleshoot with source="image" to enter the shared engine
— see app/routes/troubleshoot.py and vision/confirmation.py.
"""

from fastapi import APIRouter, Depends, File, UploadFile

from app.deps import get_vision_extractor_dep
from app.schemas import VisionCandidateOut, VisionExtractResponse
from vision.image_intake import check_image_quality
from vision.vision_extract import VisionExtractionError, VisionExtractor

router = APIRouter(prefix="/api", tags=["vision"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/vision/extract", response_model=VisionExtractResponse)
async def extract_from_image(
    file: UploadFile = File(...),
    extractor: VisionExtractor = Depends(get_vision_extractor_dep),
) -> VisionExtractResponse:
    image_bytes = await file.read()

    quality = check_image_quality(image_bytes)
    if not quality.usable:
        return VisionExtractResponse(
            status="image_unclear",
            reason=quality.reason,
            candidates=[],
            message="The image could not be read clearly enough to detect equipment information.",
        )

    mime_type = file.content_type if file.content_type in _ALLOWED_CONTENT_TYPES else "image/jpeg"

    try:
        result = extractor.extract(image_bytes, mime_type=mime_type)
    except VisionExtractionError as exc:
        return VisionExtractResponse(
            status="error",
            reason=None,
            candidates=[],
            message=str(exc),
        )

    return VisionExtractResponse(
        status=result.status,
        reason=None,
        candidates=[
            VisionCandidateOut(
                equipment_category=candidate.equipment_category,
                manufacturer=candidate.manufacturer,
                model=candidate.model,
                code=candidate.code,
                confidence=candidate.confidence,
                raw_model_text=candidate.raw_model_text,
            )
            for candidate in result.candidates
        ],
        message=result.message,
    )