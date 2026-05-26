<!--
SPDX-License-Identifier: CC-BY-4.0
-->

# spec/schemas/

Normative JSON Schema definitions for Mosvera's aesthetic primitives.
Schemas are first-class peers of the prose specification: they are
machine-readable, language-agnostic, and embedded into conforming
runtimes.

## Conventions

- **Dialect:** [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema).
- **Field names** use `snake_case` per
  [ADR-0005](../docs/decisions/0005-schema-naming-conventions.md).
- **`$`-prefixed keys** are reserved for spec directives. JSON Schema's
  own keys (`$schema`, `$id`, `$ref`, `$defs`) and Mosvera's composition
  directives (`$extends` per MEP-0002; `$unset`, `$revert` per MEP-0001)
  share that namespace. User-defined field names MUST NOT begin with `$`,
  and unknown `$`-prefixed keys are rejected.
- **Allowed characters** in field names: `[a-z][a-z0-9_]*`. No
  hyphens, no uppercase, no dots.
- **`$id` scheme:** https rooted at the canonical domain —
  `https://mosvera.io/schema/0.1/<name>` (see
  [ADR-0014](../docs/decisions/0014-canonical-public-domain.md)). A stable
  namespace identifier; it need not be dereferenceable. Cross-schema
  references use these `$id`s.
- **License:** Apache-2.0 (schemas ship inside conforming runtimes
  and therefore use the code license, not the documentation license)
  per [ADR-0001](../docs/decisions/0001-license-choice.md).

## Schemas (v0.1)

| File | Encodes |
|------|---------|
| [`common.schema.json`](./common.schema.json) | Shared `$defs`: field-name pattern, reference, recursive `aesthetic_object` (with `$unset`/`$revert`), `merge_strategy` annotation, `criticality`, `lowering_action`. |
| [`composition.schema.json`](./composition.schema.json) | A use-site assembly: `base` + ordered `modifiers` + inline `overrides` (MEP-0001 precedence chain). |
| [`template.schema.json`](./template.schema.json) | A reusable aesthetic starting point; optional single-parent `$extends` (MEP-0002). |
| [`modifier.schema.json`](./modifier.schema.json) | A partial aesthetic delta deep-merged onto a base (MEP-0001). |
| [`palette.schema.json`](./palette.schema.json) | Semantic role → color value; DTCG-compat target per ADR-0006. |
| [`capability-manifest.schema.json`](./capability-manifest.schema.json) | A provider adapter's per-construct lowering-action declaration (MEP-0003). |

The **aesthetic vocabulary is intentionally open at v0.1** — templates and
modifiers constrain *structure and naming*, not the specific aesthetic fields
(`camera`, `lighting`, etc.). Freezing the vocabulary prematurely is exactly
what the MEPs warn against; it will firm up through the MEP process as concrete
examples exercise it.

## Status

Phase 1 (Specification Genesis). The six schemas above are present and
encode the three foundational MEPs (0001 composition, 0002 inheritance,
0003 provider compilation) plus ADR-0005 naming.

## Meta-schema check

Every published schema validates against the JSON Schema 2020-12
meta-schema. All six currently pass, along with positive/negative
document tests (a valid composition is accepted; malformed documents —
hyphenated fields, uppercase fields, unknown `$`-directives, missing
required fields — are rejected; and a capability manifest with an
`approximate` mapping lacking a documenting `note` is rejected per
MEP-0003). A standing CI hook for this check is pending the repo-plumbing
work.
