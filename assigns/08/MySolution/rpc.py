"""JSON-RPC envelopes and the fixed Queens method allowlist; no HTTP code."""

import json
import math

from rpc_errors import RpcError
from streams import StreamManager


def error_reply(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def reject_constant(value):
    raise ValueError("Non-finite JSON number")


def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Non-finite JSON number")
    return number


class Dispatcher:
    def __init__(self, manager=None):
        self.manager = manager if manager is not None else StreamManager()

    def handle_json(self, body):
        """Return a response object, or None for a notification."""
        try:
            request = json.loads(body, parse_constant=reject_constant,
                                 parse_float=finite_float)
        except (ValueError, UnicodeError, RecursionError):
            return error_reply(None, -32700, "Parse error")
        return self.handle(request)

    def handle(self, request):
        if not isinstance(request, dict):
            return error_reply(None, -32600, "Invalid request; batches are not supported")
        request_id = request.get("id")
        valid_id = (request_id is None or type(request_id) in (str, int) or
                    (type(request_id) is float and math.isfinite(request_id)))
        if (request.get("jsonrpc") != "2.0" or
                not isinstance(request.get("method"), str) or not valid_id):
            return error_reply(None, -32600, "Invalid request")
        notification = "id" not in request
        try:
            self.manager.cleanup()
            result = self._dispatch(request["method"], request.get("params", {}))
            reply = {"jsonrpc": "2.0", "id": request_id, "result": result}
        except RpcError as error:
            reply = error_reply(request_id, error.code, error.message)
        except Exception:
            reply = error_reply(request_id, -32603, "Internal error")
        return None if notification else reply

    def _dispatch(self, method, params):
        fields = {
            "service.health": set(),
            "queens.open": {"size"},
            "queens.next": {"stream_id", "limit"},
            "queens.close": {"stream_id"},
        }
        if method not in fields:
            raise RpcError(-32601, "Method not found")
        if not isinstance(params, dict) or set(params) != fields[method]:
            raise RpcError(-32602, "Parameters must be an object with exactly the required fields")
        if method == "service.health":
            return {"status": "ok", "version": "1.0"}
        if method == "queens.open":
            return self.manager.open(params["size"])
        if method == "queens.next":
            return self.manager.next(params["stream_id"], params["limit"])
        return self.manager.close(params["stream_id"])
