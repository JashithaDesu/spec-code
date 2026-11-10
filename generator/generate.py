"""Deterministic code generator: spec/openapi.yaml -> src/generated/.

The same spec always produces byte-identical files, so gates/check_generated.py can detect
generated code that was edited by hand or not regenerated after a spec change.

Usage:  python generator/generate.py [--out DIR]
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "spec" / "openapi.yaml"
TEMPLATES = Path(__file__).resolve().parent / "templates"
HTTP_METHODS = ("get", "post", "put", "patch", "delete")
SERVICE_CLASS = "VoucherService"


def snake_case(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def resolve(node, spec):
    """Replace every local $ref with a deep copy of what it points to."""
    if isinstance(node, dict):
        if "$ref" in node:
            target = spec
            for part in node["$ref"].lstrip("#/").split("/"):
                target = target[part]
            return resolve(copy.deepcopy(target), spec)
        return {key: resolve(value, spec) for key, value in node.items()}
    if isinstance(node, list):
        return [resolve(item, spec) for item in node]
    return node


def ref_name(schema_holder):
    """'#/components/schemas/Voucher' -> 'Voucher'. The spec gate requires refs, not inline schemas."""
    return schema_holder["$ref"].rsplit("/", 1)[-1]


def build_model(spec):
    operations = []
    for path, path_item in spec["paths"].items():
        for http_method in HTTP_METHODS:
            if http_method not in path_item:
                continue
            op = path_item[http_method]
            params = [resolve(p, spec) for p in op.get("parameters", [])]
            path_params = [
                {"name": p["name"], "py_name": snake_case(p["name"]), "schema": p["schema"]}
                for p in params if p["in"] == "path"
            ]
            body = op.get("requestBody", {}).get("content", {}).get("application/json")
            responses = []
            for status, response in sorted(op["responses"].items()):
                schema = response["content"]["application/json"]["schema"]
                responses.append((status, ref_name(schema)))
            operations.append({
                "operation_id": op["operationId"],
                "method_name": snake_case(op["operationId"]),
                "http_method": http_method,
                "path": path,
                "flask_path": re.sub(r"\{(\w+)\}", r"<\1>", path),
                "summary": op.get("summary", ""),
                "description": " ".join(op.get("description", "").split()),
                "requirements": op.get("x-requirements", []),
                "path_params": path_params,
                "request": ref_name(body["schema"]) if body else None,
                "responses": responses,
            })
    operations.sort(key=lambda o: o["operation_id"])

    schemas = {name: resolve(schema, spec) for name, schema in spec["components"]["schemas"].items()}
    operation_index = {
        op["operation_id"]: {
            "request": op["request"],
            "params": {p["name"]: p["schema"] for p in op["path_params"]},
            "responses": dict(op["responses"]),
        }
        for op in operations
    }
    return operations, schemas, operation_index


def generate(out_dir, spec_path=SPEC_PATH):
    spec_text = Path(spec_path).read_text(encoding="utf-8")
    spec = yaml.safe_load(spec_text)
    operations, schemas, operation_index = build_model(spec)

    digest = hashlib.sha256(spec_text.encode("utf-8")).hexdigest()[:16]
    header = ("# GENERATED FILE - DO NOT EDIT BY HAND.\n"
              f"# Source: spec/openapi.yaml (sha256 {digest}). Regenerate: python generator/generate.py")

    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    context = {
        "header": header,
        "spec_path": "spec/openapi.yaml",
        "service_class": SERVICE_CLASS,
        "operations": operations,
        "schemas_json": json.dumps(schemas, indent=2, sort_keys=True, ensure_ascii=False),
        "operations_json": json.dumps(operation_index, indent=2, sort_keys=True),
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "__init__.py": f"{header}\n",
        "schemas.py": env.get_template("schemas.py.j2").render(context),
        "service_base.py": env.get_template("service_base.py.j2").render(context),
        "routes.py": env.get_template("routes.py.j2").render(context),
    }
    for name, content in files.items():
        (out_dir / name).write_text(content, encoding="utf-8")
    return sorted(files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "src" / "generated"))
    args = parser.parse_args()
    written = generate(args.out)
    print(f"Generated {len(written)} files in {args.out}: {', '.join(written)}")
