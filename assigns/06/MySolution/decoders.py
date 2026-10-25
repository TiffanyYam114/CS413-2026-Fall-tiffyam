"""Bounded pure-context observation through the existing shared evaluator.

Kinds are 'nat', 'bool', or a tuple of two kinds for a (possibly nested) pair.
An observation budget is shared by every projection and component context.
Python inspects final shapes only; it never executes encoded operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

if __package__:
    from . import church_encodings as c
    from .target_ast import App, EvaluationResult, Lam, Term, Var, evaluate, free_vars
else:
    import church_encodings as c
    from target_ast import App, EvaluationResult, Lam, Term, Var, evaluate, free_vars

type DataKind = Literal["nat", "bool"] | tuple[DataKind, DataKind]


@dataclass(frozen=True)
class ObservationResult:
    status: Literal["completed", "exhausted", "malformed"]
    value: object
    steps: int
    message: str = ""

    @property
    def completed(self) -> bool:
        return self.status == "completed"


@dataclass(frozen=True)
class PipelineResult:
    execution: EvaluationResult
    observation: ObservationResult | None


def _budget(value: int) -> None:
    if type(value) is not int or value < 0:
        raise ValueError("budget must be a nonnegative integer")


def _kind(kind: DataKind) -> None:
    if kind in ("nat", "bool"):
        return
    if isinstance(kind, tuple) and len(kind) == 2:
        _kind(kind[0])
        _kind(kind[1])
        return
    raise ValueError("expected kind 'nat', 'bool', or a pair of kinds")


class _Malformed(Exception):
    pass


class _Exhausted(Exception):
    pass


def _alpha_key(term: Term, binders: tuple[str, ...] = ()) -> tuple:
    """Inspect bound-variable structure; this performs no reduction."""
    match term:
        case Var(name):
            return ("bound", binders.index(name)) if name in binders else ("free", name)
        case Lam(name, body):
            return ("lam", _alpha_key(body, (name,) + binders))
        case App(fn, arg):
            return ("app", _alpha_key(fn, binders), _alpha_key(arg, binders))
    raise _Malformed("observation output contains a non-target node")


class _Observer:
    def __init__(self, budget: int):
        self.remaining = budget
        self.steps = 0

    def run(self, context: Term) -> Lam:
        try:
            result = evaluate(context, self.remaining)
        except (ValueError, TypeError) as error:
            raise _Malformed(str(error)) from error
        self.steps += result.steps
        self.remaining -= result.steps
        if not result.completed:
            raise _Exhausted("observation beta-value step budget exhausted")
        if not isinstance(result.value, Lam):
            raise _Malformed("observation did not return a lambda value")
        return result.value

    def decode(self, value: Lam, kind: DataKind) -> object:
        if kind == "nat":
            step = Lam("tail", Lam("c", Lam("z", App(Var("c"), Var("tail")))))
            base = Lam("c", Lam("z", Var("z")))
            spine = self.run(c.apply(value, step, base))
            count = 0
            while isinstance(spine, Lam) and isinstance(spine.body, Lam):
                outer, inner, body = spine.name, spine.body.name, spine.body.body
                if body == Var(inner):
                    return count
                if (outer == inner or not isinstance(body, App)
                        or body.fn != Var(outer) or not isinstance(body.arg, Lam)
                        or free_vars(body.arg)):
                    break
                spine = body.arg
                count += 1
            raise _Malformed("natural observation is not a finite STEP/BASE spine")
        if kind == "bool":
            yes = Lam("marker", Var("marker"))
            no = Lam("first", Lam("second", Var("first")))
            marker = self.run(c.apply(value, yes, no))
            key = _alpha_key(marker)
            if key == _alpha_key(yes):
                return True
            if key == _alpha_key(no):
                return False
            raise _Malformed("boolean observation did not select a recognized marker")
        # Observe the already evaluated pair by bounded projections, recursively.
        left = self.run(c.apply(c.FST(), value))
        first = self.decode(left, kind[0])
        right = self.run(c.apply(c.SND(), value))
        second = self.decode(right, kind[1])
        return (first, second)


def observe_value(value: Term, kind: DataKind, max_steps: int = 50000) -> ObservationResult:
    """Observe an already evaluated, closed lambda using one aggregate budget.

    Invalid budget/kind raises ValueError. Malformed values yield 'malformed'.
    Exhaustion yields 'exhausted', never a partial decoded value. Failure counts
    include all successful contractions before the failed observation context.
    """
    _budget(max_steps)
    _kind(kind)
    observer = _Observer(max_steps)
    try:
        if not isinstance(value, Lam) or free_vars(value):
            raise _Malformed("expected a closed target lambda value")
        decoded = observer.decode(value, kind)
        return ObservationResult("completed", decoded, observer.steps)
    except _Exhausted as error:
        return ObservationResult("exhausted", None, observer.steps, str(error))
    except _Malformed as error:
        return ObservationResult("malformed", None, observer.steps, str(error))


def observe_natural(value: Term, max_steps: int = 50000) -> ObservationResult:
    return observe_value(value, "nat", max_steps)


def observe_boolean(value: Term, max_steps: int = 50000) -> ObservationResult:
    return observe_value(value, "bool", max_steps)


def observe(term: Term, kind: DataKind, execution_budget: int = 50000,
            observation_budget: int = 50000) -> PipelineResult:
    """Evaluate once, then observe with an independent budget and step count."""
    _budget(execution_budget)
    _budget(observation_budget)
    _kind(kind)
    if not isinstance(term, Term):
        raise TypeError("observation requires a pure target term")
    execution = evaluate(term, execution_budget)
    observation = (observe_value(execution.value, kind, observation_budget)
                   if execution.completed else None)
    return PipelineResult(execution, observation)


def observe_pair(term: Term, kinds: tuple[DataKind, DataKind],
                 execution_budget: int = 50000, observation_budget: int = 50000) -> PipelineResult:
    """Evaluate a pair, project its values, and recursively observe components."""
    if not isinstance(kinds, tuple) or len(kinds) != 2:
        raise ValueError("pair observation requires two component kinds")
    return observe(term, kinds, execution_budget, observation_budget)
