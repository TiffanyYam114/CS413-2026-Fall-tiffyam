"""Coordinate source operations without passing HTTP objects into the model."""
from .examples import EXAMPLES
from .source import MAX_SOURCE_BYTES, SourceError
from threading import Thread
from .backend import LambdaBackend
from .tools import Artifact, BackendReply, Outcome, Result


class SourceController:
    def __init__(self, model, backend=None):
        self.model = model
        self.backend = backend if backend is not None else LambdaBackend()

    def command(self, command, source=None, example=None, version=None):
        if command == "manual":
            self.model.manual(version)
        elif command == "edit":
            self.model.edit(source, version)
        elif command == "apply":
            self.model.apply(source, version)
        elif command == "discard":
            self.model.discard(version)
        elif command == "example":
            if not isinstance(example, str) or example not in EXAMPLES:
                raise SourceError("Choose Factorial or Fibonacci.")
            name, text = EXAMPLES[example]
            self.model.load(name, text, version)
        else:
            raise SourceError("Unknown source operation.")

    def upload(self, name, contents, version=None):
        name = name.replace("\\", "/").rsplit("/", 1)[-1] or "Uploaded source"
        try:
            text = contents.decode("utf-8-sig")
        except UnicodeDecodeError:
            self.model.load(name, contents.decode("utf-8-sig", errors="replace"), version,
                            "File is not valid UTF-8. Invalid bytes appear as replacement characters in the draft; edit them or discard and upload a UTF-8 file.")
            return
        reason = "Upload exceeds the 64 KiB (65536-byte) UTF-8 limit." if len(contents) > MAX_SOURCE_BYTES else None
        self.model.load(name, text, version, reason)

    def action(self, operation, version=None):
        revision, source, artifact = self.model.begin_operation(operation, version)

        def work():
            try:
                reply = (self.backend.execute(artifact) if operation == "execute"
                         else getattr(self.backend, operation)(source))
                if not isinstance(reply, BackendReply) or not isinstance(reply.outcome, Outcome):
                    raise TypeError("Backend must return a BackendReply with an Outcome.")
                generated = None
                if operation == "compile" and reply.outcome == Outcome.SUCCESS and reply.generated_code:
                    generated = Artifact(revision, reply.generated_code.format, reply.generated_code.code)
                self.model.finish_operation(Result(operation, revision, reply.outcome,
                                                   reply.text, reply.free_variables), generated)
            except Exception as exc:
                self.model.finish_operation(Result(operation, revision, Outcome.BACKEND_FAILURE,
                                                   f"Backend failed: {type(exc).__name__}: {str(exc)[:1000]}. You can retry."))

        try:
            Thread(target=work, name=f"lambda-{operation}-{revision}", daemon=True).start()
        except Exception as exc:
            self.model.finish_operation(Result(operation, revision, Outcome.BACKEND_FAILURE,
                                               f"Could not start backend: {exc}. You can retry."))
