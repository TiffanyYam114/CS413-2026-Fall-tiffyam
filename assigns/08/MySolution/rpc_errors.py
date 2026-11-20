"""Public RPC errors shared by validation and stream management."""


class RpcError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def integer_in_range(value, name, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise RpcError(-32602, f"{name} must be an integer from {minimum} through {maximum}")


def valid_stream_id(value):
    if not isinstance(value, str) or not value:
        raise RpcError(-32602, "stream_id must be a nonempty string")
