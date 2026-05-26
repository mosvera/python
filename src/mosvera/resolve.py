# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .errors import ResolutionError
from .merge import merge
from .types import JsonObject, MergeStrategies, Registry


def _collection(registry: Registry, name: str) -> dict[str, JsonObject]:
    return registry.get(name, {})


def resolve_template(
    doc: JsonObject, registry: Registry, strategies: MergeStrategies
) -> JsonObject:
    templates = _collection(registry, "templates")
    chain: list[JsonObject] = []
    seen: set[str] = set()

    current: JsonObject | None = doc
    while current is not None:
        doc_id = current.get("id")
        if isinstance(doc_id, str):
            if doc_id in seen:
                raise ResolutionError("inheritance_cycle")
            seen.add(doc_id)
        chain.append(current)

        parent = current.get("$extends")
        if parent is None:
            break
        if isinstance(parent, list):
            raise ResolutionError("multiple_inheritance_unsupported")
        if not isinstance(parent, str):
            raise ResolutionError("inheritance_cycle")

        next_doc = templates.get(parent)
        if next_doc is None:
            raise ResolutionError("unknown_reference")
        current = next_doc

    acc: JsonObject = {}
    for layer in reversed(chain):
        acc = merge(acc, layer, strategies)
    return acc


def resolve_palette(
    palette_or_id: JsonObject | str,
    registry: Registry,
    strategies: MergeStrategies,
) -> JsonObject:
    palettes = _collection(registry, "palettes")
    first = palettes.get(palette_or_id) if isinstance(palette_or_id, str) else palette_or_id
    if first is None:
        raise ResolutionError("unknown_reference")

    chain: list[JsonObject] = []
    seen: set[str] = set()

    current: JsonObject | None = first
    while current is not None:
        doc_id = current.get("id")
        if isinstance(doc_id, str):
            if doc_id in seen:
                raise ResolutionError("inheritance_cycle")
            seen.add(doc_id)
        chain.append(current)

        parent = current.get("$extends")
        if parent is None:
            break
        if isinstance(parent, list):
            raise ResolutionError("multiple_inheritance_unsupported")
        if not isinstance(parent, str):
            raise ResolutionError("inheritance_cycle")

        next_doc = palettes.get(parent)
        if next_doc is None:
            raise ResolutionError("unknown_reference")
        current = next_doc

    acc: JsonObject = {}
    for layer in reversed(chain):
        acc = merge(acc, layer, strategies)
    return acc


def resolve_composition(
    composition: JsonObject,
    registry: Registry,
    strategies: MergeStrategies,
) -> JsonObject:
    templates = _collection(registry, "templates")
    modifiers = _collection(registry, "modifiers")

    base_name = composition.get("base")
    if not isinstance(base_name, str):
        raise ResolutionError("unknown_reference")
    base_doc = templates.get(base_name)
    if base_doc is None:
        raise ResolutionError("unknown_reference")

    acc = merge({}, resolve_template(base_doc, registry, strategies), strategies)

    modifier_refs = composition.get("modifiers")
    if isinstance(modifier_refs, list):
        for ref in modifier_refs:
            if not isinstance(ref, str):
                raise ResolutionError("unknown_reference")
            modifier = modifiers.get(ref)
            if modifier is None:
                raise ResolutionError("unknown_reference")
            acc = merge(acc, modifier, strategies)

    overrides = composition.get("overrides")
    if isinstance(overrides, dict):
        acc = merge(acc, overrides, strategies)

    return acc


def resolve_named_composition(
    id: str,
    registry: Registry,
    strategies: MergeStrategies,
) -> JsonObject:
    composition = registry.get("compositions", {}).get(id)
    if composition is None:
        raise ResolutionError("unknown_reference")
    return resolve_composition(composition, registry, strategies)


def resolve_aesthetic(
    composition_or_id: JsonObject | str,
    registry: Registry,
    strategies: MergeStrategies,
) -> JsonObject:
    if isinstance(composition_or_id, str):
        return resolve_named_composition(composition_or_id, registry, strategies)
    return resolve_composition(composition_or_id, registry, strategies)
