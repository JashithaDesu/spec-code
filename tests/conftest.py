"""Shared fixtures. Choose the implementation under test with the TARGET variable:

    python -m pytest tests                    # spec-driven (src/), the default
    TARGET=codefirst python -m pytest tests   # code-first (code_first/)
"""
import importlib
import os
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generator.generate import resolve  # noqa: E402  (tooling only, not the generated code)

TARGETS = {"spec": "src.app", "codefirst": "code_first.app"}


def pytest_configure(config):
    config.addinivalue_line("markers", "req(id): links a test to a requirement in requirements.yaml")


@pytest.fixture
def client():
    target = os.environ.get("TARGET", "spec")
    module = importlib.import_module(TARGETS[target])
    app = module.create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(scope="session")
def spec():
    return yaml.safe_load((ROOT / "spec" / "openapi.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def schema(spec):
    """schema("Voucher") -> the fully resolved JSON Schema from the spec."""
    return lambda name: resolve(spec["components"]["schemas"][name], spec)


def issue(client, amount=50000, currency="SEK"):
    response = client.post("/vouchers", json={"amount": amount, "currency": currency})
    assert response.status_code == 201, response.get_data(as_text=True)
    return response.get_json()


def redeem(client, voucher_id, amount, key="order-0001"):
    return client.post(f"/vouchers/{voucher_id}/redemptions",
                       json={"amount": amount, "idempotencyKey": key})
