"""Validate method inputs and wrap LAMBDA3 without reimplementing it."""

import json
import logging
import multiprocessing
from pathlib import Path
import re
import sys
import tempfile
import time

from .rpc_errors import RpcError, internal_error

# LAMBDA3 imports its sibling basics0 module. Resolve it from this file so
# starting the server from a different directory still uses the provided code.
LAMBDA3_DIRECTORY = Path(__file__).resolve().parents[1] / "LAMBDA3"
sys.path.insert(0, str(LAMBDA3_DIRECTORY))
import lambda3  # noqa: E402

MAX_SOURCE_BYTES = 65_536
INTERPRET_TIMEOUT_SECONDS = 2
logger = logging.getLogger(__name__)


def _invalid_params(parameter: str, detail: str, **data) -> RpcError:
    return RpcError(
        -32602, "Invalid params", "params",
        parameter=parameter, detail=detail, **data,
    )


def _check_fields(params, required: set[str]) -> None:
    if not isinstance(params, dict):
        raise _invalid_params("params", "Params must be an object.")
    for field in sorted(required):
        if field not in params:
            raise _invalid_params(field, "Required parameter is missing.")
    if params.keys() - required:
        raise _invalid_params("params", "Unexpected parameters are not allowed.")


def _check_source(params) -> str:
    source = params["source"]
    if not isinstance(source, str) or not source.strip():
        raise _invalid_params("source", "Source must be a nonblank string.")
    try:
        size = len(source.encode("utf-8"))
    except UnicodeEncodeError:
        raise _invalid_params("source", "Source must be valid UTF-8 text.") from None
    if size > MAX_SOURCE_BYTES:
        raise _invalid_params(
            "source", "Source exceeds the maximum UTF-8 byte length.",
            limit=MAX_SOURCE_BYTES, unit="bytes",
        )
    return source


def _safe_diagnostic(message: str) -> str:
    # Known language errors may quote source tokens. Strip control characters
    # and path-like text, and never stringify an arbitrary backend exception.
    message = "".join(character if character.isprintable() else " " for character in message)
    message = " ".join(message.split())
    message = re.sub(r"(?:[A-Za-z]:[\\/]|/)[^\s'\"<>]+", "[path]", message)
    return message[:500]


def _parse_and_typecheck(source: str):
    try:
        return lambda3.d0exp_parse_and_typecheck(source)
    except lambda3.LambdaSyntaxError as error:
        data = {"detail": _safe_diagnostic(error.msg)}
        if isinstance(error.lineno, int) and error.lineno > 0:
            data["line"] = error.lineno
        if isinstance(error.offset, int) and error.offset > 0:
            data["column"] = error.offset
        raise RpcError(-32010, "LAMBDA syntax error", "syntax", **data) from None
    except lambda3.TypeCheckError as error:
        raise RpcError(
            -32011, "LAMBDA type error", "typecheck",
            detail=_safe_diagnostic(str(error)),
        ) from None


def _interpret_worker(source: str, output_path: str) -> None:
    """Only formatted strings or safe errors cross the process boundary."""
    try:
        expression, typ = _parse_and_typecheck(source)
        value = lambda3.d0exp_evaluate(expression)
        payload = {"result": {
            "type": lambda3.format_type(typ),
            "value": lambda3.d0val_format(value),
        }}
    except RpcError as error:
        payload = {"error": error.as_dict()}
    except Exception:
        logger.exception("Unexpected LAMBDA3 interpretation failure")
        payload = {"error": internal_error().as_dict()}

    # A file avoids filling an IPC pipe while the parent waits for completion.
    # The parent reads it only after the worker exits, so partial output is
    # never returned. TemporaryDirectory removes it after every call.
    Path(output_path).write_text(json.dumps(payload), encoding="utf-8")


def _interpret_with_deadline(source: str) -> dict:
    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory(prefix="lambda3-rpc-") as directory:
        output_path = Path(directory) / "result.json"
        process = context.Process(
            target=_interpret_worker, args=(source, str(output_path)), daemon=True,
        )
        started = False
        try:
            deadline = time.monotonic() + INTERPRET_TIMEOUT_SECONDS
            process.start()
            started = True
            process.join(max(0, deadline - time.monotonic()))
            if process.is_alive():
                raise RpcError(
                    -32012, "Execution timeout", "timeout",
                    limit=INTERPRET_TIMEOUT_SECONDS, unit="seconds",
                )
            if process.exitcode != 0 or not output_path.is_file():
                raise RuntimeError("Interpretation worker exited without a result")
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            if "error" in payload:
                error = payload["error"]
                data = dict(error["data"])
                category = data.pop("category")
                raise RpcError(error["code"], error["message"], category, **data)
            return payload["result"]
        finally:
            if started:
                if process.is_alive():
                    process.terminate()
                    process.join(0.5)
                    if process.is_alive():
                        process.kill()
                        process.join()
                process.close()


def health(params) -> dict:
    _check_fields(params, set())
    return {"status": "ok", "version": "1.0"}


def typecheck(params) -> dict:
    _check_fields(params, {"source"})
    source = _check_source(params)
    _, typ = _parse_and_typecheck(source)
    return {"type": lambda3.format_type(typ)}


def interpret(params) -> dict:
    _check_fields(params, {"source"})
    return _interpret_with_deadline(_check_source(params))


def compile_source(params) -> dict:
    _check_fields(params, {"source", "target"})
    source = _check_source(params)
    target = params["target"]
    if target not in ("python", "javascript"):
        raise _invalid_params("target", "Target must be 'python' or 'javascript'.")
    expression, _ = _parse_and_typecheck(source)
    compiler = (
        lambda3.d0exp_compile if target == "python" else lambda3.d0exp_compile_js
    )
    return {"target": target, "code": compiler(expression)}
