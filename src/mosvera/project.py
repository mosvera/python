# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Literal, cast

from .errors import RegistryProjectError
from .parser import parse
from .types import (
    DocumentKind,
    JsonObject,
    LoadedProject,
    MergeStrategies,
    Registry,
    RegistryDiagnostic,
    RegistryDiagnosticCode,
    RegistryKind,
    RegistryReference,
)
from .validator import Validator, create_validator

DOC_EXT_RE = re.compile(r"\.(json|ya?ml)$", re.IGNORECASE)
SAFE_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")

ID_TO_KIND: dict[str, DocumentKind] = {
    "https://mosvera.io/schema/0.1/template": "template",
    "https://mosvera.io/schema/0.1/modifier": "modifier",
    "https://mosvera.io/schema/0.1/palette": "palette",
    "https://mosvera.io/schema/0.1/composition": "composition",
    "https://mosvera.io/schema/0.1/capability-manifest": "capability-manifest",
}


def _classify(doc: JsonObject, file: str) -> DocumentKind:
    schema_id = doc.get("$schema")
    if isinstance(schema_id, str) and schema_id in ID_TO_KIND:
        return ID_TO_KIND[schema_id]
    if re.search(r"(^|/)template\.", file):
        return "template"
    if re.search(r"(^|/)modifier\.", file):
        return "modifier"
    if re.search(r"(^|/)palette\.", file):
        return "palette"
    if re.search(r"(^|/)composition\.", file):
        return "composition"
    if re.search(r"\.manifest\.(json|ya?ml)$", file, re.IGNORECASE):
        return "capability-manifest"
    raise ValueError(f'cannot classify document "{file}"')


DiagnosticKind = RegistryKind | Literal["capability-manifest"]


def _diagnostic(
    code: RegistryDiagnosticCode,
    message: str,
    kind: DiagnosticKind | None = None,
    id: str | None = None,
    path: str | None = None,
    reference: RegistryReference | None = None,
    errors: list[JsonObject] | None = None,
) -> RegistryDiagnostic:
    return RegistryDiagnostic(
        code=code,
        message=message,
        kind=kind,
        id=id,
        path=path,
        reference=reference,
        errors=errors,
    )


def _ensure_safe_file(file: str, path_for_message: str) -> None:
    if file.startswith(".") or "/" in file or "\\" in file or Path(file).is_absolute():
        raise RegistryProjectError(
            f'unsafe registry filename "{path_for_message}"',
            [
                _diagnostic(
                    "unsafe_filename",
                    f'unsafe registry filename "{path_for_message}"',
                    path=path_for_message,
                )
            ],
        )


def _ensure_safe_id(id: str) -> None:
    if SAFE_ID_RE.fullmatch(id) is None:
        raise RegistryProjectError(
            f'unsafe registry id "{id}"',
            [
                _diagnostic(
                    "unsafe_filename",
                    f'registry id "{id}" is not a valid Mosvera reference id',
                    id=id,
                )
            ],
        )


def _read_doc(path: Path) -> JsonObject:
    return parse(path.read_text(encoding="utf8"))


def _validate_or_throw(
    validator: Validator, doc: JsonObject, kind: DocumentKind, file: str
) -> None:
    result = validator.validate(doc, kind)
    if result.valid:
        return
    raise RegistryProjectError(
        f'invalid {kind} document "{file}"',
        [
            _diagnostic(
                "schema_failure",
                f'invalid {kind} document "{file}"',
                kind=kind,
                path=file,
                errors=[{"path": issue.path, "message": issue.message} for issue in result.errors],
            )
        ],
    )


def _require_id(doc: JsonObject, kind: RegistryKind, path_for_message: str) -> str:
    doc_id = doc.get("id")
    if not isinstance(doc_id, str):
        raise RegistryProjectError(
            f'{kind} document "{path_for_message}" is missing a string id',
            [
                _diagnostic(
                    "invalid_document",
                    f'{kind} document "{path_for_message}" is missing a string id',
                    kind=kind,
                    path=path_for_message,
                )
            ],
        )
    _ensure_safe_id(doc_id)
    return doc_id


def _provider_id(doc: JsonObject, path_for_message: str) -> str:
    provider = doc.get("provider")
    if not isinstance(provider, str):
        raise RegistryProjectError(
            f'manifest "{path_for_message}" is missing provider',
            [
                _diagnostic(
                    "invalid_document",
                    f'manifest "{path_for_message}" is missing provider',
                    kind="capability-manifest",
                    path=path_for_message,
                )
            ],
        )
    _ensure_safe_id(provider)
    return provider


def _registry_collection(registry: Registry, kind: RegistryKind) -> dict[str, JsonObject]:
    key = {
        "template": "templates",
        "modifier": "modifiers",
        "palette": "palettes",
        "composition": "compositions",
    }[kind]
    return registry.setdefault(key, {})


def _load_doc_file(
    root: Path,
    rel_file: str,
    validator: Validator,
    project: LoadedProject,
    diagnostics: list[RegistryDiagnostic],
) -> None:
    _ensure_safe_file(Path(rel_file).name, rel_file)
    doc = _read_doc(root / rel_file)
    kind = _classify(doc, rel_file)
    _validate_or_throw(validator, doc, kind, rel_file)

    if kind == "capability-manifest":
        provider = _provider_id(doc, rel_file)
        if provider in project.manifests:
            diagnostics.append(
                _diagnostic(
                    "duplicate_id",
                    (
                        f'duplicate capability manifest provider "{provider}" '
                        f'while loading "{rel_file}"'
                    ),
                    kind="capability-manifest",
                    id=provider,
                    path=rel_file,
                )
            )
        project.manifests[provider] = doc
        return

    collection = _registry_collection(project.registry, kind)
    doc_id = _require_id(doc, kind, rel_file)
    if doc_id in collection:
        diagnostics.append(
            _diagnostic(
                "duplicate_id",
                f'duplicate {kind} id "{doc_id}" while loading "{rel_file}"',
                kind=kind,
                id=doc_id,
                path=rel_file,
            )
        )
    collection[doc_id] = doc


def load_project(directory: str | Path, validator: Validator | None = None) -> LoadedProject:
    active_validator = validator or create_validator()
    root = Path(directory).resolve()
    strategies: MergeStrategies = {}
    strategy_path = root / "merge-strategies.json"
    if strategy_path.exists():
        strategies = cast(MergeStrategies, _read_doc(strategy_path))

    project = LoadedProject(
        registry={"templates": {}, "modifiers": {}, "palettes": {}, "compositions": {}},
        manifests={},
        strategies=strategies,
    )
    diagnostics: list[RegistryDiagnostic] = []

    for entry in root.iterdir():
        if (
            entry.is_file()
            and DOC_EXT_RE.search(entry.name)
            and entry.name != "merge-strategies.json"
        ):
            _load_doc_file(root, entry.name, active_validator, project, diagnostics)

    manifests_dir = root / "manifests"
    if manifests_dir.exists():
        for entry in manifests_dir.iterdir():
            if entry.is_file() and DOC_EXT_RE.search(entry.name):
                _load_doc_file(
                    root,
                    str(Path("manifests") / entry.name),
                    active_validator,
                    project,
                    diagnostics,
                )

    if diagnostics:
        raise RegistryProjectError("registry project contains duplicate ids", diagnostics)
    return project


def _stable_stringify(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _file_name(kind: RegistryKind, id: str) -> str:
    return f"{kind}.{id}.json"


def _assert_within(root: Path, target: Path) -> None:
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RegistryProjectError(
            f"path escapes registry root: {target}",
            [
                _diagnostic(
                    "unsafe_filename", f"path escapes registry root: {target}", path=str(target)
                )
            ],
        ) from exc


def _atomic_write(path: Path, body: str) -> None:
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp.write_text(body, encoding="utf8")
    os.replace(temp, path)


def save_project_document(
    directory: str | Path,
    kind: RegistryKind,
    document: JsonObject,
    validator: Validator | None = None,
    create_directory: bool = False,
) -> None:
    active_validator = validator or create_validator()
    doc_id = _require_id(document, kind, f"{kind}.{document.get('id', '<missing>')}.json")
    root = Path(directory).resolve()
    if create_directory:
        root.mkdir(parents=True, exist_ok=True)
    path = root / _file_name(kind, doc_id)
    _assert_within(root, path)
    _validate_or_throw(active_validator, document, kind, path.name)
    _atomic_write(path, _stable_stringify(document))


def delete_project_document(directory: str | Path, kind: RegistryKind, id: str) -> None:
    _ensure_safe_id(id)
    root = Path(directory).resolve()
    path = root / _file_name(kind, id)
    _assert_within(root, path)
    if path.exists():
        path.unlink()


def write_merge_strategies(
    directory: str | Path,
    strategies: MergeStrategies,
    create_directory: bool = False,
) -> None:
    root = Path(directory).resolve()
    if create_directory:
        root.mkdir(parents=True, exist_ok=True)
    path = root / "merge-strategies.json"
    _assert_within(root, path)
    _atomic_write(path, _stable_stringify(strategies))
