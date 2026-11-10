"""Gate 3: traceability from requirement to spec operation to test.

Every requirement must be linked to at least one operation (x-requirements in the spec) and
at least one test (@pytest.mark.req). Writes a traceability matrix to
gates/out/traceability.md so it can be attached to a review or the thesis."""
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEST_MARK = re.compile(r'@pytest\.mark\.req\("(REQ-\d+)"\)\s*\n(?:@[^\n]*\n)*def (test_\w+)')


def collect():
    reqs = yaml.safe_load((ROOT / "requirements" / "requirements.yaml").read_text(encoding="utf-8"))
    spec = yaml.safe_load((ROOT / "spec" / "openapi.yaml").read_text(encoding="utf-8"))

    operations = defaultdict(list)
    for item in spec["paths"].values():
        for op in item.values():
            for req in op.get("x-requirements", []):
                operations[req].append(op["operationId"])

    tests = defaultdict(list)
    for test_file in sorted((ROOT / "tests").glob("test_*.py")):
        for req, test_name in TEST_MARK.findall(test_file.read_text(encoding="utf-8")):
            tests[req].append(f"{test_file.stem}::{test_name}")
    return reqs["requirements"], operations, tests


def main():
    requirements, operations, tests = collect()
    known = {r["id"] for r in requirements}
    problems = []
    rows = ["| Requirement | Title | Operations | Tests |", "|---|---|---|---|"]
    for req in requirements:
        ops, tst = operations.get(req["id"], []), tests.get(req["id"], [])
        if not ops:
            problems.append(f"{req['id']}: not linked to any operation in the spec")
        if not tst:
            problems.append(f"{req['id']}: no test marked @pytest.mark.req(\"{req['id']}\")")
        rows.append(f"| {req['id']} | {req['title']} | {', '.join(ops) or '-'} | {len(tst)} |")
    for req in sorted(set(tests) - known):
        problems.append(f"tests refer to unknown requirement {req}")

    out = ROOT / "gates" / "out"
    out.mkdir(exist_ok=True)
    (out / "traceability.md").write_text("# Traceability matrix\n\n" + "\n".join(rows) + "\n",
                                         encoding="utf-8")
    print("\n".join(rows))
    for problem in problems:
        print(problem)
    print(f"trace_check: {'FAILED' if problems else 'passed'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
