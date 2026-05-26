# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Literal, cast

from .errors import ResolutionError
from .registry import (
    collect_references,
    get_registry_document,
    upsert_registry_document,
    validate_registry,
)
from .types import (
    AestheticPack,
    AestheticPackImportPlan,
    AestheticPackImportResult,
    Json,
    JsonObject,
    MergeStrategies,
    Registry,
    RegistryDiagnostic,
    RegistryDiagnosticCode,
    RegistryKind,
    RegistryReference,
)
from .validator import Validator

PACK_SCHEMA = "https://mosvera.io/schema/0.1/aesthetic-pack"
PACK_KIND = "mosvera.aesthetic_pack"
PACK_VERSION = "0.1"
KINDS: tuple[RegistryKind, ...] = ("template", "palette", "modifier", "composition")
COLLECTION_BY_KIND: dict[RegistryKind, str] = {
    "template": "templates",
    "palette": "palettes",
    "modifier": "modifiers",
    "composition": "compositions",
}
STRUCTURAL_KEYS = {
    "$schema",
    "$extends",
    "$unset",
    "$revert",
    "id",
    "base",
    "modifiers",
    "overrides",
}


def _collection(registry: Registry | None, kind: RegistryKind) -> dict[str, JsonObject]:
    if registry is None:
        return {}
    return registry.get(COLLECTION_BY_KIND[kind], {})


def _entries(registry: Registry | None, kind: RegistryKind) -> list[tuple[str, JsonObject]]:
    return sorted(_collection(registry, kind).items())


def _empty_registry() -> Registry:
    return {"templates": {}, "palettes": {}, "modifiers": {}, "compositions": {}}


def _empty_rename_map() -> dict[RegistryKind, dict[str, str]]:
    return {"template": {}, "palette": {}, "modifier": {}, "composition": {}}


def _doc_id(doc: JsonObject) -> str | None:
    doc_id = doc.get("id")
    return doc_id if isinstance(doc_id, str) else None


def _pack_id(pack: object) -> str:
    if isinstance(pack, dict) and isinstance(pack.get("id"), str):
        return cast(str, pack["id"])
    return "<invalid>"


def _diagnostic(
    code: RegistryDiagnosticCode,
    message: str,
    *,
    kind: RegistryKind | Literal["capability-manifest", "aesthetic-pack"] | None = None,
    id: str | None = None,
    path: str | None = None,
    reference: RegistryReference | None = None,
    errors: list[JsonObject] | None = None,
) -> RegistryDiagnostic:
    return RegistryDiagnostic(
        code=code,
        message=message,
        kind=kind,
        id=id,
        path=path,
        reference=reference,
        errors=errors,
    )


def _as_pack(pack: object) -> AestheticPack | None:
    if not isinstance(pack, dict):
        return None
    if pack.get("kind") != PACK_KIND or pack.get("version") != PACK_VERSION:
        return None
    if not isinstance(pack.get("id"), str):
        return None
    entrypoint = pack.get("entrypoint")
    if not (
        isinstance(entrypoint, dict)
        and entrypoint.get("kind") == "composition"
        and isinstance(entrypoint.get("id"), str)
    ):
        return None
    if not isinstance(pack.get("documents"), dict):
        return None
    return cast(AestheticPack, pack)


def _validate_pack_shape(pack: object, validator: Validator | None) -> list[RegistryDiagnostic]:
    if validator is None:
        return []
    result = validator.validate(pack, "aesthetic-pack")
    if result.valid:
        return []
    return [
        _diagnostic(
            "schema_failure",
            "aesthetic pack failed schema validation",
            kind="aesthetic-pack",
            id=_pack_id(pack),
            errors=[{"path": issue.path, "message": issue.message} for issue in result.errors],
        )
    ]


def _validate_document_keys(pack: AestheticPack) -> list[RegistryDiagnostic]:
    diagnostics: list[RegistryDiagnostic] = []
    documents = cast(Registry, pack["documents"])
    for kind in KINDS:
        seen: set[str] = set()
        for key, doc in _entries(documents, kind):
            actual = _doc_id(doc)
            if actual != key:
                actual_label = actual or "<missing>"
                diagnostics.append(
                    _diagnostic(
                        "invalid_document",
                        f'{kind} pack key "{key}" does not match document id "{actual_label}"',
                        kind=kind,
                        id=key,
                        path=f"/documents/{COLLECTION_BY_KIND[kind]}/{key}",
                    )
                )
            if actual is not None:
                if actual in seen:
                    diagnostics.append(
                        _diagnostic(
                            "duplicate_id",
                            f'duplicate {kind} id "{actual}" in aesthetic pack',
                            kind=kind,
                            id=actual,
                            path=f"/documents/{COLLECTION_BY_KIND[kind]}/{key}",
                        )
                    )
                seen.add(actual)
    return diagnostics


def _merged_for_reference_checks(pack: AestheticPack) -> Registry:
    documents = cast(Registry, pack["documents"])
    return {
        "templates": {**documents.get("templates", {})},
        "palettes": {**documents.get("palettes", {})},
        "modifiers": {**documents.get("modifiers", {})},
        "compositions": {**documents.get("compositions", {})},
    }


def _dedupe(diagnostics: list[RegistryDiagnostic]) -> list[RegistryDiagnostic]:
    seen: set[str] = set()
    out: list[RegistryDiagnostic] = []
    for diagnostic in diagnostics:
        key = json.dumps(asdict(diagnostic), sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            out.append(diagnostic)
    return out


def validate_aesthetic_pack(
    pack: object,
    validator: Validator | None = None,
) -> list[RegistryDiagnostic]:
    diagnostics = _validate_pack_shape(pack, validator)
    typed = _as_pack(pack)
    if typed is None:
        return diagnostics

    documents = cast(Registry, typed["documents"])
    diagnostics.extend(_validate_document_keys(typed))
    entrypoint = cast(dict[str, str], typed["entrypoint"])
    entrypoint_id = entrypoint["id"]
    if entrypoint_id not in _collection(documents, "composition"):
        diagnostics.append(
            _diagnostic(
                "unknown_reference",
                f'aesthetic pack entrypoint composition "{entrypoint_id}" was not found',
                kind="aesthetic-pack",
                id=cast(str, typed["id"]),
                reference=RegistryReference(
                    kind="composition",
                    id=entrypoint_id,
                    field="entrypoint",
                ),
            )
        )

    diagnostics.extend(validate_registry(documents, validator))
    merged = _merged_for_reference_checks(typed)
    for kind in KINDS:
        for id, doc in _entries(documents, kind):
            for ref in collect_references(doc, kind):
                if ref.id not in _collection(merged, ref.kind):
                    message = (
                        f'{kind} "{id}" references missing {ref.kind} "{ref.id}" via {ref.field}'
                    )
                    diagnostics.append(
                        _diagnostic(
                            "unknown_reference",
                            message,
                            kind=kind,
                            id=id,
                            reference=ref,
                        )
                    )

    return _dedupe(diagnostics)


def _stable_stringify(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _next_available_id(
    kind: RegistryKind,
    id: str,
    registry: Registry,
    reserved: dict[RegistryKind, set[str]],
) -> str:
    if id not in _collection(registry, kind) and id not in reserved[kind]:
        return id
    candidate = f"{id}-imported"
    index = 2
    while candidate in _collection(registry, kind) or candidate in reserved[kind]:
        candidate = f"{id}-imported-{index}"
        index += 1
    return candidate


def _plan_strategies(
    pack: AestheticPack,
    existing: MergeStrategies | None,
    strategy_conflict: Literal["fail", "replace"],
    diagnostics: list[RegistryDiagnostic],
) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"add": [], "replace": [], "conflicts": []}
    strategies = cast(MergeStrategies, pack.get("merge_strategies", {}))
    for key, strategy in sorted(strategies.items()):
        current = existing.get(key) if existing is not None else None
        if current is None:
            out["add"].append(key)
        elif _stable_stringify(current) != _stable_stringify(strategy):
            if strategy_conflict == "replace":
                out["replace"].append(key)
            else:
                out["conflicts"].append(key)
                diagnostics.append(
                    _diagnostic(
                        "strategy_conflict",
                        f'merge strategy "{key}" conflicts with the active registry',
                        kind="aesthetic-pack",
                        id=cast(str, pack["id"]),
                        path=f"/merge_strategies/{key}",
                    )
                )
    return out


def preview_aesthetic_pack_import(
    pack: AestheticPack,
    registry: Registry,
    *,
    validator: Validator | None = None,
    strategies: MergeStrategies | None = None,
    conflict_strategy: Literal["auto_rename", "fail", "replace"] = "auto_rename",
    strategy_conflict: Literal["fail", "replace"] = "fail",
) -> AestheticPackImportPlan:
    diagnostics = validate_aesthetic_pack(pack, validator)
    typed = _as_pack(pack)
    rename_map = _empty_rename_map()
    operations: list[dict[str, str]] = []

    if typed is not None:
        documents = cast(Registry, typed["documents"])
        reserved: dict[RegistryKind, set[str]] = {
            "template": set(),
            "palette": set(),
            "modifier": set(),
            "composition": set(),
        }
        for kind in KINDS:
            for id, _doc in _entries(documents, kind):
                target = (
                    _next_available_id(kind, id, registry, reserved)
                    if conflict_strategy == "auto_rename"
                    else id
                )
                rename_map[kind][id] = target
                reserved[kind].add(target)
                exists = id in _collection(registry, kind)
                if exists and conflict_strategy == "fail":
                    diagnostics.append(
                        _diagnostic(
                            "duplicate_id",
                            f'{kind} "{id}" already exists in the active registry',
                            kind=kind,
                            id=id,
                        )
                    )
                action = "rename" if target != id else "replace" if exists else "add"
                operations.append({"kind": kind, "original_id": id, "id": target, "action": action})

    merge_strategies = (
        {"add": [], "replace": [], "conflicts": []}
        if typed is None
        else _plan_strategies(typed, strategies, strategy_conflict, diagnostics)
    )
    entrypoint = (
        cast(dict[str, str], typed["entrypoint"])
        if typed is not None
        else {"kind": "composition", "id": "<invalid>"}
    )
    installed_entrypoint = {
        "kind": "composition",
        "id": rename_map["composition"].get(entrypoint["id"], entrypoint["id"]),
    }
    return {
        "valid": len(diagnostics) == 0,
        "pack_id": cast(str, typed["id"]) if typed is not None else _pack_id(pack),
        "entrypoint": dict(entrypoint),
        "installed_entrypoint": installed_entrypoint,
        "operations": operations,
        "rename_map": rename_map,
        "merge_strategies": merge_strategies,
        "diagnostics": diagnostics,
    }


def _rewrite_document(
    kind: RegistryKind,
    doc: JsonObject,
    id: str,
    rename_map: dict[RegistryKind, dict[str, str]],
) -> JsonObject:
    out = deepcopy(doc)
    out["id"] = id
    parent = out.get("$extends")
    if kind in {"template", "palette"} and isinstance(parent, str):
        out["$extends"] = rename_map[kind].get(parent, parent)
    if kind == "composition":
        base = out.get("base")
        if isinstance(base, str):
            out["base"] = rename_map["template"].get(base, base)
        modifiers = out.get("modifiers")
        if isinstance(modifiers, list):
            out["modifiers"] = [
                rename_map["modifier"].get(ref, ref) if isinstance(ref, str) else ref
                for ref in modifiers
            ]
    return out


def _rewritten_pack(pack: AestheticPack, plan: AestheticPackImportPlan) -> AestheticPack:
    documents = cast(Registry, pack["documents"])
    rename_map = cast(dict[RegistryKind, dict[str, str]], plan["rename_map"])
    out_docs = _empty_registry()
    for kind in KINDS:
        collection: dict[str, JsonObject] = {}
        for id, doc in _entries(documents, kind):
            next_id = rename_map[kind].get(id, id)
            collection[next_id] = _rewrite_document(kind, doc, next_id, rename_map)
        out_docs[COLLECTION_BY_KIND[kind]] = collection

    next_pack: AestheticPack = {
        "$schema": pack.get("$schema", PACK_SCHEMA),
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "id": pack["id"],
        "entrypoint": plan["installed_entrypoint"],
        "documents": out_docs,
    }
    if "name" in pack:
        next_pack["name"] = pack["name"]
    if "description" in pack:
        next_pack["description"] = pack["description"]
    if "merge_strategies" in pack:
        next_pack["merge_strategies"] = deepcopy(pack["merge_strategies"])
    return next_pack


def import_aesthetic_pack(
    registry: Registry,
    pack: AestheticPack,
    *,
    validator: Validator | None = None,
    strategies: MergeStrategies | None = None,
    conflict_strategy: Literal["auto_rename", "fail", "replace"] = "auto_rename",
    strategy_conflict: Literal["fail", "replace"] = "fail",
) -> AestheticPackImportResult:
    plan = preview_aesthetic_pack_import(
        pack,
        registry,
        validator=validator,
        strategies=strategies,
        conflict_strategy=conflict_strategy,
        strategy_conflict=strategy_conflict,
    )
    base_strategies = deepcopy(strategies or {})
    if not plan["valid"]:
        return {
            "registry": deepcopy(registry),
            "strategies": base_strategies,
            "pack": deepcopy(pack),
            "plan": plan,
        }

    installed = _rewritten_pack(pack, plan)
    next_registry = deepcopy(registry)
    documents = cast(Registry, installed["documents"])
    for kind in KINDS:
        for _id, doc in _entries(documents, kind):
            next_registry = upsert_registry_document(next_registry, kind, doc)

    next_strategies = deepcopy(base_strategies)
    pack_strategies = cast(MergeStrategies, pack.get("merge_strategies", {}))
    merge_plan = cast(dict[str, list[str]], plan["merge_strategies"])
    for key in [*merge_plan["add"], *merge_plan["replace"]]:
        if key in pack_strategies:
            next_strategies[key] = deepcopy(pack_strategies[key])

    return {
        "registry": next_registry,
        "strategies": next_strategies,
        "pack": installed,
        "plan": plan,
    }


def _add_dependency(out: Registry, registry: Registry, kind: RegistryKind, id: str) -> JsonObject:
    existing = _collection(out, kind).get(id)
    if existing is not None:
        return existing
    doc = get_registry_document(registry, kind, id)
    if doc is None:
        raise ResolutionError("unknown_reference")
    out[COLLECTION_BY_KIND[kind]][id] = doc
    return doc


def _collect_template_dependencies(
    out: Registry,
    registry: Registry,
    id: str,
    seen: set[str],
) -> None:
    if id in seen:
        return
    seen.add(id)
    doc = _add_dependency(out, registry, "template", id)
    parent = doc.get("$extends")
    if isinstance(parent, str):
        _collect_template_dependencies(out, registry, parent, seen)


def collect_aesthetic_pack_dependencies(id: str, registry: Registry) -> Registry:
    out = _empty_registry()
    composition = _add_dependency(out, registry, "composition", id)
    base = composition.get("base")
    if not isinstance(base, str):
        raise ResolutionError("unknown_reference")
    _collect_template_dependencies(out, registry, base, set())
    modifiers = composition.get("modifiers")
    if isinstance(modifiers, list):
        for modifier in modifiers:
            if not isinstance(modifier, str):
                raise ResolutionError("unknown_reference")
            _add_dependency(out, registry, "modifier", modifier)
    return out


def _sorted_registry(registry: Registry) -> Registry:
    out = _empty_registry()
    for kind in KINDS:
        out[COLLECTION_BY_KIND[kind]] = dict(_entries(registry, kind))
    return out


def _collect_strategy_fields(value: Json, out: set[str]) -> None:
    if isinstance(value, list):
        for child in value:
            _collect_strategy_fields(child, out)
        return
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if key not in STRUCTURAL_KEYS and isinstance(child, list):
            out.add(key)
        if not key.startswith("$"):
            _collect_strategy_fields(child, out)


def _exported_strategies(
    registry: Registry,
    strategies: MergeStrategies | None,
) -> MergeStrategies | None:
    if strategies is None:
        return None
    fields: set[str] = set()
    for kind in KINDS:
        for _id, doc in _entries(registry, kind):
            _collect_strategy_fields(doc, fields)
    out: MergeStrategies = {}
    for field in sorted(fields):
        if field in strategies:
            out[field] = deepcopy(strategies[field])
    return out or None


def export_aesthetic_pack(
    entrypoint_id: str,
    registry: Registry,
    *,
    id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    strategies: MergeStrategies | None = None,
) -> AestheticPack:
    documents = _sorted_registry(collect_aesthetic_pack_dependencies(entrypoint_id, registry))
    pack: AestheticPack = {
        "$schema": PACK_SCHEMA,
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "id": id or entrypoint_id,
        "entrypoint": {"kind": "composition", "id": entrypoint_id},
        "documents": documents,
    }
    if name is not None:
        pack["name"] = name
    if description is not None:
        pack["description"] = description
    merge_strategies = _exported_strategies(documents, strategies)
    if merge_strategies is not None:
        pack["merge_strategies"] = merge_strategies
    return pack
