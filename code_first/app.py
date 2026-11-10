"""Code-first implementation of the Offline Voucher API.

In the code-first condition you build the whole API here from requirements/requirements.yaml
only, without reading spec/, src/ or generator/. An AI coding assistant may be used.
create_app() must return a Flask app; the same acceptance tests are then run against it:

    TARGET=codefirst python -m pytest tests
"""
from flask import Flask


def create_app():
    app = Flask(__name__)
    # Build the routes for issuing, looking up and redeeming vouchers here.
    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
