"""Acceptance tests derived from requirements/requirements.yaml.

Each test is linked to a requirement with @pytest.mark.req, so gates/trace_check.py can
show that every requirement is tested. These tests only use HTTP, so they judge the
spec-driven and the code-first implementation in exactly the same way."""
import pytest

from tests.conftest import issue, redeem


# ---------- REQ-001: Issue a voucher ----------

@pytest.mark.req("REQ-001")
def test_issue_voucher(client):
    response = client.post("/vouchers", json={"amount": 50000, "currency": "SEK"})
    assert response.status_code == 201
    voucher = response.get_json()
    assert voucher["amount"] == 50000
    assert voucher["balance"] == 50000
    assert voucher["currency"] == "SEK"
    assert voucher["status"] == "active"
    assert voucher["id"]


@pytest.mark.req("REQ-001")
def test_voucher_ids_are_unique(client):
    ids = {issue(client, amount=100)["id"] for _ in range(20)}
    assert len(ids) == 20


@pytest.mark.req("REQ-001")
def test_issue_voucher_in_eur(client):
    assert issue(client, currency="EUR")["currency"] == "EUR"


# ---------- REQ-002: Amount limits ----------

@pytest.mark.req("REQ-002")
@pytest.mark.parametrize("amount", [1, 100000])
def test_amount_limits_are_inclusive(client, amount):
    assert issue(client, amount=amount)["balance"] == amount


@pytest.mark.req("REQ-002")
@pytest.mark.parametrize("body", [
    {"amount": 0, "currency": "SEK"},
    {"amount": 100001, "currency": "SEK"},
    {"amount": -5, "currency": "SEK"},
    {"amount": "100", "currency": "SEK"},
    {"amount": 12.5, "currency": "SEK"},
    {"amount": True, "currency": "SEK"},
    {"currency": "SEK"},
    {"amount": 100},
    {"amount": 100, "currency": "USD"},
    {"amount": 100, "currency": "SEK", "note": "extra field"},
    [100, "SEK"],
])
def test_invalid_issue_requests_are_rejected(client, body):
    response = client.post("/vouchers", json=body)
    assert response.status_code == 422
    assert response.get_json()["code"] == "VALIDATION_ERROR"


@pytest.mark.req("REQ-002")
def test_non_json_body_is_rejected(client):
    response = client.post("/vouchers", data="amount=100", content_type="text/plain")
    assert response.status_code == 422
    assert response.get_json()["code"] == "VALIDATION_ERROR"


# ---------- REQ-003: Look up a voucher ----------

@pytest.mark.req("REQ-003")
def test_get_voucher_returns_the_issued_voucher(client):
    voucher = issue(client)
    response = client.get(f"/vouchers/{voucher['id']}")
    assert response.status_code == 200
    assert response.get_json() == voucher


@pytest.mark.req("REQ-003")
def test_unknown_voucher_is_404(client):
    response = client.get("/vouchers/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["code"] == "VOUCHER_NOT_FOUND"


@pytest.mark.req("REQ-003")
def test_too_long_voucher_id_is_422(client):
    response = client.get("/vouchers/" + "x" * 65)
    assert response.status_code == 422
    assert response.get_json()["code"] == "VALIDATION_ERROR"


# ---------- REQ-004: Redeem part of a voucher ----------

@pytest.mark.req("REQ-004")
def test_partial_redemption_reduces_balance(client):
    voucher = issue(client, amount=50000)
    response = redeem(client, voucher["id"], 12000)
    assert response.status_code == 200
    assert response.get_json() == {"voucherId": voucher["id"], "amount": 12000,
                                   "remainingBalance": 38000, "status": "active"}
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 38000


@pytest.mark.req("REQ-004")
def test_several_redemptions_add_up(client):
    voucher = issue(client, amount=1000)
    for i, amount in enumerate([100, 250, 400]):
        assert redeem(client, voucher["id"], amount, key=f"order-{i:04d}").status_code == 200
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 250


@pytest.mark.req("REQ-004")
def test_redeem_unknown_voucher_is_404(client):
    response = redeem(client, "does-not-exist", 100)
    assert response.status_code == 404
    assert response.get_json()["code"] == "VOUCHER_NOT_FOUND"


@pytest.mark.req("REQ-004")
@pytest.mark.parametrize("body", [
    {"amount": 0, "idempotencyKey": "order-0001"},
    {"amount": 100},
    {"amount": 100, "idempotencyKey": "short"},
    {"amount": 100, "idempotencyKey": "k" * 65},
    {"amount": 100, "idempotencyKey": "order-0001", "tip": 5},
])
def test_invalid_redeem_requests_are_rejected(client, body):
    voucher = issue(client, amount=1000)
    response = client.post(f"/vouchers/{voucher['id']}/redemptions", json=body)
    assert response.status_code == 422
    assert response.get_json()["code"] == "VALIDATION_ERROR"
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 1000


# ---------- REQ-005: No negative balance ----------

@pytest.mark.req("REQ-005")
def test_overdraw_is_rejected_and_balance_unchanged(client):
    voucher = issue(client, amount=1000)
    response = redeem(client, voucher["id"], 1001)
    assert response.status_code == 409
    assert response.get_json()["code"] == "INSUFFICIENT_BALANCE"
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 1000


@pytest.mark.req("REQ-005")
def test_overdraw_after_partial_redemption(client):
    voucher = issue(client, amount=1000)
    redeem(client, voucher["id"], 600, key="order-0001")
    response = redeem(client, voucher["id"], 401, key="order-0002")
    assert response.status_code == 409
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 400


# ---------- REQ-006: Idempotent redemption ----------

@pytest.mark.req("REQ-006")
def test_repeated_key_does_not_charge_twice(client):
    voucher = issue(client, amount=1000)
    first = redeem(client, voucher["id"], 300, key="order-0001")
    second = redeem(client, voucher["id"], 300, key="order-0001")
    assert second.status_code == 200
    assert second.get_json() == first.get_json()
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 700


@pytest.mark.req("REQ-006")
def test_repeated_key_returns_original_result_even_with_a_different_amount(client):
    voucher = issue(client, amount=1000)
    first = redeem(client, voucher["id"], 300, key="order-0001").get_json()
    second = redeem(client, voucher["id"], 500, key="order-0001")
    assert second.status_code == 200
    assert second.get_json() == first
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["balance"] == 700


@pytest.mark.req("REQ-006")
def test_the_same_key_on_different_vouchers_is_independent(client):
    a = issue(client, amount=1000)
    b = issue(client, amount=1000)
    redeem(client, a["id"], 300, key="order-0001")
    redeem(client, b["id"], 300, key="order-0001")
    assert client.get(f"/vouchers/{b['id']}").get_json()["balance"] == 700


@pytest.mark.req("REQ-006")
def test_a_rejected_redemption_can_be_retried_with_the_same_key(client):
    """A 409 is not a completed redemption, so it is not remembered: the same key may be
    used again after the situation changes. This is a design decision made explicit."""
    voucher = issue(client, amount=1000)
    assert redeem(client, voucher["id"], 2000, key="order-0001").status_code == 409
    assert redeem(client, voucher["id"], 500, key="order-0001").status_code == 200


# ---------- REQ-007: Fully redeemed vouchers ----------

@pytest.mark.req("REQ-007")
def test_redeeming_the_full_balance_marks_voucher_redeemed(client):
    voucher = issue(client, amount=1000)
    response = redeem(client, voucher["id"], 1000)
    assert response.get_json()["remainingBalance"] == 0
    assert response.get_json()["status"] == "redeemed"
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["status"] == "redeemed"


@pytest.mark.req("REQ-007")
def test_redeemed_voucher_rejects_new_redemptions(client):
    voucher = issue(client, amount=1000)
    redeem(client, voucher["id"], 1000, key="order-0001")
    response = redeem(client, voucher["id"], 1, key="order-0002")
    assert response.status_code == 409
    assert response.get_json()["code"] == "VOUCHER_REDEEMED"


@pytest.mark.req("REQ-007")
def test_repeating_the_final_redemption_still_returns_its_result(client):
    voucher = issue(client, amount=1000)
    first = redeem(client, voucher["id"], 1000, key="order-0001")
    again = redeem(client, voucher["id"], 1000, key="order-0001")
    assert again.status_code == 200
    assert again.get_json() == first.get_json()


# ---------- REQ-008: Consistent errors ----------

@pytest.mark.req("REQ-008")
def test_every_error_has_code_and_message_only(client):
    voucher = issue(client, amount=100)
    redeem(client, voucher["id"], 100, key="order-0001")
    errors = [
        client.post("/vouchers", json={"amount": 0, "currency": "SEK"}),
        client.get("/vouchers/missing"),
        redeem(client, "missing", 10),
        redeem(client, voucher["id"], 10, key="order-0002"),
    ]
    other = issue(client, amount=100)
    errors.append(redeem(client, other["id"], 500))
    for response in errors:
        body = response.get_json()
        assert set(body) == {"code", "message"}, body
        assert isinstance(body["message"], str) and body["message"]
