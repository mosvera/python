# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mosvera import (
    ResolutionError,
    compile_contract,
    resolve_composition,
    resolve_named_composition,
    resolve_palette,
    resolve_template,
)

FIXTURES = Path(__file__).parent / "fixtures" / "compliance"


def _load_vectors(kind: str) -> list[dict[str, Any]]:
    return [
        json.loads(path.read_text(encoding="utf8"))
        for path in sorted((FIXTURES / kind).glob("*.json"))
    ]


def _run_resolution(vector: dict[str, Any]) -> dict[str, Any]:
    registry = vector.get("registry", {})
    strategies = vector.get("merge_strategies", {})
    try:
        input_kind = vector.get("input_kind")
        if input_kind == "template":
            canonical = resolve_template(vector["input"], registry, strategies)
        elif input_kind == "palette":
            canonical = resolve_palette(vector["input"], registry, strategies)
        elif input_kind == "composition_ref":
            canonical = resolve_named_composition(vector["input"], registry, strategies)
        else:
            canonical = resolve_composition(vector["input"], registry, strategies)
        return {"canonical": canonical}
    except ResolutionError as exc:
        return {"status": "error", "error": exc.kind}


def _run_compilation(vector: dict[str, Any]) -> dict[str, Any]:
    return compile_contract(
        vector["canonical"],
        vector["manifest"],
        vector.get("criticality", {}),
    )


@pytest.mark.parametrize("vector", _load_vectors("resolution"), ids=lambda v: v["id"])
def test_resolution_conformance(vector: dict[str, Any]) -> None:
    assert _run_resolution(vector) == vector["expect"]


@pytest.mark.parametrize("vector", _load_vectors("compilation"), ids=lambda v: v["id"])
def test_compilation_conformance(vector: dict[str, Any]) -> None:
    assert _run_compilation(vector) == vector["expect"]
