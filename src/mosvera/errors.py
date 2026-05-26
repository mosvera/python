# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .types import RegistryDiagnostic, ResolutionErrorKind


class ResolutionError(Exception):
    def __init__(self, kind: ResolutionErrorKind, message: str | None = None) -> None:
        super().__init__(message or kind)
        self.kind = kind


class RegistryProjectError(Exception):
    def __init__(self, message: str, diagnostics: list[RegistryDiagnostic]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics
