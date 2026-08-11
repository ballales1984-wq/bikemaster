"""Generate TypeScript API types directly from Pydantic schemas."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import get_type_hints

REPO_ROOT = Path(__file__).resolve().parent.parent


def _to_pascal(name: str) -> str:
    parts = name.replace("-", "_").split("_")
    return "".join((p[0].upper() + p[1:]) if p else "" for p in parts)


def _py_type_to_ts(annotation) -> str:
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    if isinstance(annotation, str):
        annotation = annotation.replace("NoneType", "null")
        if annotation in {"int", "float"}:
            return "number"
        if annotation in {"str"}:
            return "string"
        if annotation in {"bool"}:
            return "boolean"
        if annotation.startswith("bike_analyzer.backend.models.models."):
            return _to_pascal(annotation.split(".")[-1])
        if annotation.startswith("bike_analyzer.core.models."):
            return _to_pascal(annotation.split(".")[-1])
        return annotation

    if origin is None:
        name = str(annotation).replace("NoneType", "null")
        if name.startswith("<class '") and name.endswith("'>"):
            name = name[8:-2]
        if name in {"int", "float"}:
            return "number"
        if name in {"str"}:
            return "string"
        if name in {"bool"}:
            return "boolean"
        if name in {"datetime.datetime", "datetime.date"}:
            return "string"
        if name.startswith("bike_analyzer.backend.models.models."):
            return _to_pascal(name.split(".")[-1])
        if name.startswith("bike_analyzer.core.models."):
            return _to_pascal(name.split(".")[-1])
        return name

    if origin is list:
        inner = _py_type_to_ts(args[0]) if args else "any"
        return f"{inner}[]"
    if origin is dict:
        key = _py_type_to_ts(args[0]) if args else "string"
        value = _py_type_to_ts(args[1]) if len(args) > 1 else "any"
        return f"Record<{key}, {value}>"
    if origin is not None and "Optional" in str(origin):
        inner = _py_type_to_ts(args[0]) if args else "any"
        return f"{inner} | null"

    return "any"


def _extract_schemas() -> dict[str, dict]:
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from bike_analyzer.backend.api import schemas as schemas_mod
    except Exception as exc:
        print(f"Failed to import schemas: {exc}")
        return {}

    schemas = {}
    for name in dir(schemas_mod):
        obj = getattr(schemas_mod, name)
        if not (isinstance(obj, type) and hasattr(obj, "model_fields")):
            continue

        try:
            hints = get_type_hints(obj)
            model_fields = getattr(obj, "model_fields", {})
            required_names = [k for k, v in model_fields.items() if getattr(v, "is_required", lambda: True)()]
            props = {}
            for field_name, hint in hints.items():
                if field_name in {"Config", "model_config"}:
                    continue
                ts_type = _py_type_to_ts(hint)
                props[field_name] = {
                    "ts_type": ts_type,
                    "required": field_name in required_names,
                }
            schemas[name] = props
        except Exception as exc:
            print(f"Skip schema {name}: {exc}")
    return schemas


def generate_types() -> str:
    schemas = _extract_schemas()
    if not schemas:
        return "// No Pydantic schemas extracted."

    lines = [
        "// Auto-generated from Pydantic schemas.",
        "// Do not edit manually.",
        "",
    ]
    for name, props in schemas.items():
        ts_name = _to_pascal(name)
        lines.append(f"export interface {ts_name} {{")
        for prop, meta in props.items():
            optional = "" if meta["required"] else "?"
            lines.append(f"  {prop}{optional}: {meta['ts_type']};")
        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    types = generate_types()
    out = REPO_ROOT / "frontend" / "src" / "types" / "api.generated.ts"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(types, encoding="utf-8")
    print(f"Wrote generated types to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



