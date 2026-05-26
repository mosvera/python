# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, TypedDict

Json: TypeAlias = Any
JsonObject: TypeAlias = dict[str, Any]
RegistryKind: TypeAlias = Literal["template", "modifier", "palette", "composition"]
DocumentKind: TypeAlias = Literal[
    "composition",
    "template",
    "modifier",
    "palette",
    "capability-manifest",
    "aesthetic-pack",
]
LoweringAction: TypeAlias = Literal["native", "approximate", "emulate", "unsupported"]
Criticality: TypeAlias = Literal["required", "optional"]
ResolutionErrorKind: TypeAlias = Literal[
    "inheritance_cycle",
    "reference_cycle",
    "unknown_reference",
    "multiple_inheritance_unsupported",
]
RegistryDiagnosticCode: TypeAlias = Literal[
    "unknown_reference",
    "invalid_document",
    "duplicate_id",
    "unsafe_filename",
    "schema_failure",
    "strategy_conflict",
]


class MergeStrategy(TypedDict, total=False):
    strategy: Literal["replace", "append", "merge_by"]
    key: str


MergeStrategies: TypeAlias = dict[str, MergeStrategy]
Registry: TypeAlias = dict[str, dict[str, JsonObject]]
CapabilityManifest: TypeAlias = dict[str, Any]
CompileResult: TypeAlias = dict[str, Any]
DesignTokens: TypeAlias = dict[str, Any]
CssVariableMap: TypeAlias = dict[str, str]
AestheticPack: TypeAlias = JsonObject
AestheticPackImportPlan: TypeAlias = dict[str, Any]
AestheticPackImportResult: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[ValidationIssue]


@dataclass(frozen=True)
class RegistryEntrySummary:
    kind: RegistryKind
    id: str
    extends: str | None = None
    base: str | None = None


@dataclass(frozen=True)
class RegistryReference:
    kind: RegistryKind
    id: str
    field: str


@dataclass(frozen=True)
class RegistryDiagnostic:
    code: RegistryDiagnosticCode
    message: str
    kind: RegistryKind | Literal["capability-manifest", "aesthetic-pack"] | None = None
    id: str | None = None
    path: str | None = None
    reference: RegistryReference | None = None
    errors: list[JsonObject] | None = None


@dataclass(frozen=True)
class LoadedProject:
    registry: Registry
    manifests: dict[str, CapabilityManifest]
    strategies: MergeStrategies
