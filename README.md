<!--
SPDX-License-Identifier: CC-BY-4.0
-->

# mosvera

Python runtime for the language-neutral Mosvera specification.

The Python runtime loads local aesthetic registries, resolves named
aesthetics from composition documents, validates Mosvera schemas, applies
merge and inheritance semantics, and compiles neutral design tokens. It
mirrors the `@mosvera/runtime` TypeScript/JavaScript package against the
shared conformance suite.

```bash
pip install mosvera
```

New users should start with the
[`10-minute quickstart`](https://github.com/mosvera/spec/blob/main/docs/guides/10-minute-quickstart.md),
which includes a Python runtime smoke after the Claude Desktop and MCP paths.

The package is published on PyPI as the Python peer runtime for the
language-neutral Mosvera spec.

## Basic Use

Load a registry, resolve a named aesthetic, and compile CSS variables:

```python
from mosvera import (
    compile_design_tokens,
    compose_strategies,
    derive_strategies,
    load_project,
    resolve_aesthetic,
    to_css_variables,
)

project = load_project("./my-aesthetic-system")
strategies = compose_strategies(derive_strategies(), project.strategies)

canonical = resolve_aesthetic("executive-editorial", project.registry, strategies)
tokens = compile_design_tokens(canonical)
css_variables = to_css_variables(tokens)
```

Save a new composition document into a local registry:

```python
from mosvera import create_composition, save_project_document

composition = create_composition(
    "executive-editorial",
    "base_t",
    modifiers=["executive", "editorial"],
    overrides={"voice": {"headline": "Board-ready and concise."}},
)

save_project_document("./my-aesthetic-system", "composition", composition)
```

Exchange a named aesthetic as a portable pack:

```python
from mosvera import export_aesthetic_pack, import_aesthetic_pack

pack = export_aesthetic_pack("executive-editorial", project.registry)
imported = import_aesthetic_pack(project.registry, pack)
print(imported["plan"]["installed_entrypoint"]["id"])
```

The runtime does not generate decks, HTML reports, images, or provider calls.
It supplies the structured aesthetic model that other tools can apply.

## Status

Phase 6G complete. The runtime passes the same 25 conformance vectors as
`@mosvera/runtime`; the full Python suite currently covers parser,
validator, registry, pack, resolution, token, project persistence, and smoke
paths.

## License

Code is Apache-2.0.
