"""Gate 4: static guardrails for the business logic (src/logic/service.py).

AI-written code is checked against these rules before any test runs:
  G1  VoucherService subclasses the generated VoucherServiceBase
  G2  every method of the generated interface is implemented
  G3  only allow-listed modules are imported (no file, network or process access)
  G4  no eval/exec/open/__import__/print
  G5  a status code returned directly by a method, e.g. `return 404, {...}`,
      must be declared for that operation in the spec

Usage: python gates/check_guardrails.py [path/to/service.py]
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.generated.schemas import OPERATIONS  # noqa: E402

ALLOWED_IMPORTS = {"uuid", "secrets", "threading", "dataclasses", "typing", "copy", "datetime", "time",
                   "src.generated.service_base", "__future__"}
FORBIDDEN_CALLS = {"eval", "exec", "open", "__import__", "print", "compile"}


def snake_case(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def check(source):
    tree = ast.parse(source)
    problems = []
    statuses = {snake_case(op_id): set(op["responses"]) for op_id, op in OPERATIONS.items()}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            names = []
        for name in names:
            if name not in ALLOWED_IMPORTS:
                problems.append(f"G3 line {node.lineno}: import of '{name}' is not allowed")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            problems.append(f"G4 line {node.lineno}: call to {node.func.id}() is not allowed")

    service = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "VoucherService"), None)
    if service is None:
        return problems + ["G1: class VoucherService not found"]
    if "VoucherServiceBase" not in [getattr(b, "id", getattr(b, "attr", "")) for b in service.bases]:
        problems.append("G1: VoucherService must subclass VoucherServiceBase")

    methods = {n.name: n for n in service.body if isinstance(n, ast.FunctionDef)}
    for name in sorted(statuses):
        if name not in methods:
            problems.append(f"G2: method {name}() is not implemented")

    for name, func in methods.items():
        if name not in statuses:
            continue
        for node in ast.walk(func):
            if (isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) and node.value.elts
                    and isinstance(node.value.elts[0], ast.Constant)
                    and isinstance(node.value.elts[0].value, int)):
                status = str(node.value.elts[0].value)
                if status not in statuses[name]:
                    problems.append(f"G5 line {node.lineno}: {name}() returns {status}, "
                                    f"spec allows {sorted(statuses[name])}")
    return problems


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "src" / "logic" / "service.py"
    problems = check(path.read_text(encoding="utf-8"))
    for problem in problems:
        print(problem)
    print(f"check_guardrails: {'FAILED' if problems else 'passed'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
