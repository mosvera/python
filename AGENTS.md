# Agent Guidance

This repo is the Python peer runtime for Mosvera. It should match the
language-neutral spec and the shared compliance semantics, while using Pythonic
helpers around plain dictionary wire documents.

## Safety Rules

- Do not commit secrets, `.env*`, local config, vault references, generated
  media, caches, private notes, or local machine paths.
- Preserve unrelated user changes and keep edits narrow.
- Use DCO-signed commits when committing.
- Do not publish packages, rotate credentials, change repo visibility, or
  trigger releases unless explicitly asked.

## Repo Boundaries

- Preserve plain `dict` document models and Mosvera wire field names.
- Keep TypeScript runtime parity where the spec defines shared behavior.
- Do not add MCP server behavior, provider HTTP calls, artifact generation, or
  hosted-service assumptions here.

## Verification

- Run `ruff check`, `ruff format --check`, `mypy`, and `pytest`.
- Run `python -m build` when packaging metadata or shipped files change.
- Run `git diff --check` before committing.
