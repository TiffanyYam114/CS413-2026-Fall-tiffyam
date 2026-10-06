"""Coordinate source operations without passing HTTP objects into the model."""
from .examples import EXAMPLES
from .source import MAX_SOURCE_BYTES, SourceError


class SourceController:
    def __init__(self, model):
        self.model = model

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
