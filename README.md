<!--
SPDX-License-Identifier: CC-BY-4.0
-->

# mosvera

Python runtime for the language-neutral Mosvera specification.

The Python runtime loads aesthetic registries, resolves named compositions,
validates Mosvera schemas, applies merge and inheritance semantics, and
compiles neutral design tokens. It mirrors the `@mosvera/runtime`
TypeScript/JavaScript package against the shared conformance suite.

```bash
pip install mosvera
```

The package is published on PyPI as the Python peer runtime for the
language-neutral Mosvera spec.

## Basic Use

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

The runtime does not generate decks, HTML reports, images, or provider calls.
It supplies the structured aesthetic model that other tools can apply.

## Status

Phase 6E parity runtime. It is expected to pass the same 25 conformance vectors
as `@mosvera/runtime`.

## License

Code is Apache-2.0.
