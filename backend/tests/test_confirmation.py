"""Tests for vision/confirmation.py."""

import pytest

from vision.confirmation import build_confirmed_query


def test_valid_confirmation_builds_query_with_image_source():
    query = build_confirmed_query(
        equipment_category="solar_inverter",
        manufacturer="Growatt",
        model="MIN 3000 TL-X",
        code="201",
    )
    assert query.source == "image"
    assert query.manufacturer == "Growatt"


def test_missing_manufacturer_raises():
    with pytest.raises(ValueError, match="manufacturer"):
        build_confirmed_query(equipment_category="solar_inverter", manufacturer=None, model="MIN 3000 TL-X")


def test_missing_model_raises():
    with pytest.raises(ValueError, match="model"):
        build_confirmed_query(equipment_category="solar_inverter", manufacturer="Growatt", model="")


def test_missing_equipment_category_raises():
    with pytest.raises(ValueError, match="equipment_category"):
        build_confirmed_query(equipment_category=None, manufacturer="Growatt", model="MIN 3000 TL-X")


def test_multiple_missing_fields_all_reported():
    with pytest.raises(ValueError) as exc_info:
        build_confirmed_query(equipment_category=None, manufacturer="   ", model="MIN 3000 TL-X")
    message = str(exc_info.value)
    assert "equipment_category" in message
    assert "manufacturer" in message