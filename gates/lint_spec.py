"""Gate 1: the spec follows the project's rules before any code is generated.

These are house rules on top of standard OpenAPI validity (CI also runs Spectral):
  R1  every operation has a camelCase operationId, a summary and x-requirements
  R2  every x-requirements id exists in requirements/requirements.yaml
  R3  request and response bodies use $ref to a named schema (no inline schemas)
  R4  every 4xx/5xx response uses the shared Error schema
  R5  every object schema sets additionalProperties: false and lists required fields
  R6  every named schema has a description
  R7  every request body has an example that is valid against its schema
"""
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from generator.generate import resolve  # noqa: E402

HTTP_METHODS = ("get", "post", "put", "patch", "delete")


def lint(spec, requirement_ids):
    problems = []
    for path, item in spec.get("paths", {}).items():
        for method in HTTP_METHODS:
            if method not in item:
                continue
            op, where = item[method], f"{method.upper()} {path}"
            op_id = op.get("operationId", "")
            if not re.fullmatch(r"[a-z][a-zA-Z0-9]*", op_id):
                problems.append(f"R1 {where}: operationId missing or not camelCase")
            if not op.get("summary"):
                problems.append(f"R1 {where}: summary missing")
            reqs = op.get("x-requirements") or []
            if not reqs:
                problems.append(f"R1 {where}: x-requirements missing")
            for req in reqs:
                if req not in requirement_ids:
                    problems.append(f"R2 {where}: unknown requirement {req}")

            body = op.get("requestBody", {}).get("content", {}).get("application/json")
            if body:
                if "$ref" not in body.get("schema", {}):
                    problems.append(f"R3 {where}: request body schema must be a $ref")
                elif "example" not in body:
                    problems.append(f"R7 {where}: request body has no example")
                else:
                    schema = resolve(body["schema"], spec)
                    for error in Draft202012Validator(schema).iter_errors(body["example"]):
                        problems.append(f"R7 {where}: example is invalid: {error.message}")

            for status, response in op.get("responses", {}).items():
                schema = response.get("content", {}).get("application/json", {}).get("schema", {})
                if "$ref" not in schema:
                    problems.append(f"R3 {where} {status}: response schema must be a $ref")
                elif status[0] in "45" and not schema["$ref"].endswith("/Error"):
                    problems.append(f"R4 {where} {status}: error responses must use Error")

    for name, schema in spec.get("components", {}).get("schemas", {}).items():
        if not schema.get("description"):
            problems.append(f"R6 schema {name}: description missing")
        if schema.get("type") == "object":
            if schema.get("additionalProperties") is not False:
                problems.append(f"R5 schema {name}: additionalProperties must be false")
            if not schema.get("required"):
                problems.append(f"R5 schema {name}: required list missing")
    return problems


def main():
    spec = yaml.safe_load((ROOT / "spec" / "openapi.yaml").read_text(encoding="utf-8"))
    reqs = yaml.safe_load((ROOT / "requirements" / "requirements.yaml").read_text(encoding="utf-8"))
    problems = lint(spec, {r["id"] for r in reqs["requirements"]})
    for problem in problems:
        print(problem)
    print(f"lint_spec: {'FAILED' if problems else 'passed'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
