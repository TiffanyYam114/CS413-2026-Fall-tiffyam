"""Applied source and editable drafts, independent of Django and the browser."""
from threading import RLock

MAX_SOURCE_BYTES = 64 * 1024


class SourceError(ValueError):
    """An input change cannot be accepted; its editable draft is retained."""


class SourceConflict(ValueError):
    """The requested operation conflicts with current application state."""


class SourceModel:
    def __init__(self):
        self._lock = RLock()
        self.source = None
        self.source_name = "No source loaded"
        self.revision = 0
        self.version = 0
        self.draft = ""
        self.draft_name = "Manual input"
        self.manual_pending = False
        self.draft_error = None

    def _dirty(self):
        return self.manual_pending or self.draft != (self.source or "")

    def _check_version(self, version):
        if version is not None and version != self.version:
            raise SourceConflict("Source changed in another request. Your editor text was retained; refresh to see the current source.")

    def _replaceable(self, version):
        self._check_version(version)
        if self._dirty():
            raise SourceConflict("Apply or discard changes before replacing source.")

    @staticmethod
    def _validate(text):
        if not isinstance(text, str):
            raise SourceError("Source must be text.")
        if not text.strip():
            raise SourceError("Source cannot be empty or whitespace only.")
        try:
            size = len(text.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise SourceError("Source must be valid UTF-8 text.") from exc
        if size > MAX_SOURCE_BYTES:
            raise SourceError("Source exceeds the 64 KiB (65536-byte) UTF-8 limit.")

    def _edit(self, text):
        if not isinstance(text, str):
            raise SourceError("Draft must be text.")
        if self.draft != text:
            self.draft = text
            self.draft_error = None
            self.version += 1

    def _accept(self, text, name):
        self.source = self.draft = text
        self.source_name = self.draft_name = name
        self.manual_pending = False
        self.draft_error = None
        self.revision += 1
        self.version += 1

    def manual(self, version=None):
        with self._lock:
            self._replaceable(version)
            self.draft = ""
            self.draft_name = "Manual input"
            self.manual_pending = True
            self.draft_error = None
            self.version += 1

    def edit(self, text, version=None):
        with self._lock:
            self._check_version(version)
            self._edit(text)

    def apply(self, text, version=None):
        with self._lock:
            self._check_version(version)
            self._edit(text)  # Retain rejected edits even if autosave has not arrived.
            self._validate(self.draft)
            if self.draft_error:
                raise SourceError(self.draft_error)
            if not self._dirty():
                raise SourceConflict("There are no changes to apply.")
            self._accept(self.draft, self.draft_name)

    def discard(self, version=None):
        with self._lock:
            self._check_version(version)
            self.draft = self.source or ""
            self.draft_name = self.source_name if self.source is not None else "Manual input"
            self.manual_pending = False
            self.draft_error = None
            self.version += 1

    def load(self, name, text, version=None, invalid_reason=None):
        with self._lock:
            self._replaceable(version)
            try:
                if invalid_reason:
                    raise SourceError(invalid_reason)
                self._validate(text)
            except SourceError:
                # An upload rejection changes only the draft, never applied state.
                if isinstance(text, str):
                    self.draft = text
                    self.draft_name = name
                    self.manual_pending = True
                    self.draft_error = invalid_reason
                    self.version += 1
                raise
            self._accept(text, name)

    def require_applied_source(self, version=None):
        with self._lock:
            self._check_version(version)
            if self._dirty():
                raise SourceConflict("Apply or discard changes before running a tool.")
            if self.source is None:
                raise SourceConflict("Apply or load source before running a tool.")
            return self.source, self.revision

    def snapshot(self):
        with self._lock:
            return {
                "source": self.source, "source_name": self.source_name,
                "revision": self.revision, "version": self.version,
                "draft": self.draft, "draft_name": self.draft_name,
                "dirty": self._dirty(), "max_source_bytes": MAX_SOURCE_BYTES,
            }
