"""Local PIL-only image quality checks used before vision extraction."""

from io import BytesIO
from statistics import mean, pvariance

from PIL import Image, ImageFilter

from vision.contracts import ImageQualityCheck

MIN_BRIGHTNESS_MEAN = 35.0
GLARE_MEAN_BRIGHTNESS_FLOOR = 150.0
GLARE_PIXEL_THRESHOLD = 250
GLARE_FRACTION_LIMIT = 0.35
MIN_SHARPNESS_VARIANCE = 45.0
MIN_SHARPNESS_VARIANCE_WHEN_BRIGHT = 100.0
EDGE_VARIANCE_BORDER_MARGIN = 5


def _load_grayscale_pixels(image_bytes: bytes) -> tuple[list[int], int, int]:
    with Image.open(BytesIO(image_bytes)) as image:
        grayscale = image.convert("L")
        width, height = grayscale.size
        return list(grayscale.getdata()), width, height


def _edge_variance(image_bytes: bytes) -> float:
    with Image.open(BytesIO(image_bytes)) as image:
        edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
        width, height = edges.size
        pixels = list(edges.getdata())

    margin = min(EDGE_VARIANCE_BORDER_MARGIN, height // 4, width // 4)
    if margin <= 0:
        return float(pvariance(pixels)) if pixels else 0.0

    cropped: list[int] = []
    for row in range(margin, height - margin):
        start = row * width + margin
        end = row * width + width - margin
        cropped.extend(pixels[start:end])

    return float(pvariance(cropped)) if cropped else 0.0


def check_image_quality(image_bytes: bytes) -> ImageQualityCheck:
    if not image_bytes:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    try:
        pixels, _width, _height = _load_grayscale_pixels(image_bytes)
    except Exception:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    if not pixels:
        return ImageQualityCheck(usable=False, reason="unreadable_file")

    mean_brightness = float(mean(pixels))
    if mean_brightness < MIN_BRIGHTNESS_MEAN:
        return ImageQualityCheck(usable=False, reason="too_dark")

    glare_fraction = sum(pixel >= GLARE_PIXEL_THRESHOLD for pixel in pixels) / len(pixels)
    looks_bright_or_blown = (
        mean_brightness > GLARE_MEAN_BRIGHTNESS_FLOOR
        or glare_fraction > GLARE_FRACTION_LIMIT
    )
    sharpness_variance = _edge_variance(image_bytes)

    if looks_bright_or_blown:
        if sharpness_variance < MIN_SHARPNESS_VARIANCE_WHEN_BRIGHT:
            return ImageQualityCheck(usable=False, reason="too_bright_or_glare")
    elif sharpness_variance < MIN_SHARPNESS_VARIANCE:
        return ImageQualityCheck(usable=False, reason="too_blurry")

    return ImageQualityCheck(usable=True, reason=None)
