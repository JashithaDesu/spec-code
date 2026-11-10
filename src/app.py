"""App factory for the spec-driven implementation."""
from flask import Flask

from src.generated.routes import register_routes
from src.logic.service import VoucherService


def create_app(validate_responses=True):
    app = Flask(__name__)
    register_routes(app, VoucherService(), validate_responses=validate_responses)
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
