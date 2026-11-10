"""Tests for the pipeline itself: generator, gates and the AI loop helpers.

Kept outside tests/ so they are not counted as acceptance tests.
Run with: python -m pytest tooling_tests"""
import copy
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.fill_logic import extract_code  # noqa: E402
from gates.check_guardrails import check as check_guardrails  # noqa: E402
from gates.lint_spec import lint  # noqa: E402
from generator.generate import generate  # noqa: E402

SPEC = yaml.safe_load((ROOT / "spec" / "openapi.yaml").read_text(encoding="utf-8"))
REQS = {r["id"] for r in yaml.safe_load(
    (ROOT / "requirements" / "requirements.yaml").read_text(encoding="utf-8"))["requirements"]}

GOOD_LOGIC = '''
from src.generated.service_base import VoucherServiceBase

class VoucherService(VoucherServiceBase):
    def issue_voucher(self, body):
        return 201, {}
    def get_voucher(self, voucher_id):
        return 404, {"code": "VOUCHER_NOT_FOUND", "message": "no"}
    def redeem_voucher(self, voucher_id, body):
        return 409, {"code": "INSUFFICIENT_BALANCE", "message": "no"}
'''


# ---------- generator ----------

def test_generator_is_deterministic(tmp_path):
    generate(tmp_path / "a")
    generate(tmp_path / "b")
    for f in (tmp_path / "a").iterdir():
        assert f.read_text() == (tmp_path / "b" / f.name).read_text()


def test_committed_generated_code_matches_the_spec(tmp_path):
    for name in generate(tmp_path):
        assert (tmp_path / name).read_text() == (ROOT / "src" / "generated" / name).read_text(), name


# ---------- lint_spec ----------

def test_the_real_spec_passes_lint():
    assert lint(SPEC, REQS) == []


def _mutate(edit):
    spec = copy.deepcopy(SPEC)
    edit(spec)
    return lint(spec, REQS)


@pytest.mark.parametrize("rule, edit", [
    ("R1", lambda s: s["paths"]["/vouchers"]["post"].pop("operationId")),
    ("R1", lambda s: s["paths"]["/vouchers"]["post"].pop("x-requirements")),
    ("R2", lambda s: s["paths"]["/vouchers"]["post"].__setitem__("x-requirements", ["REQ-999"])),
    ("R3", lambda s: s["paths"]["/vouchers"]["post"]["responses"]["201"]["content"]["application/json"]
       .__setitem__("schema", {"type": "object"})),
    ("R4", lambda s: s["paths"]["/vouchers"]["post"]["responses"]["422"]["content"]["application/json"]
       .__setitem__("schema", {"$ref": "#/components/schemas/Voucher"})),
    ("R5", lambda s: s["components"]["schemas"]["Voucher"].pop("additionalProperties")),
    ("R6", lambda s: s["components"]["schemas"]["Voucher"].pop("description")),
    ("R7", lambda s: s["paths"]["/vouchers"]["post"]["requestBody"]["content"]["application/json"]
       .__setitem__("example", {"amount": 0, "currency": "SEK"})),
])
def test_lint_catches_rule_violations(rule, edit):
    problems = _mutate(edit)
    assert any(p.startswith(rule) for p in problems), problems


# ---------- check_guardrails ----------

def test_good_logic_passes_guardrails():
    assert check_guardrails(GOOD_LOGIC) == []


@pytest.mark.parametrize("rule, source", [
    ("G1", GOOD_LOGIC.replace("VoucherService(VoucherServiceBase)", "VoucherService(object)")),
    ("G2", GOOD_LOGIC.replace("def get_voucher", "def lookup")),
    ("G3", "import os\n" + GOOD_LOGIC),
    ("G3", "import requests\n" + GOOD_LOGIC),
    ("G4", GOOD_LOGIC.replace("return 201, {}", "print('hi')\n        return 201, {}")),
    ("G5", GOOD_LOGIC.replace("return 409,", "return 400,")),
    ("G5", GOOD_LOGIC.replace("return 201, {}", "return 200, {}")),
])
def test_guardrails_catch_violations(rule, source):
    problems = check_guardrails(source)
    assert any(p.startswith(rule) for p in problems), problems


# ---------- AI loop helpers ----------

def test_extract_code_takes_the_first_python_block():
    reply = "Sure!\n```python\nx = 1\n```\nand also\n```python\ny = 2\n```"
    assert extract_code(reply) == "x = 1\n"


def test_extract_code_falls_back_to_the_whole_reply():
    assert extract_code("x = 1") == "x = 1\n"
