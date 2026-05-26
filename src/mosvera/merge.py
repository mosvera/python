# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypeGuard

from .types import Json, JsonObject, MergeStrategies, MergeStrategy

STRUCTURAL = {"id", "$schema", "$extends", "base", "modifiers", "overrides"}


def _is_object(value: Any) -> TypeGuard[JsonObject]:
    return isinstance(value, dict)


def _string_list(value: Any) -> list[str]:
    return [x for x in value if isinstance(x, str)] if isinstance(value, list) else []


def _merge_list(
    base: list[Json], overlay: list[Json], strategy: MergeStrategy | None
) -> list[Json]:
    if strategy is None or strategy.get("strategy") == "replace":
        return deepcopy(overlay)
    if strategy.get("strategy") == "append":
        return [*deepcopy(base), *deepcopy(overlay)]

    key = strategy.get("key")
    if key is None:
        return deepcopy(overlay)

    result = deepcopy(base)
    index: dict[Any, int] = {}
    for i, element in enumerate(result):
        if isinstance(element, dict) and key in element:
            index[element[key]] = i

    for element in overlay:
        if isinstance(element, dict) and key in element and element[key] in index:
            i = index[element[key]]
            target = result[i]
            if isinstance(target, dict):
                result[i] = merge(target, element, {})
        else:
            result.append(deepcopy(element))
    return result


def merge(acc: JsonObject, layer: JsonObject, strategies: MergeStrategies) -> JsonObject:
    result = deepcopy(acc)

    revert = _string_list(layer.get("$revert"))
    pre: dict[str, tuple[bool, Json]] = {}
    for field in revert:
        pre[field] = (field in result, deepcopy(result.get(field)))

    for key, value in layer.items():
        if key in STRUCTURAL or key.startswith("$"):
            continue
        current = result.get(key)
        if key not in result:
            result[key] = deepcopy(value)
        elif _is_object(current) and _is_object(value):
            result[key] = merge(current, value, strategies)
        elif isinstance(current, list) and isinstance(value, list):
            result[key] = _merge_list(current, value, strategies.get(key))
        else:
            result[key] = deepcopy(value)

    for field in _string_list(layer.get("$unset")):
        result.pop(field, None)

    for field in revert:
        present, value = pre[field]
        if present:
            result[field] = value
        else:
            result.pop(field, None)

    return result
