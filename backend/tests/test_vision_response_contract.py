"""Tests for vision/response_contract.py."""

import json

import pytest

from vision.response_contract import VisionResponseContractError, parse_vision_candidates


def test_parses_single_candidate():
    payload = json.dumps(
        {
            "candidates": [
                {
                    "equipment_category": "solar_inverter",
                    "manufacturer": "Growatt",
                    "model": "MIN 3000 TL-X",
                    "code": "201",
                    "confidence": 0.92,
                    "raw_model_text": "MIN 3000TL-X",
                }
            ]
        }
    )
    candidates = parse_vision_candidates(payload)
    assert len(candidates) == 1
    assert candidates[0].manufacturer == "Growatt"
    assert candidates[0].confidence == 0.92


def test_parses_multiple_candidates_for_ambiguous_reading():
    payload = json.dumps(
        {
            "candidates": [
                {"equipment_category": "solar_inverter", "manufacturer": "Growatt", "model": "MIN 3000 TL-X", "code": None, "confidence": 0.5},
                {"equipment_category": "solar_inverter", "manufacturer": "Growatt", "model": "MIN 5000 TL-X", "code": None, "confidence": 0.4},
            ]
        }
    )
    candidates = parse_vision_candidates(payload)
    assert len(candidates) == 2


def test_empty_candidates_list_is_valid():
    candidates = parse_vision_candidates(json.dumps({"candidates": []}))
    assert candidates == []


def test_strips_markdown_fence():
    fenced = "```json\n" + json.dumps({"candidates": []}) + "\n```"
    assert parse_vision_candidates(fenced) == []


def test_missing_candidates_key_raises():
    with pytest.raises(VisionResponseContractError):
        parse_vision_candidates(json.dumps({"something_else": []}))


def test_candidates_not_a_list_raises():
    with pytest.raises(VisionResponseContractError):
        parse_vision_candidates(json.dumps({"candidates": "not a list"}))


def test_invalid_json_raises():
    with pytest.raises(VisionResponseContractError):
        parse_vision_candidates("not json")


def test_confidence_is_clamped_to_0_1_range():
    payload = json.dumps({"candidates": [{"confidence": 5.0}]})
    candidates = parse_vision_candidates(payload)
    assert candidates[0].confidence == 1.0

    payload_negative = json.dumps({"candidates": [{"confidence": -3.0}]})
    candidates_negative = parse_vision_candidates(payload_negative)
    assert candidates_negative[0].confidence == 0.0


def test_missing_confidence_defaults_to_zero_not_an_error():
    payload = json.dumps({"candidates": [{"manufacturer": "Growatt"}]})
    candidates = parse_vision_candidates(payload)
    assert candidates[0].confidence == 0.0
    assert candidates[0].manufacturer == "Growatt"


def test_non_dict_items_in_candidates_list_are_skipped_not_erroring():
    payload = json.dumps({"candidates": ["not a dict", {"manufacturer": "Growatt", "confidence": 0.8}]})
    candidates = parse_vision_candidates(payload)
    assert len(candidates) == 1
    assert candidates[0].manufacturer == "Growatt"