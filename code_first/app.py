"""Code-first implementation of the Offline Voucher API.

In the code-first condition you build the whole API here from requirements/requirements.yaml
only, without reading spec/, src/ or generator/. An AI coding assistant may be used.
create_app() must return a Flask app; the same acceptance tests are then run against it:

    TARGET=codefirst python -m pytest tests
"""
from flask import Flask, jsonify, request
import uuid


def create_app():
    app = Flask(__name__)
    
    # In-memory data stores scoped to the application instance
    vouchers = {}
    redemptions = {}

    def error_response(code, message, status_code):
        """Helper to return consistent JSON error responses per REQ-008."""
        return jsonify({"code": code, "message": message}), status_code

    @app.route('/vouchers', methods=['POST'])
    def issue_voucher():
        """REQ-001 & REQ-002: Issue a new voucher with amount limits and currency validation."""
        if not request.is_json:
            return error_response("VALIDATION_ERROR", "Request body must be JSON.", 422)
        
        body = request.get_json()
        if not isinstance(body, dict) or set(body.keys()) != {"amount", "currency"}:
            return error_response("VALIDATION_ERROR", "Request must contain exactly 'amount' and 'currency' fields.", 422)
        
        amount = body.get("amount")
        currency = body.get("currency")
        
        # Validate amount (must be integer between 1 and 100000 minor units)
        if not isinstance(amount, int) or isinstance(amount, bool) or not (1 <= amount <= 100000):
            return error_response("VALIDATION_ERROR", "Amount must be a whole number between 1 and 100000.", 422)
        
        # Validate currency (SEK or EUR)
        if currency not in ["SEK", "EUR"]:
            return error_response("VALIDATION_ERROR", "Unsupported currency. Must be SEK or EUR.", 422)
        
        voucher_id = str(uuid.uuid4())
        
        voucher = {
            "id": voucher_id,
            "amount": amount,
            "balance": amount,
            "currency": currency,
            "status": "active"
        }
        
        vouchers[voucher_id] = voucher
        return jsonify(voucher), 201

    @app.route('/vouchers/<voucher_id>', methods=['GET'])
    def get_voucher(voucher_id):
        """REQ-003: Look up a voucher by ID."""
        if len(voucher_id) > 64:
            return error_response("VALIDATION_ERROR", "Voucher ID exceeds maximum length of 64 characters.", 422)
            
        voucher = vouchers.get(voucher_id)
        if not voucher:
            return error_response("VOUCHER_NOT_FOUND", "Voucher with the given ID does not exist.", 404)
            
        return jsonify(voucher), 200

    @app.route('/vouchers/<voucher_id>/redemptions', methods=['POST'])
    def redeem_voucher(voucher_id):
        """REQ-004, REQ-005, REQ-006, REQ-007: Redeem part or all of an active voucher idempotently."""
        if len(voucher_id) > 64:
            return error_response("VALIDATION_ERROR", "Voucher ID exceeds maximum length of 64 characters.", 422)
            
        voucher = vouchers.get(voucher_id)
        if not voucher:
            return error_response("VOUCHER_NOT_FOUND", "Voucher with the given ID does not exist.", 404)
            
        if not request.is_json:
            return error_response("VALIDATION_ERROR", "Request body must be JSON.", 422)
            
        body = request.get_json()
        if not isinstance(body, dict) or set(body.keys()) != {"amount", "idempotencyKey"}:
            return error_response("VALIDATION_ERROR", "Request must contain exactly 'amount' and 'idempotencyKey' fields.", 422)
            
        amount = body.get("amount")
        idempotency_key = body.get("idempotencyKey")
        
        # Validate redemption amount
        if not isinstance(amount, int) or isinstance(amount, bool) or not (1 <= amount <= 100000):
            return error_response("VALIDATION_ERROR", "Redemption amount must be between 1 and 100000.", 422)
            
        # Validate idempotency key length (8 to 64 characters)
        if not isinstance(idempotency_key, str) or not (8 <= len(idempotency_key) <= 64):
            return error_response("VALIDATION_ERROR", "Idempotency key must be a string between 8 and 64 characters.", 422)
            
        key_tuple = (voucher_id, idempotency_key)
        
        # REQ-006: Return original result if this idempotency key was already successfully used
        if key_tuple in redemptions:
            return jsonify(redemptions[key_tuple]), 200
            
        # REQ-007: Reject further redemption if voucher is already fully redeemed
        if voucher["status"] == "redeemed" or voucher["balance"] == 0:
            return error_response("VOUCHER_REDEEMED", "Voucher is already fully redeemed.", 409)
            
        # REQ-005: Reject redemption larger than remaining balance
        if amount > voucher["balance"]:
            return error_response("INSUFFICIENT_BALANCE", "Redemption amount exceeds remaining voucher balance.", 409)
            
        # REQ-004 & REQ-007: Reduce balance and update status if fully redeemed
        voucher["balance"] -= amount
        if voucher["balance"] == 0:
            voucher["status"] = "redeemed"
            
        redemption_result = {
            "voucherId": voucher_id,
            "amount": amount,
            "remainingBalance": voucher["balance"],
            "status": voucher["status"]
        }
        
        # Save successful redemption for idempotency checks
        redemptions[key_tuple] = redemption_result
        return jsonify(redemption_result), 200

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)