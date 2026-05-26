# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

from .types import DocumentKind, ValidationIssue, ValidationResult

SCHEMA_FILES = [
    "common.schema.json",
    "composition.schema.json",
    "template.schema.json",
    "modifier.schema.json",
    "palette.schema.json",
    "capability-manifest.schema.json",
    "aesthetic-pack.schema.json",
]

KIND_TO_ID: dict[DocumentKind, str] = {
    "composition": "https://mosvera.io/schema/0.1/composition",
    "template": "https://mosvera.io/schema/0.1/template",
    "modifier": "https://mosvera.io/schema/0.1/modifier",
    "palette": "https://mosvera.io/schema/0.1/palette",
    "capability-manifest": "https://mosvera.io/schema/0.1/capability-manifest",
    "aesthetic-pack": "https://mosvera.io/schema/0.1/aesthetic-pack",
}


class Validator(Protocol):
    def validate(self, doc: object, kind: DocumentKind) -> ValidationResult: ...


class JsonSchemaValidator:
    def __init__(self, schema_dir: str | Path | None = None) -> None:
        base = Path(schema_dir) if schema_dir is not None else Path(__file__).parent / "schemas"
        self._schemas: dict[str, Mapping[str, Any]] = {}
        for name in SCHEMA_FILES:
            schema = cast(Mapping[str, Any], json.loads((base / name).read_text(encoding="utf8")))
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str):
                raise ValueError(f"{name} is missing $id")
            self._schemas[schema_id] = schema

        store = dict(self._schemas)
        self._validators: dict[DocumentKind, Draft202012Validator] = {}
        for kind, schema_id in KIND_TO_ID.items():
            schema = self._schemas[schema_id]
            resolver = RefResolver.from_schema(schema, store=store)
            self._validators[kind] = Draft202012Validator(schema, resolver=resolver)

    def validate(self, doc: object, kind: DocumentKind) -> ValidationResult:
        validator = self._validators[kind]
        errors = sorted(validator.iter_errors(doc), key=lambda err: list(err.path))
        if not errors:
            return ValidationResult(valid=True, errors=[])

        issues: list[ValidationIssue] = []
        for error in errors:
            path = "".join(f"/{part}" for part in error.absolute_path)
            message_path = path or "(root)"
            issues.append(
                ValidationIssue(path=path, message=f"{message_path} {error.message}".strip())
            )
        return ValidationResult(valid=False, errors=issues)


def create_validator(schema_dir: str | Path | None = None) -> Validator:
    return JsonSchemaValidator(schema_dir)
