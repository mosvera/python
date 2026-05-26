# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from .types import MergeStrategies, MergeStrategy

SCHEMA_FILES = [
    "common.schema.json",
    "composition.schema.json",
    "template.schema.json",
    "modifier.schema.json",
    "palette.schema.json",
    "capability-manifest.schema.json",
]


def _collect(node: Any, out: MergeStrategies) -> None:
    if isinstance(node, list):
        for child in node:
            _collect(child, out)
        return
    if not isinstance(node, dict):
        return

    props = node.get("properties")
    if isinstance(props, dict):
        for name, child in props.items():
            if isinstance(child, dict) and isinstance(child.get("x-mosvera-merge"), dict):
                out[name] = cast(MergeStrategy, child["x-mosvera-merge"])

    for value in node.values():
        _collect(value, out)


def derive_strategies(schema_dir: str | Path | None = None) -> MergeStrategies:
    base = Path(schema_dir) if schema_dir is not None else Path(__file__).parent / "schemas"
    out: MergeStrategies = {}
    for name in SCHEMA_FILES:
        schema = json.loads((base / name).read_text(encoding="utf8"))
        _collect(schema, out)
    return out
