<!--
SPDX-License-Identifier: CC-BY-4.0
-->

# spec/compliance/

Conformance test vectors for Mosvera.
[ADR-0007](../docs/decisions/0007-reference-runtime-language.md)
makes language-portable conformance a requirement: every conforming
runtime — TypeScript reference, Python committed port, and any
future-language community implementation — must pass the suite here.

## Format

Each conformance case is a JSON document conforming to
[`vector.schema.json`](./vector.schema.json). There are two kinds:

**`resolution`** — exercises MEP-0001 (composition) and MEP-0002
(inheritance):

- `registry` — named templates/modifiers/palettes/compositions available for
  reference resolution.
- `merge_strategies` — per-field list-merge strategy (`replace` /
  `append` / `merge_by`); schema-declared in real runtimes, carried
  inline in the vector.
- `input` + `input_kind` — the composition, template, palette, or named
  composition reference to resolve.
- `expect` — either `{ canonical: … }` (the expected resolved
  aesthetic model) or `{ status: "error", error: … }`.

**`compilation`** — exercises MEP-0003 (provider compilation):

- `manifest` — a provider capability manifest.
- `canonical` — the already-resolved composition to compile.
- `criticality` — per-construct `required`/`optional`.
- `expect` — `{ status: "compiled", warnings: [...] }` or
  `{ status: "error", error: "required_unsupported", construct: … }`.

The **canonical model** is the merge of each precedence layer's
*aesthetic content* — the structural/identity keys (`id`, `$schema`,
`$extends`, `base`, `modifiers`, `overrides`) are not aesthetic
content and do not appear in it. Compilation vectors assert the
contract *outcome* (compile vs error, and the warning set), not exact
provider payloads — exact payloads embody adapter-specific rendering
and are golden-tested with the reference adapters.

Runtimes consume these JSON cases directly. There is no host-language
code in this directory — the entire suite is the language-neutral
contract that makes Mosvera implementations substitutable.

## Layout

| Directory | Vectors |
|-----------|---------|
| [`resolution/`](./resolution/) | MEP-0001 merge/precedence + MEP-0002 inheritance (0001–0016, 0022–0025) |
| [`compilation/`](./compilation/) | MEP-0003 compilation contract outcomes (0017–0021) |

## Status

Phase 6D. 25 vectors present, covering the
normative behaviors of all three foundational MEPs: deep/scalar/
type-mismatch merge, the three list strategies, `$unset`/`$revert`,
the precedence chain, single inheritance + multi-level chains, the
inheritance/composition seam, `$revert` and `merge_by` across the
inheritance boundary, inheritance-cycle and multiple-inheritance
rejection, palette inheritance, named composition lookup,
missing-reference taxonomy, and the full compilation criticality ×
lowering-action rule table.

Each vector was verified during authoring against an independent
reference oracle (the expected output recomputed and matched), the
vector meta-schema, and the Mosvera primitive schemas. The Phase 2
TypeScript runtime will be the first committed implementation checked
against this suite.

## Why this exists

The runtime architecture is required to keep semantic logic
separable from host-language idioms so that the eventual Python
port (and any community-language implementations) are translations
rather than rewrites. Conformance cases are the testable contract
that proves the abstraction holds across languages — preventing the
single-language reference runtime from quietly becoming
TypeScript-shaped semantics that other languages can only
approximate.

See
[ADR-0007](../docs/decisions/0007-reference-runtime-language.md)
for the full rationale.
