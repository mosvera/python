# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from mosvera import (
    create_composition,
    create_modifier,
    create_template,
    create_validator,
    export_aesthetic_pack,
    import_aesthetic_pack,
    load_project,
    preview_aesthetic_pack_import,
    save_project_document,
    validate_aesthetic_pack,
)
from mosvera.types import AestheticPack, Registry


def make_pack(**overrides: object) -> AestheticPack:
    pack: AestheticPack = {
        "$schema": "https://mosvera.io/schema/0.1/aesthetic-pack",
        "kind": "mosvera.aesthetic_pack",
        "version": "0.1",
        "id": "executive-editorial",
        "entrypoint": {"kind": "composition", "id": "executive-editorial"},
        "documents": {
            "templates": {"base": create_template("base", {"tone": "neutral"})},
            "modifiers": {"warm": create_modifier("warm", {"tone": "warm"})},
            "compositions": {
                "executive-editorial": create_composition(
                    "executive-editorial", "base", modifiers=["warm"]
                )
            },
        },
    }
    pack.update(overrides)
    return pack


def test_validate_aesthetic_pack() -> None:
    assert validate_aesthetic_pack(make_pack(), create_validator()) == []


def test_pack_validation_rejects_bad_shape_and_unknown_references() -> None:
    bad_kind = {**make_pack(), "kind": "theme"}
    assert "schema_failure" in [
        diagnostic.code for diagnostic in validate_aesthetic_pack(bad_kind, create_validator())
    ]

    mismatch = make_pack(
        documents={
            "templates": {"base": create_template("not-base")},
            "compositions": {
                "executive-editorial": create_composition("executive-editorial", "missing")
            },
        }
    )
    codes = [
        diagnostic.code for diagnostic in validate_aesthetic_pack(mismatch, create_validator())
    ]
    assert "invalid_document" in codes
    assert "unknown_reference" in codes


def test_preview_and_import_auto_rename_rewrite_references() -> None:
    registry: Registry = {
        "templates": {"base": create_template("base", {"tone": "existing"})},
        "modifiers": {},
        "palettes": {},
        "compositions": {},
    }
    preview = preview_aesthetic_pack_import(make_pack(), registry, validator=create_validator())
    assert preview["valid"] is True
    assert preview["rename_map"]["template"]["base"] == "base-imported"

    result = import_aesthetic_pack(registry, make_pack(), validator=create_validator())
    assert result["plan"]["valid"] is True
    assert result["registry"]["templates"]["base"]["tone"] == "existing"
    assert result["registry"]["templates"]["base-imported"]["tone"] == "neutral"
    imported_base = result["pack"]["documents"]["compositions"]["executive-editorial"]["base"]
    assert imported_base == "base-imported"


def test_strategy_conflicts_default_to_failure() -> None:
    with_strategies = make_pack(merge_strategies={"tags": {"strategy": "append"}})
    preview = preview_aesthetic_pack_import(
        with_strategies,
        {},
        strategies={"tags": {"strategy": "replace"}},
    )
    assert preview["valid"] is False
    assert "strategy_conflict" in [diagnostic.code for diagnostic in preview["diagnostics"]]

    replace = preview_aesthetic_pack_import(
        with_strategies,
        {},
        strategies={"tags": {"strategy": "replace"}},
        strategy_conflict="replace",
    )
    assert replace["valid"] is True
    assert replace["merge_strategies"]["replace"] == ["tags"]


def test_export_and_reimport_pack_dependencies() -> None:
    registry: Registry = {
        "templates": {"base": create_template("base", {"components": [{"name": "card"}]})},
        "modifiers": {"warm": create_modifier("warm", {"tone": "warm"})},
        "palettes": {},
        "compositions": {
            "executive-editorial": create_composition(
                "executive-editorial", "base", modifiers=["warm"]
            )
        },
    }
    exported = export_aesthetic_pack(
        "executive-editorial",
        registry,
        strategies={"components": {"strategy": "merge_by", "key": "name"}},
    )
    assert exported["merge_strategies"] == {"components": {"strategy": "merge_by", "key": "name"}}

    result = import_aesthetic_pack({}, exported, validator=create_validator())
    assert result["plan"]["valid"] is True
    assert "executive-editorial" in result["registry"]["compositions"]
    assert validate_aesthetic_pack(result["pack"], create_validator()) == []


def test_project_loader_ignores_pack_files(tmp_path: Path) -> None:
    save_project_document(tmp_path, "template", create_template("base"), create_directory=True)
    (tmp_path / "executive-editorial.mosvera.json").write_text(
        '{"kind":"mosvera.aesthetic_pack","version":"0.1","id":"bad","entrypoint":{"kind":"composition","id":"bad"},"documents":{}}',
        encoding="utf8",
    )
    assert sorted(load_project(tmp_path).registry["templates"]) == ["base"]
