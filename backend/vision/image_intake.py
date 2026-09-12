"""
Pre-Vision-call image quality checks: blur, darkness, and overexposure/
glare. Runs BEFORE any Gemini Vision call, so an unusable image produces
the "image unclear" state without spending an API call.

All checks here are pure local computation (PIL + numpy) — no network, no
API key required. This is deliberate: quality is exactly the kind of thing
that should never depend on the external service being available.

Rotation detection is intentionally NOT attempted here. No lightweight,
reliable heuristic exists for arbitrary nameplate/label photos taken in
the field, and Gemini Vision's own OCR is reasonably tolerant of moderate
rotation. If this proves insufficient once real photos are tested, add a
dedicated check then rather than guessing at a threshold now.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

from vision.contracts import ImageQualityCheck

# Mean grayscale brightness is on a 0-255 scale.
MIN_BRIGHTNESS_MEAN = 35.0  # below this, likely too dark to read text/labels

# Signals that a frame MIGHT be overexposed/glare — brightness and blown-
# highlight fraction alone. Neither is used as an independent rejection
# gate: a legitimate product/nameplate photo with a large white background
# or a white label routinely has high overall brightness and a large
# fraction of near-white pixels while still being perfectly readable, since
# the actual text/markings retain real contrast and edges. These two
# signals are only used to decide *why* an already-detail-deficient image
# is unusable (glare vs. blur) — see check_image_quality below.
GLARE_MEAN_BRIGHTNESS_FLOOR = 150.0
GLARE_PIXEL_THRESHOLD = 250
GLARE_FRACTION_LIMIT = 0.35

# Variance of an edge-detected image is a simple sharpness proxy — a
# blurry photo has fewer/weaker edges, so lower variance. This is the
# ordinary bar used for normal-brightness images.
MIN_SHARPNESS_VARIANCE = 45.0

# A stricter detail bar used specifically when the brightness/glare
# signals above are present. Faint sensor noise on a genuinely blown-out,
# unreadable frame can produce just enough edge variance to clear the
# ordinary MIN_SHARPNESS_VARIANCE bar (confirmed directly: a synthetic
# near-white frame with only +/-2 noise measured ~46 — right at that bar)
# without containing any real recoverable content. Requiring noticeably
# more edge variance when the frame already looks bright/blown avoids that
# false negative, while a real product photo's actual label/markings
# clear this bar comfortably (confirmed directly: ~410 in a realistic
# bright-background reproduction of the reported false-rejection case).
MIN_SHARPNESS_VARIANCE_WHEN_BRIGHT = 100.0

# PIL's FIND_EDGES filter treats pixels outside the image as black when
# convolving at the border, which produces a false "edge" ring around the
# outside of every image regardless of actual content. A margin is cropped
# off before computing variance so this border artifact doesn't make a
# genuinely flat/blurry image look sharp (confirmed by direct testing: a
# perfectly flat image showed edge variance ~320 before cropping, purely
# from this border effect, vs. 0.0 after cropping).
EDGE_VARIANCE_BORDER_MARGIN = 5


def _load_grayscale_array(image_bytes: bytes) -> np.ndarray:
    with Image.open(BytesIO(image_bytes)) as img:
        grayscale = img.convert("L")
        return np.asarray(grayscale, dtype="float32")


def _edge_variance(image_bytes: bytes) -> float:
    with Image.open(BytesIO(image_bytes)) as img:
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_array = np.asarray(edges, dtype="float32")

    margin = min(
        EDGE_VARIANCE_BORDER_MARGIN,
        edge_array.shape[0] // 4,
        edge_array.shape[1] // 4,
    )
    if margin > 0:
        cropped = edge_array[margin:-margin, margin:-margin]
        if cropped.size > 0:
            edge_array = cropped

    return float(edge_array.var())


def check_image_quality(image_bytes: bytes) -> ImageQualityCheck:
    if not image_bytes:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    try:
        gray = _load_grayscale_array(image_bytes)
    except Exception:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    if gray.size == 0:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    mean_brightness = float(gray.mean())
    if mean_brightness < MIN_BRIGHTNESS_MEAN:
        return ImageQualityCheck(usable=False, reason="too_dark")

    glare_fraction = float((gray >= GLARE_PIXEL_THRESHOLD).mean())
    looks_bright_or_blown = (
        mean_brightness > GLARE_MEAN_BRIGHTNESS_FLOOR or glare_fraction > GLARE_FRACTION_LIMIT
    )

    sharpness_variance = _edge_variance(image_bytes)

    if looks_bright_or_blown:
        # Only reject a bright/blown-highlight frame if it ALSO lacks real,
        # recoverable detail — a bright background alone is not glare.
        if sharpness_variance < MIN_SHARPNESS_VARIANCE_WHEN_BRIGHT:
            return ImageQualityCheck(usable=False, reason="too_bright_or_glare")
    else:
        if sharpness_variance < MIN_SHARPNESS_VARIANCE:
            return ImageQualityCheck(usable=False, reason="too_blurry")

    return ImageQualityCheck(usable=True, reason=None)