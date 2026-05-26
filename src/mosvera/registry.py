# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import re
from copy import deepcopy
from typing import cast

from .types import (
    DocumentKind,
    JsonObject,
    MergeStrategies,
    Registry,
    RegistryDiagnostic,
    RegistryEntrySummary,
    RegistryKind,
    RegistryReference,
)
from .validator import Validator

SCHEMA_BY_KIND: dict[RegistryKind, str] = {
    "template": "https://mosvera.io/schema/0.1/template",
    "modifier": "https://mosvera.io/schema/0.1/modifier",
    "palette": "https://mosvera.io/schema/0.1/palette",
    "composition": "https://mosvera.io/schema/0.1/composition",
}

COLLECTION_BY_KIND: dict[RegistryKind, str] = {
    "template": "templates",
    "modifier": "modifiers",
    "palette": "palettes",
    "composition": "compositions",
}

KINDS: tuple[RegistryKind, ...] = ("template", "modifier", "palette", "composition")
REFERENCE_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def _assert_reference(id: str) -> None:
    if REFERENCE_RE.fullmatch(id) is None:
        raise ValueError(f'invalid Mosvera reference id "{id}"')


def _collection(registry: Registry, kind: RegistryKind) -> dict[str, JsonObject]:
    return registry.get(COLLECTION_BY_KIND[kind], {})


def _doc_id(doc: JsonObject) -> str | None:
    doc_id = doc.get("id")
    return doc_id if isinstance(doc_id, str) else None


def _schema_doc(kind: RegistryKind, id: str, values: JsonObject) -> JsonObject:
    _assert_reference(id)
    return {"$schema": SCHEMA_BY_KIND[kind], "id": id, **deepcopy(values)}


def create_template(id: str, values: JsonObject | None = None) -> JsonObject:
    return _schema_doc("template", id, values or {})


def create_modifier(id: str, values: JsonObject | None = None) -> JsonObject:
    return _schema_doc("modifier", id, values or {})


def create_palette(
    id: str,
    roles: dict[str, str] | None = None,
    values: JsonObject | None = None,
) -> JsonObject:
    doc_values = deepcopy(values or {})
    doc_values["roles"] = deepcopy(roles or {})
    return _schema_doc("palette", id, doc_values)


def create_composition(
    id: str,
    base: str,
    modifiers: list[str] | None = None,
    overrides: JsonObject | None = None,
) -> JsonObject:
    _assert_reference(id)
    _assert_reference(base)
    out: JsonObject = {"$schema": SCHEMA_BY_KIND["composition"], "id": id, "base": base}
    if modifiers is not None:
        out["modifiers"] = deepcopy(modifiers)
    if overrides is not None:
        out["overrides"] = deepcopy(overrides)
    return out


def list_registry_entries(
    registry: Registry,
    kind: RegistryKind | None = None,
) -> list[RegistryEntrySummary]:
    kinds = KINDS if kind is None else (kind,)
    out: list[RegistryEntrySummary] = []
    for current_kind in kinds:
        for id, doc in sorted(_collection(registry, current_kind).items()):
            parent = doc.get("$extends")
            base = doc.get("base")
            out.append(
                RegistryEntrySummary(
                    kind=current_kind,
                    id=id,
                    extends=parent if isinstance(parent, str) else None,
                    base=base if current_kind == "composition" and isinstance(base, str) else None,
                )
            )
    return out


def get_registry_document(registry: Registry, kind: RegistryKind, id: str) -> JsonObject | None:
    doc = _collection(registry, kind).get(id)
    return deepcopy(doc) if doc is not None else None


def merge_registry(base: Registry, overlay: Registry | None) -> Registry:
    overlay = overlay or {}
    return {
        "templates": {**base.get("templates", {}), **overlay.get("templates", {})},
        "modifiers": {**base.get("modifiers", {}), **overlay.get("modifiers", {})},
        "palettes": {**base.get("palettes", {}), **overlay.get("palettes", {})},
        "compositions": {**base.get("compositions", {}), **overlay.get("compositions", {})},
    }


def compose_strategies(*layers: MergeStrategies | None) -> MergeStrategies:
    out: MergeStrategies = {}
    for layer in layers:
        if layer is not None:
            out.update(layer)
    return out


def upsert_registry_document(
    registry: Registry, kind: RegistryKind, document: JsonObject
) -> Registry:
    doc_id = _doc_id(document)
    if doc_id is None:
        raise ValueError(f"{kind} document is missing a string id")
    _assert_reference(doc_id)
    next_registry = merge_registry(registry, None)
    collection = dict(next_registry.get(COLLECTION_BY_KIND[kind], {}))
    collection[doc_id] = deepcopy(document)
    next_registry[COLLECTION_BY_KIND[kind]] = collection
    return next_registry


def remove_registry_document(registry: Registry, kind: RegistryKind, id: str) -> Registry:
    _assert_reference(id)
    next_registry = merge_registry(registry, None)
    collection = dict(next_registry.get(COLLECTION_BY_KIND[kind], {}))
    collection.pop(id, None)
    next_registry[COLLECTION_BY_KIND[kind]] = collection
    return next_registry


def collect_references(doc: JsonObject, kind: RegistryKind) -> list[RegistryReference]:
    refs: list[RegistryReference] = []
    if kind in {"template", "palette"}:
        parent = doc.get("$extends")
        if isinstance(parent, str):
            refs.append(RegistryReference(kind=kind, id=parent, field="$extends"))
    if kind == "composition":
        base = doc.get("base")
        if isinstance(base, str):
            refs.append(RegistryReference(kind="template", id=base, field="base"))
        modifiers = doc.get("modifiers")
        if isinstance(modifiers, list):
            for modifier in modifiers:
                if isinstance(modifier, str):
                    refs.append(RegistryReference(kind="modifier", id=modifier, field="modifiers"))
    return refs


def validate_registry(
    registry: Registry, validator: Validator | None = None
) -> list[RegistryDiagnostic]:
    diagnostics: list[RegistryDiagnostic] = []
    for kind in KINDS:
        docs = _collection(registry, kind)
        for id, doc in docs.items():
            actual = _doc_id(doc)
            if actual != id:
                actual_label = actual or "<missing>"
                diagnostics.append(
                    RegistryDiagnostic(
                        code="invalid_document",
                        kind=kind,
                        id=id,
                        message=(
                            f'{kind} registry key "{id}" does not match '
                            f'document id "{actual_label}"'
                        ),
                    )
                )
            if validator is not None:
                result = validator.validate(doc, cast(DocumentKind, kind))
                if not result.valid:
                    diagnostics.append(
                        RegistryDiagnostic(
                            code="schema_failure",
                            kind=kind,
                            id=id,
                            message=f'{kind} "{id}" failed schema validation',
                            errors=[
                                {"path": issue.path, "message": issue.message}
                                for issue in result.errors
                            ],
                        )
                    )
            for ref in collect_references(doc, kind):
                if ref.id not in _collection(registry, ref.kind):
                    diagnostics.append(
                        RegistryDiagnostic(
                            code="unknown_reference",
                            kind=kind,
                            id=id,
                            reference=ref,
                            message=(
                                f'{kind} "{id}" references missing {ref.kind} '
                                f'"{ref.id}" via {ref.field}'
                            ),
                        )
                    )
    return diagnostics
