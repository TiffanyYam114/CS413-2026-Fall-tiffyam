"""Errors shared by the dispatcher and the LAMBDA3 adapter."""


class RpcError(Exception):
    """A client-facing error whose data is safe to send over HTTP."""

    def __init__(self, code: int, message: str, category: str, **data):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = {"category": category, **data}

    def as_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "data": self.data}


def internal_error() -> RpcError:
    return RpcError(-32603, "Internal error", "internal")


def error_response(request_id, error: RpcError) -> dict:
    return {"jsonrpc": "2.0", "error": error.as_dict(), "id": request_id}
