# GENERATED FILE - DO NOT EDIT BY HAND.
# Source: spec/openapi.yaml (sha256 9dcedbb6cdc027c6). Regenerate: python generator/generate.py
"""JSON Schemas resolved from spec/openapi.yaml, used to validate requests and responses."""
import json

SCHEMAS = json.loads(r'''
{
  "Currency": {
    "description": "Supported currencies",
    "enum": [
      "SEK",
      "EUR"
    ],
    "type": "string"
  },
  "Error": {
    "additionalProperties": false,
    "description": "The common error body for every error response (REQ-008)",
    "properties": {
      "code": {
        "description": "Machine-readable error code",
        "enum": [
          "VALIDATION_ERROR",
          "VOUCHER_NOT_FOUND",
          "INSUFFICIENT_BALANCE",
          "VOUCHER_REDEEMED"
        ],
        "type": "string"
      },
      "message": {
        "description": "Human-readable explanation",
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "code",
      "message"
    ],
    "type": "object"
  },
  "IssueVoucherRequest": {
    "additionalProperties": false,
    "description": "Body for issuing a voucher",
    "properties": {
      "amount": {
        "description": "Voucher value in minor units",
        "maximum": 100000,
        "minimum": 1,
        "type": "integer"
      },
      "currency": {
        "description": "Supported currencies",
        "enum": [
          "SEK",
          "EUR"
        ],
        "type": "string"
      }
    },
    "required": [
      "amount",
      "currency"
    ],
    "type": "object"
  },
  "RedeemRequest": {
    "additionalProperties": false,
    "description": "Body for redeeming an amount",
    "properties": {
      "amount": {
        "description": "Amount to redeem in minor units",
        "maximum": 100000,
        "minimum": 1,
        "type": "integer"
      },
      "idempotencyKey": {
        "description": "Client-chosen key; repeating it returns the original result",
        "maxLength": 64,
        "minLength": 8,
        "type": "string"
      }
    },
    "required": [
      "amount",
      "idempotencyKey"
    ],
    "type": "object"
  },
  "Redemption": {
    "additionalProperties": false,
    "description": "The result of a redemption",
    "properties": {
      "amount": {
        "description": "Amount redeemed in minor units",
        "maximum": 100000,
        "minimum": 1,
        "type": "integer"
      },
      "remainingBalance": {
        "description": "Balance after the redemption",
        "maximum": 100000,
        "minimum": 0,
        "type": "integer"
      },
      "status": {
        "description": "Voucher status after the redemption",
        "enum": [
          "active",
          "redeemed"
        ],
        "type": "string"
      },
      "voucherId": {
        "description": "The redeemed voucher",
        "maxLength": 64,
        "minLength": 1,
        "type": "string"
      }
    },
    "required": [
      "voucherId",
      "amount",
      "remainingBalance",
      "status"
    ],
    "type": "object"
  },
  "Voucher": {
    "additionalProperties": false,
    "description": "A voucher and its current state",
    "properties": {
      "amount": {
        "description": "Original value in minor units",
        "maximum": 100000,
        "minimum": 1,
        "type": "integer"
      },
      "balance": {
        "description": "Remaining value in minor units",
        "maximum": 100000,
        "minimum": 0,
        "type": "integer"
      },
      "currency": {
        "description": "Supported currencies",
        "enum": [
          "SEK",
          "EUR"
        ],
        "type": "string"
      },
      "id": {
        "description": "Unique voucher id",
        "maxLength": 64,
        "minLength": 1,
        "type": "string"
      },
      "status": {
        "description": "active while balance > 0, redeemed when balance is 0",
        "enum": [
          "active",
          "redeemed"
        ],
        "type": "string"
      }
    },
    "required": [
      "id",
      "amount",
      "balance",
      "currency",
      "status"
    ],
    "type": "object"
  }
}
''')

# operationId -> {"request": schema name or None, "params": {name: schema},
#                 "responses": {status code: schema name}}
OPERATIONS = json.loads(r'''
{
  "getVoucher": {
    "params": {
      "voucherId": {
        "maxLength": 64,
        "minLength": 1,
        "type": "string"
      }
    },
    "request": null,
    "responses": {
      "200": "Voucher",
      "404": "Error",
      "422": "Error"
    }
  },
  "issueVoucher": {
    "params": {},
    "request": "IssueVoucherRequest",
    "responses": {
      "201": "Voucher",
      "422": "Error"
    }
  },
  "redeemVoucher": {
    "params": {
      "voucherId": {
        "maxLength": 64,
        "minLength": 1,
        "type": "string"
      }
    },
    "request": "RedeemRequest",
    "responses": {
      "200": "Redemption",
      "404": "Error",
      "409": "Error",
      "422": "Error"
    }
  }
}
''')
