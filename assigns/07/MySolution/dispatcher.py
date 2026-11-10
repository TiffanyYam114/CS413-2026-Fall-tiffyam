"""JSON-RPC envelopes and batches, independent of Flask."""

import logging
import math

from . import lambda_service
from .rpc_errors import RpcError, error_response, internal_error

logger = logging.getLogger(__name__)


def _valid_id(value) -> bool:
    # bool is a subclass of int in Python, but is not a JSON-RPC numeric ID.
    return (
        value is None
        or isinstance(value, str)
        or type(value) is int
        or (type(value) is float and math.isfinite(value))
    )


class Dispatcher:
    def __init__(self):
        self.methods = {
            "service.health": lambda_service.health,
            "lambda.typecheck": lambda_service.typecheck,
            "lambda.interpret": lambda_service.interpret,
            "lambda.compile": lambda_service.compile_source,
        }

    def dispatch(self, payload):
        """Return a response object/array, or None when no reply is needed."""
        if isinstance(payload, list):
            if not payload:
                return error_response(None, RpcError(
                    -32600, "Invalid Request", "request",
                    detail="Batch must not be empty.",
                ))
            responses = []
            for member in payload:
                response = self._dispatch_one(member, in_batch=True)
                if response is not None:
                    responses.append(response)
            return responses or None
        return self._dispatch_one(payload)

    def _dispatch_one(self, request, *, in_batch=False):
        is_object = isinstance(request, dict)
        request_id = request.get("id") if is_object else None
        valid_envelope = (
            is_object
            and request.get("jsonrpc") == "2.0"
            and isinstance(request.get("method"), str)
            and _valid_id(request_id)
        )
        if not valid_envelope:
            response_id = (
                request_id if not in_batch and _valid_id(request_id) else None
            )
            return error_response(response_id, RpcError(
                -32600, "Invalid Request", "request",
                detail="Expected a request object with jsonrpc '2.0', a string method, and an allowed ID.",
            ))

        notification = "id" not in request
        try:
            handler = self.methods.get(request["method"])
            if handler is None:
                raise RpcError(-32601, "Method not found", "method")
            result = handler(request.get("params"))
            response = {"jsonrpc": "2.0", "result": result, "id": request_id}
        except RpcError as error:
            response = error_response(request_id, error)
        except Exception:
            logger.exception("Unexpected RPC method failure")
            response = error_response(request_id, internal_error())
        return None if notification else response
