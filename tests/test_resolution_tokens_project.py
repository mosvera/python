# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from mosvera import (
    RegistryProjectError,
    ResolutionError,
    compile_design_tokens,
    create_composition,
    create_modifier,
    create_template,
    delete_project_document,
    load_project,
    resolve_aesthetic,
    resolve_palette,
    save_project_document,
    to_css_variables,
    write_merge_strategies,
)


def test_palette_resolution_and_unknown_reference() -> None:
    registry = {
        "palettes": {
            "brand": {
                "id": "brand",
                "roles": {"background": "#fff", "accent": "#36f"},
            },
            "executive": {
                "id": "executive",
                "$extends": "brand",
                "roles": {"accent": "#74e", "highlight": "#fc5"},
            },
        }
    }
    assert resolve_palette("executive", registry, {}) == {
        "roles": {"background": "#fff", "accent": "#74e", "highlight": "#fc5"}
    }
    with pytest.raises(ResolutionError) as err:
        resolve_palette("missing", registry, {})
    assert err.value.kind == "unknown_reference"


def test_named_aesthetic_resolution_and_tokens() -> None:
    registry = {
        "templates": {"base_t": {"id": "base_t", "palette": {"accent": "#123"}}},
        "compositions": {
            "executive-editorial": create_composition("executive-editorial", "base_t")
        },
    }
    canonical = resolve_aesthetic("executive-editorial", registry, {})
    tokens = compile_design_tokens({**canonical, "provider_hint": "strict"})
    assert tokens["extensions"] == {"provider_hint": "strict"}
    assert to_css_variables(tokens)["--mosvera-palette-accent"] == "#123"


def test_project_load_save_delete_and_safety(tmp_path: Path) -> None:
    save_project_document(
        tmp_path,
        "template",
        create_template("base_t", {"z_value": 2, "a_value": 1}),
        create_directory=True,
    )
    save_project_document(tmp_path, "modifier", create_modifier("compact", {"density": "compact"}))
    save_project_document(
        tmp_path,
        "composition",
        create_composition("executive_editorial", "base_t", modifiers=["compact"]),
    )
    write_merge_strategies(tmp_path, {"tags": {"strategy": "append"}})

    template_body = (tmp_path / "template.base_t.json").read_text(encoding="utf8")
    assert template_body.index('"a_value"') < template_body.index('"z_value"')

    project = load_project(tmp_path)
    assert sorted(project.registry["templates"]) == ["base_t"]
    assert sorted(project.registry["modifiers"]) == ["compact"]
    assert sorted(project.registry["compositions"]) == ["executive_editorial"]
    assert project.strategies == {"tags": {"strategy": "append"}}

    (tmp_path / "template.yaml_t.yaml").write_text(
        "$schema: https://mosvera.io/schema/0.1/template\nid: yaml_t\ndensity: comfortable\n",
        encoding="utf8",
    )
    assert load_project(tmp_path).registry["templates"]["yaml_t"]["density"] == "comfortable"

    with pytest.raises(RegistryProjectError):
        save_project_document(tmp_path, "template", {"id": "../bad"})

    (tmp_path / ".template.bad.json").write_text('{"id":"bad"}', encoding="utf8")
    with pytest.raises(RegistryProjectError):
        load_project(tmp_path)

    (tmp_path / ".template.bad.json").unlink()
    delete_project_document(tmp_path, "template", "base_t")
    assert "base_t" not in load_project(tmp_path).registry["templates"]
