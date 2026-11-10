# GENERATED FILE - DO NOT EDIT BY HAND.
# Source: spec/openapi.yaml (sha256 9dcedbb6cdc027c6). Regenerate: python generator/generate.py
"""The interface that hand-written or AI-written business logic must implement.

Every method returns a tuple (status_code, payload_dict). The generated routes check that
the status code is declared in the spec and that the payload matches its schema."""
from abc import ABC, abstractmethod


class VoucherServiceBase(ABC):
    @abstractmethod
    def get_voucher(self, voucher_id: str) -> tuple[int, dict]:
        """Look up a voucher

        Returns the voucher with its current balance and status.

        Operation: GET /vouchers/{voucherId}  (getVoucher)
        Requirements: REQ-003, REQ-008
        Allowed responses:
            200 -> Voucher
            404 -> Error
            422 -> Error
        """

    @abstractmethod
    def issue_voucher(self, body: dict) -> tuple[int, dict]:
        """Issue a new voucher

        Creates an active voucher whose balance equals the requested amount.

        Operation: POST /vouchers  (issueVoucher)
        Requirements: REQ-001, REQ-002, REQ-008
        Body: IssueVoucherRequest (already validated against the spec)
        Allowed responses:
            201 -> Voucher
            422 -> Error
        """

    @abstractmethod
    def redeem_voucher(self, voucher_id: str, body: dict) -> tuple[int, dict]:
        """Redeem an amount from a voucher

        Reduces the balance by the amount. Repeating a request with the same idempotency key
        returns the original result without reducing the balance again. Only successful
        redemptions are remembered, so a rejected request may be retried with the same key.

        Operation: POST /vouchers/{voucherId}/redemptions  (redeemVoucher)
        Requirements: REQ-004, REQ-005, REQ-006, REQ-007, REQ-008
        Body: RedeemRequest (already validated against the spec)
        Allowed responses:
            200 -> Redemption
            404 -> Error
            409 -> Error
            422 -> Error
        """
