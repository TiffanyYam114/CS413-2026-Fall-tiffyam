"""Framework-independent contract for replaceable language tools."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Outcome(StrEnum):
    SUCCESS = "success"
    INPUT_ERROR = "input_error"
    LANGUAGE_ERROR = "language_error"
    RUNTIME_ERROR = "runtime_error"
    BACKEND_FAILURE = "backend_failure"
    NOT_IMPLEMENTED = "not_implemented"


OPERATIONS = ("lint", "interpret", "typecheck", "compile", "execute")
WORKER_TIMEOUT_SECONDS = 3.0
MAX_OUTPUT_CHARS = 8192


@dataclass(frozen=True)
class GeneratedCode:
    format: str
    code: str


@dataclass(frozen=True)
class Artifact:
    """Reserved for real compiler output, tied to its applied source revision."""
    revision: int
    format: str
    code: str


@dataclass(frozen=True)
class BackendReply:
    outcome: Outcome
    text: str
    free_variables: frozenset[str] | None = None
    generated_code: GeneratedCode | None = None


@dataclass(frozen=True)
class Result:
    operation: str
    revision: int
    outcome: Outcome
    text: str
    free_variables: frozenset[str] | None = None


class Backend(Protocol):
    """Each operation must complete within a documented execution bound."""
    def lint(self, source: str) -> BackendReply: ...
    def interpret(self, source: str) -> BackendReply: ...
    def typecheck(self, source: str) -> BackendReply: ...
    def compile(self, source: str) -> BackendReply: ...
    def execute(self, artifact: Artifact) -> BackendReply: ...
