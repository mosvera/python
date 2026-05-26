# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import asdict

from mosvera import (
    collect_references,
    compose_strategies,
    create_composition,
    create_modifier,
    create_palette,
    create_template,
    get_registry_document,
    list_registry_entries,
    merge,
    merge_registry,
    remove_registry_document,
    upsert_registry_document,
    validate_registry,
)


def test_merge_semantics() -> None:
    acc = {
        "a": 1,
        "obj": {"x": 1, "y": 1},
        "tags": [{"name": "a", "value": 1}],
        "gone": True,
    }
    layer = {
        "obj": {"y": 2},
        "tags": [{"name": "a", "value": 2}, {"name": "b", "value": 3}],
        "$unset": ["gone"],
    }
    assert merge(acc, layer, {"tags": {"strategy": "merge_by", "key": "name"}}) == {
        "a": 1,
        "obj": {"x": 1, "y": 2},
        "tags": [{"name": "a", "value": 2}, {"name": "b", "value": 3}],
    }


def test_registry_helpers_are_copy_based() -> None:
    registry = {
        "templates": {"base_t": create_template("base_t", {"density": "comfortable"})},
        "modifiers": {"compact": create_modifier("compact", {"density": "compact"})},
        "palettes": {"brand": create_palette("brand", {"accent": "#3366ff"})},
        "compositions": {
            "executive_editorial": create_composition(
                "executive_editorial",
                "base_t",
                modifiers=["compact"],
            )
        },
    }

    assert [asdict(entry) for entry in list_registry_entries(registry)] == [
        {"kind": "template", "id": "base_t", "extends": None, "base": None},
        {"kind": "modifier", "id": "compact", "extends": None, "base": None},
        {"kind": "palette", "id": "brand", "extends": None, "base": None},
        {"kind": "composition", "id": "executive_editorial", "extends": None, "base": "base_t"},
    ]

    doc = get_registry_document(registry, "template", "base_t")
    assert doc == registry["templates"]["base_t"]
    assert doc is not registry["templates"]["base_t"]

    merged = merge_registry(
        registry, {"compositions": {"expressive": create_composition("expressive", "base_t")}}
    )
    assert sorted(merged["compositions"]) == ["executive_editorial", "expressive"]

    added = upsert_registry_document(
        registry, "modifier", create_modifier("warm", {"tone": "warm"})
    )
    assert "warm" in added["modifiers"]
    assert "warm" not in registry["modifiers"]
    removed = remove_registry_document(added, "modifier", "warm")
    assert "warm" not in removed["modifiers"]


def test_collect_references_and_validate_registry() -> None:
    composition = create_composition("broken", "missing_t", modifiers=["ghost"])
    assert collect_references(composition, "composition") == [
        collect_references(composition, "composition")[0],
        collect_references(composition, "composition")[1],
    ]
    diagnostics = validate_registry({"compositions": {"broken": composition}})
    assert [diagnostic.code for diagnostic in diagnostics] == [
        "unknown_reference",
        "unknown_reference",
    ]


def test_compose_strategies_later_wins() -> None:
    assert compose_strategies(
        {"tags": {"strategy": "replace"}}, {"tags": {"strategy": "append"}}
    ) == {"tags": {"strategy": "append"}}
