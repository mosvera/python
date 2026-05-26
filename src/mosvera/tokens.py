# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from .types import CssVariableMap, DesignTokens, JsonObject

RECOGNIZED = {"palette", "typography", "layout", "motion", "imagery", "voice"}


def compile_design_tokens(canonical: JsonObject, preserve_unknown: bool = True) -> DesignTokens:
    tokens: DesignTokens = {"extensions": {}}
    for key, value in canonical.items():
        if key in RECOGNIZED and isinstance(value, dict):
            tokens[key] = deepcopy(value)
        elif preserve_unknown:
            tokens["extensions"][key] = deepcopy(value)
    return tokens


def _kebab(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "-", value.replace("_", "-")).lower()


def _css_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return json.dumps(value, separators=(",", ":"))


def _flatten(out: CssVariableMap, prefix: str, value: Any) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            _flatten(out, f"{prefix}-{_kebab(key)}", value[key])
        return
    out[f"--{prefix}"] = _css_value(value)


def to_css_variables(tokens: DesignTokens, prefix: str = "mosvera") -> CssVariableMap:
    out: CssVariableMap = {}
    root = _kebab(prefix)
    for key in sorted(tokens):
        value = tokens[key]
        _flatten(out, f"{root}-{_kebab(key)}", value)
    return out
