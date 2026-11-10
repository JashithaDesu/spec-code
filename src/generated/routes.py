# GENERATED FILE - DO NOT EDIT BY HAND.
# Source: spec/openapi.yaml (sha256 9dcedbb6cdc027c6). Regenerate: python generator/generate.py
"""Flask routes for every operation in the spec.

Each route validates path parameters and the request body against the spec, calls the
service, and (unless disabled) checks that the service's response is declared in the spec
and matches its schema. A response that breaks the contract becomes a 500 error, so a test
or an API fuzzer notices immediately."""
from flask import jsonify, request
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .schemas import OPERATIONS, SCHEMAS


class ContractViolation(Exception):
    """The business logic returned something the spec does not allow."""


def _first_error(schema, instance):
    error = best_match(Draft202012Validator(schema).iter_errors(instance))
    return None if error is None else error.message


def _validation_error(message):
    return jsonify({"code": "VALIDATION_ERROR", "message": message}), 422


def _respond(operation_id, result, validate_responses):
    try:
        status, payload = result
    except (TypeError, ValueError):
        raise ContractViolation(f"{operation_id}: service must return (status_code, payload)")
    allowed = OPERATIONS[operation_id]["responses"]
    if validate_responses:
        if str(status) not in allowed:
            raise ContractViolation(f"{operation_id}: status {status} is not declared in the spec")
        problem = _first_error(SCHEMAS[allowed[str(status)]], payload)
        if problem:
            raise ContractViolation(f"{operation_id}: {status} response does not match "
                                    f"{allowed[str(status)]}: {problem}")
    return jsonify(payload), status


def register_routes(app, service, validate_responses=True):
    @app.errorhandler(ContractViolation)
    def _contract_violation(error):
        app.logger.error("Contract violation: %s", error)
        app.config.setdefault("CONTRACT_VIOLATIONS", []).append(str(error))
        return jsonify({"code": "CONTRACT_VIOLATION", "message": str(error)}), 500

    @app.route("/vouchers/<voucherId>", methods=["GET"], endpoint="getVoucher")
    def get_voucher(voucherId):
        problem = _first_error(OPERATIONS["getVoucher"]["params"]["voucherId"], voucherId)
        if problem:
            return _validation_error(f"voucherId: {problem}")
        result = service.get_voucher(voucherId)
        return _respond("getVoucher", result, validate_responses)

    @app.route("/vouchers", methods=["POST"], endpoint="issueVoucher")
    def issue_voucher():
        body = request.get_json(silent=True)
        if body is None:
            return _validation_error("Request body must be valid JSON")
        problem = _first_error(SCHEMAS["IssueVoucherRequest"], body)
        if problem:
            return _validation_error(problem)
        result = service.issue_voucher(body)
        return _respond("issueVoucher", result, validate_responses)

    @app.route("/vouchers/<voucherId>/redemptions", methods=["POST"], endpoint="redeemVoucher")
    def redeem_voucher(voucherId):
        problem = _first_error(OPERATIONS["redeemVoucher"]["params"]["voucherId"], voucherId)
        if problem:
            return _validation_error(f"voucherId: {problem}")
        body = request.get_json(silent=True)
        if body is None:
            return _validation_error("Request body must be valid JSON")
        problem = _first_error(SCHEMAS["RedeemRequest"], body)
        if problem:
            return _validation_error(problem)
        result = service.redeem_voucher(voucherId, body)
        return _respond("redeemVoucher", result, validate_responses)
