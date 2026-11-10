"""Acceptance tests for change request CR-1 (REQ-009, voucher expiry).

Copied into tests/ at the start of task T2. Some tests wait about 1.5 seconds for a voucher
to expire, because black-box tests cannot move the server's clock."""
import time
from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import redeem


def _rfc3339(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _issue(client, expires_in_seconds=None, **extra):
    body = {"amount": 1000, "currency": "SEK", **extra}
    if expires_in_seconds is not None:
        body["expiresAt"] = _rfc3339(datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds))
    return client.post("/vouchers", json=body)


def _wait_until_expired(expires_at):
    deadline = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    time.sleep(max(0.0, (deadline - datetime.now(timezone.utc)).total_seconds()) + 1.1)


@pytest.mark.req("REQ-009")
def test_voucher_without_expiry_has_null_expires_at(client):
    response = _issue(client)
    assert response.status_code == 201
    assert response.get_json()["expiresAt"] is None


@pytest.mark.req("REQ-009")
def test_future_expiry_is_stored_and_returned(client):
    response = _issue(client, expires_in_seconds=3600)
    assert response.status_code == 201
    voucher = response.get_json()
    assert voucher["status"] == "active"
    assert client.get(f"/vouchers/{voucher['id']}").get_json()["expiresAt"] == voucher["expiresAt"]


@pytest.mark.req("REQ-009")
@pytest.mark.parametrize("expires_at", [
    "2001-01-01T00:00:00Z",          # in the past
    "next tuesday",                  # not a date-time
    "2099-13-40T00:00:00Z",          # impossible date
    "2099-01-01T00:00:00",           # no timezone
    12345,                           # wrong type
])
def test_invalid_expiry_is_rejected(client, expires_at):
    response = client.post("/vouchers", json={"amount": 1000, "currency": "SEK", "expiresAt": expires_at})
    assert response.status_code == 422
    assert response.get_json()["code"] == "VALIDATION_ERROR"


@pytest.mark.req("REQ-009")
def test_redemption_works_before_expiry(client):
    voucher = _issue(client, expires_in_seconds=3600).get_json()
    assert redeem(client, voucher["id"], 100).status_code == 200


@pytest.mark.req("REQ-009")
def test_expired_voucher_rejects_redemption_but_keeps_idempotent_results(client):
    voucher = _issue(client, expires_in_seconds=1).get_json()
    first = redeem(client, voucher["id"], 100, key="order-0001")
    assert first.status_code == 200

    _wait_until_expired(voucher["expiresAt"])

    response = redeem(client, voucher["id"], 100, key="order-0002")
    assert response.status_code == 410
    assert set(response.get_json()) == {"code", "message"}
    assert response.get_json()["code"] == "VOUCHER_EXPIRED"

    fetched = client.get(f"/vouchers/{voucher['id']}").get_json()
    assert fetched["status"] == "expired"
    assert fetched["balance"] == 900

    again = redeem(client, voucher["id"], 100, key="order-0001")
    assert again.status_code == 200
    assert again.get_json() == first.get_json()
