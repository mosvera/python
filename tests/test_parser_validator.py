# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from mosvera import create_validator, parse


def test_parse_json_string() -> None:
    assert parse('{"base":"x","modifiers":["m"]}') == {"base": "x", "modifiers": ["m"]}


def test_parse_yaml_string() -> None:
    assert parse("base: cinematic-editorial\nmodifiers:\n  - magic-hour\n") == {
        "base": "cinematic-editorial",
        "modifiers": ["magic-hour"],
    }


def test_parse_passes_mapping_through() -> None:
    doc = {"base": "x"}
    assert parse(doc) is doc


def test_parse_rejects_non_mapping() -> None:
    with pytest.raises(TypeError, match="mapping/object"):
        parse("[1, 2, 3]")


def test_validator_accepts_composition() -> None:
    validator = create_validator()
    result = validator.validate(
        {"base": "cinematic-editorial", "modifiers": ["magic-hour"]}, "composition"
    )
    assert result.valid is True
    assert result.errors == []


def test_validator_rejects_bad_composition() -> None:
    validator = create_validator()
    result = validator.validate({"modifiers": ["magic-hour"]}, "composition")
    assert result.valid is False
    assert result.errors
