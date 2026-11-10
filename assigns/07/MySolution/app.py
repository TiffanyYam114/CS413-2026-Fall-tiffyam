"""HTTP transport. Start from assigns/07 with: python -m MySolution.app"""

import json
import math

from flask import Flask, Response, jsonify, request

from .dispatcher import Dispatcher
from .rpc_errors import RpcError, error_response


def _reject_constant(value: str):
    raise ValueError("Nonstandard JSON constant")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Number is outside the supported finite range")
    return number


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    dispatcher = Dispatcher()
    app.extensions["rpc_dispatcher"] = dispatcher

    @app.post("/rpc", provide_automatic_options=False)
    def rpc():
        charset = request.mimetype_params.get("charset", "utf-8").lower()
        if request.mimetype != "application/json" or charset != "utf-8":
            return Response(
                "Use Content-Type: application/json with UTF-8 text.\n",
                status=415, mimetype="text/plain",
            )
        try:
            # Decode explicitly: malformed JSON must become a JSON-RPC error
            # with HTTP 200 rather than Flask's default HTTP 400 response.
            payload = json.loads(
                request.get_data().decode("utf-8"),
                parse_constant=_reject_constant, parse_float=_finite_float,
            )
        except (ValueError, RecursionError):
            return jsonify(error_response(None, RpcError(
                -32700, "Parse error", "json_parse",
                detail="Body must contain valid UTF-8 JSON with finite numbers.",
            ))), 200

        response = dispatcher.dispatch(payload)
        if response is None:
            return Response(status=204)
        return jsonify(response), 200

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000, debug=False)
