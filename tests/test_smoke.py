# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from mosvera import (
    compile_design_tokens,
    create_composition,
    create_template,
    create_validator,
    export_aesthetic_pack,
    get_registry_document,
    import_aesthetic_pack,
    list_registry_entries,
    load_project,
    resolve_aesthetic,
    resolve_named_composition,
    save_project_document,
    to_css_variables,
    validate_aesthetic_pack,
    validate_registry,
)
from mosvera.types import JsonObject, LoadedProject


class DemoAesthetic(TypedDict):
    id: str
    base: str
    accent: str
    background: str
    density: str
    duration: str
    treatment: str
    headline: str


DEMO_AESTHETICS: list[DemoAesthetic] = [
    {
        "id": "quiet-editorial",
        "base": "quiet-editorial-base",
        "accent": "#bd5838",
        "background": "#f7f2e7",
        "density": "comfortable",
        "duration": "220ms",
        "treatment": "paper_field",
        "headline": "Aesthetic infrastructure you can inspect.",
    },
    {
        "id": "technical-manual",
        "base": "technical-manual-base",
        "accent": "#17745f",
        "background": "#f2f5f1",
        "density": "compact",
        "duration": "120ms",
        "treatment": "schematic",
        "headline": "Same site, compiled as a technical surface.",
    },
    {
        "id": "cinematic-lab",
        "base": "cinematic-lab-base",
        "accent": "#e05b45",
        "background": "#12100f",
        "density": "spacious",
        "duration": "320ms",
        "treatment": "spotlit",
        "headline": "The standard can carry drama without losing structure.",
    },
    {
        "id": "claymation-playful-builder",
        "base": "claymation-playful-builder-base",
        "accent": "#d45f3f",
        "background": "#f6e7cc",
        "density": "roomy",
        "duration": "260ms",
        "treatment": "tabletop_model",
        "headline": "Same architecture, built out of warm clay and shop light.",
    },
]


def demo_template(aesthetic: DemoAesthetic) -> JsonObject:
    return create_template(
        aesthetic["base"],
        {
            "imagery": {
                "src": f"/assets/aesthetics/hero-{aesthetic['id']}.webp",
                "treatment": aesthetic["treatment"],
            },
            "layout": {
                "density": aesthetic["density"],
                "radius": "8px",
            },
            "motion": {
                "duration": aesthetic["duration"],
            },
            "palette": {
                "accent": aesthetic["accent"],
                "background": aesthetic["background"],
            },
            "typography": {
                "body": "Hanken Grotesk",
                "display": "IBM Plex Mono" if aesthetic["id"] == "technical-manual" else "Fraunces",
            },
            "voice": {
                "headline": aesthetic["headline"],
            },
        },
    )


def seed_demo_project(directory: Path) -> LoadedProject:
    for aesthetic in DEMO_AESTHETICS:
        save_project_document(directory, "template", demo_template(aesthetic))
        save_project_document(
            directory,
            "composition",
            create_composition(aesthetic["id"], aesthetic["base"]),
        )
    return load_project(directory)


def test_loads_validates_and_lists_the_four_public_demo_aesthetics(tmp_path: Path) -> None:
    project = seed_demo_project(tmp_path)
    entries = list_registry_entries(project.registry, "composition")

    assert validate_registry(project.registry, create_validator()) == []
    assert [{"id": entry.id, "base": entry.base} for entry in entries] == [
        {"id": aesthetic["id"], "base": aesthetic["base"]}
        for aesthetic in sorted(DEMO_AESTHETICS, key=lambda item: item["id"])
    ]
    assert get_registry_document(project.registry, "composition", "quiet-editorial") == {
        "$schema": "https://mosvera.io/schema/0.1/composition",
        "id": "quiet-editorial",
        "base": "quiet-editorial-base",
    }


def test_resolves_named_aesthetic_and_compiles_portable_css_variables(tmp_path: Path) -> None:
    project = seed_demo_project(tmp_path)
    canonical = resolve_named_composition(
        "claymation-playful-builder",
        project.registry,
        project.strategies,
    )
    composition = project.registry["compositions"]["claymation-playful-builder"]

    assert resolve_aesthetic(composition, project.registry, project.strategies) == canonical

    css_variables = to_css_variables(compile_design_tokens(canonical))
    assert css_variables["--mosvera-palette-accent"] == "#d45f3f"
    assert css_variables["--mosvera-imagery-treatment"] == "tabletop_model"
    assert (
        css_variables["--mosvera-voice-headline"]
        == "Same architecture, built out of warm clay and shop light."
    )


def test_saves_reloads_exports_and_reimports_user_created_aesthetic(tmp_path: Path) -> None:
    seed_demo_project(tmp_path)
    smoke = create_composition(
        "smoke-test-editorial",
        "quiet-editorial-base",
        overrides={
            "palette": {"accent": "#475569"},
            "voice": {"headline": "Executive smoke test."},
        },
    )

    save_project_document(tmp_path, "composition", smoke)
    reloaded = load_project(tmp_path)
    assert "smoke-test-editorial" in [
        entry.id for entry in list_registry_entries(reloaded.registry, "composition")
    ]

    resolved = resolve_aesthetic("smoke-test-editorial", reloaded.registry, reloaded.strategies)
    css_variables = to_css_variables(compile_design_tokens(resolved))
    assert css_variables["--mosvera-palette-accent"] == "#475569"
    assert css_variables["--mosvera-voice-headline"] == "Executive smoke test."

    pack = export_aesthetic_pack(
        "smoke-test-editorial",
        reloaded.registry,
        name="Smoke Test Editorial",
    )
    assert validate_aesthetic_pack(pack, create_validator()) == []

    imported = import_aesthetic_pack(
        {"templates": {}, "modifiers": {}, "palettes": {}, "compositions": {}},
        pack,
        validator=create_validator(),
    )
    assert imported["plan"]["valid"] is True
    assert (
        resolve_aesthetic("smoke-test-editorial", imported["registry"], imported["strategies"])
        == resolved
    )
