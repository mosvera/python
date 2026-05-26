# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import yaml

from .types import JsonObject


def parse(source: str | Mapping[str, Any]) -> JsonObject:
    doc: Any = yaml.safe_load(source) if isinstance(source, str) else source
    if not isinstance(doc, dict):
        raise TypeError("Mosvera document must be a mapping/object at the top level")
    return cast(JsonObject, doc)
