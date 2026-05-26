# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .types import CapabilityManifest, CompileResult, Criticality, JsonObject


def compile_contract(
    canonical: JsonObject,
    manifest: CapabilityManifest,
    criticality: dict[str, Criticality] | None = None,
) -> CompileResult:
    crit = criticality or {}
    constructs = manifest.get("constructs", {})
    warnings: list[dict[str, str]] = []

    for name in sorted(canonical):
        entry = constructs.get(name, {}) if isinstance(constructs, dict) else {}
        action = (
            entry.get("lowering_action", "unsupported")
            if isinstance(entry, dict)
            else "unsupported"
        )
        required = crit.get(name, "optional")

        if action == "native":
            continue
        if action == "unsupported":
            if required == "required":
                return {"status": "error", "error": "required_unsupported", "construct": name}
            warnings.append({"construct": name, "action": "unsupported"})
        else:
            warnings.append({"construct": name, "action": action})

    return {"status": "compiled", "warnings": warnings}


compile = compile_contract
