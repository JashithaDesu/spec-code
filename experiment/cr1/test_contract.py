"""Contract consistency: every response must use a status code declared in the spec and a
body that matches the spec's schema exactly.

For the spec-driven implementation the generated routes already enforce this at runtime.
For the code-first implementation this test is how consistency with the agreed interface
is measured, which is one of the metrics in experiment/PROTOCOL.md.

CR-1 version: also exercises the 410 response for an expired voucher (REQ-009)."""
import time
from datetime import datetime, timedelta, timezone

import pytest
from jsonschema import Draft202012Validator

from tests.conftest import issue, redeem


def _declared(spec, path, method, status):
    responses = spec["paths"][path][method]["responses"]
    assert str(status) in responses, f"{method.upper()} {path} returned undeclared status {status}"
    return responses[str(status)]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]


def _scenario(client):
    """Exercise every declared response of every operation once."""
    calls = []

    def record(path, method, response):
        calls.append((path, method, response))
        return response

    record("/vouchers", "post", client.post("/vouchers", json={"amount": 1000, "currency": "SEK"}))
    voucher_id = calls[-1][2].get_json()["id"]
    record("/vouchers", "post", client.post("/vouchers", json={"amount": 0, "currency": "SEK"}))

    record("/vouchers/{voucherId}", "get", client.get(f"/vouchers/{voucher_id}"))
    record("/vouchers/{voucherId}", "get", client.get("/vouchers/missing"))
    record("/vouchers/{voucherId}", "get", client.get("/vouchers/" + "x" * 65))

    path = "/vouchers/{voucherId}/redemptions"
    record(path, "post", redeem(client, voucher_id, 400, key="order-0001"))
    record(path, "post", redeem(client, voucher_id, 400, key="order-0001"))
    record(path, "post", redeem(client, voucher_id, 5000, key="order-0002"))
    record(path, "post", redeem(client, voucher_id, 600, key="order-0003"))
    record(path, "post", redeem(client, voucher_id, 1, key="order-0004"))
    record(path, "post", redeem(client, "missing", 1))
    record(path, "post", client.post(f"/vouchers/{voucher_id}/redemptions", json={"amount": 1}))

    expires = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=1)
    record("/vouchers", "post", client.post("/vouchers", json={
        "amount": 1000, "currency": "SEK", "expiresAt": expires.strftime("%Y-%m-%dT%H:%M:%SZ")}))
    expiring_id = calls[-1][2].get_json()["id"]
    time.sleep(max(0.0, (expires - datetime.now(timezone.utc)).total_seconds()) + 1.1)
    record("/vouchers/{voucherId}", "get", client.get(f"/vouchers/{expiring_id}"))
    record(path, "post", redeem(client, expiring_id, 1, key="order-0005"))
    return calls


@pytest.mark.req("REQ-008")
def test_every_response_matches_the_spec(client, spec, schema):
    violations = []
    for path, method, response in _scenario(client):
        try:
            schema_name = _declared(spec, path, method, response.status_code)
        except AssertionError as error:
            violations.append(str(error))
            continue
        validator = Draft202012Validator(schema(schema_name))
        for error in validator.iter_errors(response.get_json()):
            violations.append(f"{method.upper()} {path} {response.status_code}: {error.message}")
    assert not violations, "\n".join(violations)


@pytest.mark.req("REQ-008")
def test_scenario_covers_every_declared_response(client, spec):
    """Guards the test above: if the spec gains a response, the scenario must exercise it."""
    seen = {(path, method, str(response.status_code)) for path, method, response in _scenario(client)}
    declared = {(path, method, status)
                for path, item in spec["paths"].items()
                for method, op in item.items()
                for status in op["responses"]}
    assert declared <= seen, f"Not exercised: {sorted(declared - seen)}"
