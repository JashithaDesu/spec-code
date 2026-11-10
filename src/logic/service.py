"""Business logic for the Offline Voucher API (spec-driven condition).

This is the ONLY file filled in during the spec-driven experiment, either by
ai/fill_logic.py or by hand. Everything under src/generated/ is produced from the spec.

Rules (checked by gates/check_guardrails.py):
  - subclass VoucherServiceBase and implement every method
  - return (status_code, payload_dict) using only the statuses and schemas the spec allows
  - keep state in memory on the instance; no file, network or subprocess access
"""
from src.generated.service_base import VoucherServiceBase


class VoucherService(VoucherServiceBase):
    def __init__(self):
        pass

    def issue_voucher(self, body):
        raise NotImplementedError("REQ-001, REQ-002")

    def get_voucher(self, voucher_id):
        raise NotImplementedError("REQ-003")

    def redeem_voucher(self, voucher_id, body):
        raise NotImplementedError("REQ-004 to REQ-007")
