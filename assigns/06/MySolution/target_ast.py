"""Pure lambda terms, safe substitution, and shared call-by-value evaluation.

Target execution accepts closed terms only; all other term operations also
support open terms. Only target beta-value contractions consume the budget.
Source evaluation is unbounded and uses lexical closures in the same machine.
The machine uses an explicit stack and never evaluates beneath a lambda.

Source AST dispatch and free-variable rules are adapted from Assignment 5's
lambda1_vp.py. That supplied module is imported unchanged, never evaluated.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Literal


def _check_name(name: str) -> None:
    if not isinstance(name, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
        raise ValueError(f"invalid identifier: {name!r}")


class Term:
    """Base class; the only supported concrete forms are Var, Lam, App."""

    def __str__(self) -> str:
        return pretty(self)


@dataclass(frozen=True)
class Var(Term):
    name: str

    def __post_init__(self) -> None:
        _check_name(self.name)


@dataclass(frozen=True)
class Lam(Term):
    name: str
    body: Term

    def __post_init__(self) -> None:
        _check_name(self.name)
        _check_term(self.body)


@dataclass(frozen=True)
class App(Term):
    fn: Term
    arg: Term

    def __post_init__(self) -> None:
        _check_term(self.fn)
        _check_term(self.arg)


def _check_term(term: Term) -> None:
    if type(term) not in (Var, Lam, App):
        raise TypeError(f"expected Var, Lam, or App; got {type(term).__name__}")


def pretty(term: Term) -> str:
    """Print x, (lam x. body), or (fn arg)."""
    _check_term(term)
    match term:
        case Var(name):
            return name
        case Lam(name, body):
            return f"(lam {name}. {pretty(body)})"
        case App(fn, arg):
            return f"({pretty(fn)} {pretty(arg)})"


def free_vars(term: Term) -> frozenset[str]:
    """Names not bound by an enclosing lambda."""
    _check_term(term)
    match term:
        case Var(name):
            return frozenset({name})
        case Lam(name, body):
            return free_vars(body) - {name}
        case App(fn, arg):
            return free_vars(fn) | free_vars(arg)


def all_names(term: Term) -> frozenset[str]:
    """Both bound and free names, for conservative capture avoidance."""
    _check_term(term)
    match term:
        case Var(name):
            return frozenset({name})
        case Lam(name, body):
            return all_names(body) | {name}
        case App(fn, arg):
            return all_names(fn) | all_names(arg)


def fresh_name(binder: str, unavailable: Iterable[str]) -> str:
    """Return binder_1, binder_2, ... with the smallest available suffix.

    The supplied binder is the literal prefix: for y_1, candidates are
    y_1_1, y_1_2, ... . No global counter or reserved source names are used.
    """
    _check_name(binder)
    used = set(unavailable)
    suffix = 1
    while f"{binder}_{suffix}" in used:
        suffix += 1
    return f"{binder}_{suffix}"


def substitute(term: Term, name: str, replacement: Term) -> Term:
    """Return term[name := replacement], replacing only free occurrences.

    Rename a conflicting binder using the smallest positive suffix absent
    from all names in its body and the replacement, and the substituted name.
    Inputs are immutable and are never changed.
    """
    _check_term(term)
    _check_term(replacement)
    _check_name(name)
    replacement_fv = free_vars(replacement)

    def walk(current: Term) -> Term:
        match current:
            case Var(x):
                return replacement if x == name else current
            case App(fn, arg):
                return App(walk(fn), walk(arg))
            case Lam(x, body):
                if x == name or name not in free_vars(body):
                    return current
                if x in replacement_fv:
                    fresh = fresh_name(x, all_names(body) | all_names(replacement) | {name, x})
                    body = substitute(body, x, Var(fresh))
                    return Lam(fresh, walk(body))
                return Lam(x, walk(body))

    return walk(term)


@dataclass(frozen=True)
class EvaluationResult:
    status: Literal["completed", "exhausted"]
    value: object
    steps: int

    @property
    def completed(self) -> bool:
        return self.status == "completed"


@dataclass(frozen=True)
class _SourceClosure:
    parameter: str
    body: object
    environment: dict[str, object]
    recursive_name: str | None = None


def _source_module():
    # Support both `from MySolution.target_ast ...` and direct script imports.
    if __package__:
        from . import lambda1_vp
    else:
        import lambda1_vp
    return lambda1_vp


def evaluate(expression: object, max_steps: int = 10000) -> EvaluationResult:
    """Evaluate a target term or supplied source AST with one explicit machine.

    Target results are Lam nodes; source data results are Python int, bool,
    or pairs (tuples). Source functions are internal lexical closures. Source
    primitives run only for source nodes, never for target terms. Source
    evaluation is unbounded and reports zero target beta-value steps.

    Open target execution raises ValueError, including for free variables
    underneath lambdas. A target lambda completes even at budget zero.
    Exhaustion returns value=None when a further contraction is required.
    """
    if type(max_steps) is not int or max_steps < 0:
        raise ValueError("max_steps must be a nonnegative integer")
    target = isinstance(expression, Term)
    if target:
        _check_term(expression)
        names = free_vars(expression)
        if names:
            raise ValueError(f"cannot execute open target term: {', '.join(sorted(names))}")
        source = None
    else:
        source = _source_module()
        if not isinstance(expression, source.D0E000):
            raise TypeError("expected a target term or source AST")

    current = expression
    environment: dict[str, object] = {}
    stack: list[tuple] = []
    steps = 0
    returning = False
    value: object = None

    while True:
        if not returning:
            if isinstance(current, (Var, Lam, App)):
                match current:
                    case Var(name):
                        raise ValueError(f"unbound target variable: {name}")
                    case Lam():
                        value = current
                    case App(fn, arg):
                        stack.append(("function", arg, environment))
                        current = fn
                        continue
            elif source is not None:
                match current:
                    case source.D0Eint(n):
                        if n < 0:
                            raise ValueError("negative source literal is unsupported")
                        value = n
                    case source.D0Ebtf(b):
                        value = b
                    case source.D0Evar(name):
                        if name not in environment:
                            raise ValueError(f"unbound source variable: {name}")
                        value = environment[name]
                    case source.D0Elam(name, body):
                        value = _SourceClosure(name, body, environment)
                    case source.D0Efix(fn, name, body):
                        value = _SourceClosure(name, body, environment, fn)
                    case source.D0Eapp(fn, arg):
                        stack.append(("function", arg, environment))
                        current = fn
                        continue
                    case source.D0Elet(name, init, body):
                        stack.append(("let", name, body, environment))
                        current = init
                        continue
                    case source.D0Eif0(cond, yes, no):
                        stack.append(("if", yes, no, environment))
                        current = cond
                        continue
                    case source.D0Epair(left, right):
                        stack.append(("pair_left", right, environment))
                        current = left
                        continue
                    case source.D0Epfst(pair) | source.D0Epsnd(pair):
                        stack.append(("projection", 0 if isinstance(current, source.D0Epfst) else 1))
                        current = pair
                        continue
                    case source.D0Eop1(op, operand):
                        if op != "not":
                            raise ValueError(f"unsupported unary operator: {op}")
                        stack.append(("not",))
                        current = operand
                        continue
                    case source.D0Eop2(op, left, right):
                        if op not in {"+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "and", "or"}:
                            raise ValueError(f"unsupported binary operator: {op}")
                        stack.append(("binary_left", op, right, environment))
                        current = left
                        continue
                    case _:
                        raise TypeError(f"unsupported source expression: {type(current).__name__}")
            else:
                raise TypeError("non-target node during target execution")
            returning = True

        if not stack:
            return EvaluationResult("completed", value, steps)

        frame = stack.pop()
        match frame:
            case ("function", arg, saved_env):
                stack.append(("argument", value))
                current, environment = arg, saved_env
                returning = False
            case ("argument", fn):
                if isinstance(fn, Lam):
                    if not isinstance(value, Lam):
                        raise TypeError("target argument must be a lambda value")
                    if steps == max_steps:
                        return EvaluationResult("exhausted", None, steps)
                    current = substitute(fn.body, fn.name, value)
                    steps += 1
                elif isinstance(fn, _SourceClosure):
                    environment = dict(fn.environment)
                    if fn.recursive_name is not None:
                        environment[fn.recursive_name] = fn
                    # Insert parameter last: it shadows a coincident fix name.
                    environment[fn.parameter] = value
                    current = fn.body
                else:
                    raise TypeError("application requires a function")
                returning = False
            case ("let", name, body, saved_env):
                environment = {**saved_env, name: value}
                current = body
                returning = False
            case ("if", yes, no, saved_env):
                current = yes if value else no
                environment = saved_env
                returning = False
            case ("pair_left", right, saved_env):
                stack.append(("pair_right", value))
                current, environment = right, saved_env
                returning = False
            case ("pair_right", left):
                value = (left, value)
            case ("projection", index):
                value = value[index]
            case ("not",):
                value = not value
            case ("binary_left", op, right, saved_env):
                if (op == "and" and not value) or (op == "or" and value):
                    continue
                stack.append(("binary_right", op, value))
                current, environment = right, saved_env
                returning = False
            case ("binary_right", op, left):
                match op:
                    case "+": value = left + value
                    case "-": value = max(left - value, 0)
                    case "*": value = left * value
                    case "<": value = left < value
                    case "<=": value = left <= value
                    case ">": value = left > value
                    case ">=": value = left >= value
                    case "==": value = left == value
                    case "!=": value = left != value
                    case "and" | "or": pass  # Selected right boolean is the result.
