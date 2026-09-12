"""Tests for engine/grounding/response_contract.py."""

import json

import pytest

from engine.grounding.response_contract import ResponseContractError, parse_grounded_answer


def _valid_payload() -> dict:
    return {
        "issue_summary": "Leakage current is too high.",
        "meaning_explanation": "The inverter detected more current leaking to ground than is safe.",
        "cause_explanations": ["Could be caused by wiring or insulation issues."],
        "safe_check_guidance": [],
        "technician_only_guidance": ["Only a qualified electrician should inspect the wiring."],
        "next_action": "Restart the inverter; if the error persists, contact Growatt support.",
    }


def test_parses_valid_json():
    answer = parse_grounded_answer(json.dumps(_valid_payload()))
    assert answer.issue_summary == "Leakage current is too high."
    assert answer.cause_explanations == ["Could be caused by wiring or insulation issues."]
    assert answer.safe_check_guidance == []


def test_strips_accidental_markdown_fence():
    fenced = "```json\n" + json.dumps(_valid_payload()) + "\n```"
    answer = parse_grounded_answer(fenced)
    assert answer.next_action.startswith("Restart the inverter")


def test_missing_required_field_raises():
    payload = _valid_payload()
    del payload["meaning_explanation"]
    with pytest.raises(ResponseContractError):
        parse_grounded_answer(json.dumps(payload))


def test_empty_required_field_raises():
    payload = _valid_payload()
    payload["issue_summary"] = "   "
    with pytest.raises(ResponseContractError):
        parse_grounded_answer(json.dumps(payload))


def test_invalid_json_raises():
    with pytest.raises(ResponseContractError):
        parse_grounded_answer("this is not json at all")


def test_non_object_json_raises():
    with pytest.raises(ResponseContractError):
        parse_grounded_answer(json.dumps(["not", "an", "object"]))


def test_missing_list_fields_default_to_empty_list_not_error():
    payload = _valid_payload()
    del payload["cause_explanations"]
    del payload["safe_check_guidance"]
    del payload["technician_only_guidance"]
    answer = parse_grounded_answer(json.dumps(payload))
    assert answer.cause_explanations == []
    assert answer.safe_check_guidance == []
    assert answer.technician_only_guidance == []


def test_non_string_items_in_list_are_stringified_and_blanks_dropped():
    payload = _valid_payload()
    payload["cause_explanations"] = ["real cause", "", "   ", 42]
    answer = parse_grounded_answer(json.dumps(payload))
    assert answer.cause_explanations == ["real cause", "42"]