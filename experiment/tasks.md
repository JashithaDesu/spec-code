# Tasks

## T1. Initial implementation

Implement REQ-001 to REQ-008 from `requirements/requirements.yaml`. See `PROTOCOL.md` for
the procedure in each condition.

## T2. Change request CR-1: voucher expiry

> Merchants want vouchers that expire. When issuing a voucher, a client may give an
> expiry time. After that time the voucher can no longer be redeemed.

**Start of T2 (both conditions):** copy the new tests into the test folder and add the
requirement text:

```
cp experiment/cr1/test_cr1_expiry.py tests/
cp experiment/cr1/test_contract.py tests/test_contract.py
```

and append REQ-009 below to `requirements/requirements.yaml`, plus the interface lines below
to its `interface` section. These tests and texts are the same for both conditions.

```yaml
  - id: REQ-009
    title: Voucher expiry
    text: When issuing, a client may give expiresAt, a date-time in the future with a timezone
      (RFC 3339, e.g. 2027-03-01T12:00:00Z). A past or malformed expiresAt is rejected with 422.
      Every voucher response includes expiresAt (null when none was given). After expiresAt the
      status of a voucher that still has a balance is "expired", and a new redemption is rejected with 410 and the code
      VOUCHER_EXPIRED; the balance is unchanged. Repeating an earlier successful redemption
      (same idempotency key) still returns its original result.
```

```
  POST /vouchers body may also contain "expiresAt": RFC 3339 date-time string
  Voucher gains "expiresAt": string or null; status may also be "expired"
  POST /vouchers/{voucherId}/redemptions may also return 410 with code VOUCHER_EXPIRED
```

**Condition A** additionally updates `spec/openapi.yaml` (request field, Voucher field,
status value, error code, 410 response, `REQ-009` in `x-requirements`), runs
`python generator/generate.py`, and then updates the logic. Writing the spec change is part
of the measured work.

**Condition B** changes the code in `code_first/` directly.
