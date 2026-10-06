"""Replaceable adapter to lambda1; bounded work in disposable processes."""
import multiprocessing as mp
from . import lambda1 as lang
from .tools import (Artifact, BackendReply, MAX_OUTPUT_CHARS, Outcome,
                        WORKER_TIMEOUT_SECONDS)
from .reader import InputError, read_expression


def contains_error(value: lang.d0val) -> bool:
    if type(value) is lang.D0V000:
        return True
    return (isinstance(value, lang.D0Vpair)
            and (contains_error(value.arg1) or contains_error(value.arg2)))


def perform(operation: str, source: str) -> BackendReply:
    """Pure integration seam; called only inside a bounded worker in the app."""
    try:
        expression = read_expression(source)
    except InputError as exc:
        return BackendReply(Outcome.INPUT_ERROR, str(exc))
    if operation == "lint":
        names = lang.d0exp_fvset(expression)
        if names:
            return BackendReply(Outcome.LANGUAGE_ERROR,
                                "Undeclared variables: " + ", ".join(repr(n) for n in sorted(names)), names)
        return BackendReply(Outcome.SUCCESS, "No free variables were found.", names)
    if operation != "interpret":
        raise ValueError(f"Unknown worker operation: {operation}")
    try:
        value = lang.d0exp_evaluate(expression, lang.ENVnil())
        if contains_error(value):
            return BackendReply(Outcome.RUNTIME_ERROR,
                                "Evaluation returned D0V000() (an unbound variable), directly or inside a pair.")
        return BackendReply(Outcome.SUCCESS, repr(value))
    except (ArithmeticError, TypeError, ValueError, RecursionError) as exc:
        return BackendReply(Outcome.RUNTIME_ERROR, f"{type(exc).__name__}: {exc}")


def _worker(connection, operation: str, source: str) -> None:
    try:
        reply = perform(operation, source)
        if len(reply.text) > MAX_OUTPUT_CHARS:
            reply = BackendReply(reply.outcome, reply.text[:MAX_OUTPUT_CHARS] + "\n[Output truncated]",
                                 reply.free_variables)
        connection.send(reply)
    except Exception as exc:
        connection.send(BackendReply(Outcome.BACKEND_FAILURE,
                                    f"Language worker failed: {type(exc).__name__}: {str(exc)[:1000]}"))
    finally:
        connection.close()


class LambdaBackend:
    def __init__(self, timeout: float = WORKER_TIMEOUT_SECONDS):
        self.timeout = timeout

    def _run(self, operation: str, source: str) -> BackendReply:
        context = mp.get_context("spawn")
        receive, send = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(send, operation, source), daemon=True)
        started = False
        try:
            process.start()
            started = True
            send.close()
            if not receive.poll(self.timeout):
                return BackendReply(Outcome.BACKEND_FAILURE,
                                    f"{operation.title()} exceeded the {self.timeout:g}-second worker limit. You can retry.")
            reply = receive.recv()
            if not isinstance(reply, BackendReply):
                raise TypeError("Worker returned an invalid reply")
            return reply
        except (EOFError, OSError) as exc:
            return BackendReply(Outcome.BACKEND_FAILURE,
                                f"Worker unavailable: {type(exc).__name__}: {exc}. You can retry.")
        finally:
            receive.close()
            send.close()
            if started:
                # Do not leave a timed-out interpreter running in the background.
                if process.is_alive():
                    process.terminate()
                process.join(0.5)
                if process.is_alive():
                    process.kill()
                    process.join(0.5)
                process.close()

    def lint(self, source: str) -> BackendReply:
        return self._run("lint", source)

    def interpret(self, source: str) -> BackendReply:
        return self._run("interpret", source)

    def typecheck(self, source: str) -> BackendReply:
        return BackendReply(Outcome.NOT_IMPLEMENTED, "Type checking is not yet implemented.")

    def compile(self, source: str) -> BackendReply:
        return BackendReply(Outcome.NOT_IMPLEMENTED, "Compilation is not yet implemented.")

    def execute(self, artifact: Artifact) -> BackendReply:
        return BackendReply(Outcome.NOT_IMPLEMENTED, "Generated-code execution is not yet implemented.")
