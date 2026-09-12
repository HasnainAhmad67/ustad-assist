"""
Tests for vision/image_intake.py. All fully real — no mocking, no stubs —
since these checks are pure local computation (PIL + numpy), unlike the
Vision API call itself.
"""

from io import BytesIO

import numpy as np
from PIL import Image

from vision.image_intake import check_image_quality

print("🔥 IMAGE INTAKE TESTS")

def _png_bytes_from_array(array: np.ndarray) -> bytes:
    image = Image.fromarray(array.astype("uint8"), mode="L")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_solid_dark_image_is_too_dark():
    array = np.full((200, 200), 10, dtype="uint8")
    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is False
    assert result.reason == "too_dark"


def test_solid_bright_image_is_flagged_as_glare():
    array = np.full((200, 200), 255, dtype="uint8")
    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is False
    assert result.reason == "too_bright_or_glare"


def test_solid_mid_gray_image_is_too_blurry():
    """A perfectly flat mid-gray image has zero edge variance — brightness
    is fine, but there's no texture at all, which is what a truly
    out-of-focus photo also looks like to this check."""
    array = np.full((200, 200), 128, dtype="uint8")
    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is False
    assert result.reason == "too_blurry"


def test_noisy_mid_brightness_image_is_usable():
    rng = np.random.default_rng(seed=42)
    array = rng.integers(low=60, high=200, size=(200, 200), dtype="uint8")
    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is True
    assert result.reason is None


def test_checkerboard_high_contrast_image_is_usable():
    """A sharp, high-contrast pattern should clear both the brightness and
    sharpness thresholds easily."""
    array = np.indices((200, 200)).sum(axis=0) % 2 * 255
    result = check_image_quality(_png_bytes_from_array(array.astype("uint8")))
    assert result.usable is True


def test_bright_white_background_product_photo_is_usable():
    """
    Regression test for the reported false rejection: a realistic product
    photo with a large white/bright studio background (mean brightness
    ~247, large fraction of near-white pixels) but a genuinely legible
    device label must be accepted, not rejected as glare — the label's
    real edges/detail are what should determine usability, not the
    background brightness alone.
    """
    array = np.full((400, 400), 253, dtype="uint8")
    array[140:280, 120:280] = 210  # device body
    array[160:190, 140:260] = 250  # white label patch on the device
    rng = np.random.default_rng(seed=7)
    for _ in range(60):
        x = rng.integers(145, 255)
        y = rng.integers(165, 185)
        array[y : y + 2, x : x + 6] = 20  # simulated label text strokes

    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is True
    assert result.reason is None


def test_genuine_overexposed_glare_with_faint_noise_is_still_rejected():
    """
    A truly overexposed/glare frame — very bright, almost entirely blown
    out, with only faint sensor-noise-level texture and no real
    recoverable content — must still be rejected. This is what
    distinguishes true glare from the bright-background product photo
    above: the faint noise alone must not be mistaken for real detail.
    """
    rng = np.random.default_rng(seed=3)
    array = (253 + rng.integers(-2, 3, size=(300, 300))).clip(0, 255).astype("uint8")

    result = check_image_quality(_png_bytes_from_array(array))
    assert result.usable is False
    assert result.reason == "too_bright_or_glare"


def test_empty_bytes_is_unreadable():
    result = check_image_quality(b"")
    assert result.usable is False
    assert result.reason == "unreadable_file"


def test_garbage_bytes_is_unreadable():
    result = check_image_quality(b"this is definitely not a valid image file")
    assert result.usable is False
    assert result.reason == "unreadable_file"