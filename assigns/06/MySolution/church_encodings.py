"""Closed Church combinator builders; no evaluation or host arithmetic.

Uppercase names are Python builders, not target primitives. Calling one
returns an expanded Var/Lam/App tree. AND and OR take a boolean followed by
a *thunk* for the right operand, so they short-circuit under call-by-value.
See CHURCH_ENCODINGS.md for interfaces, formulas, and predecessor details.
"""

from __future__ import annotations

if __package__:
    from .target_ast import App, Lam, Term, Var, all_names, fresh_name
else:
    from target_ast import App, Lam, Term, Var, all_names, fresh_name


def apply(fn: Term, *arguments: Term) -> Term:
    """Left-associated application; preserves free variables and input trees."""
    for argument in arguments:
        fn = App(fn, argument)
    return fn


def _lam(names: tuple[str, ...], body: Term) -> Term:
    for name in reversed(names):
        body = Lam(name, body)
    return body


def delay(term: Term) -> Lam:
    """Wrap an expression in a fresh unused parameter, including open terms."""
    return Lam(fresh_name("u", all_names(term)), term)


def I() -> Term:
    return Lam("w", Var("w"))


def TRUE() -> Term:
    return _lam(("t", "f"), Var("t"))


def FALSE() -> Term:
    return _lam(("t", "f"), Var("f"))


def NUM(n: int) -> Term:
    """Encode a natural literal; this is the only numeric host-side loop."""
    if type(n) is not int or n < 0:
        raise ValueError("Church numeral requires a nonnegative integer")
    body: Term = Var("z")
    for _ in range(n):
        body = App(Var("s"), body)
    return _lam(("s", "z"), body)


def PAIR() -> Term:
    return _lam(("a", "b", "p"), apply(Var("p"), Var("a"), Var("b")))


def FST() -> Term:
    return Lam("p", apply(Var("p"), TRUE()))


def SND() -> Term:
    return Lam("p", apply(Var("p"), FALSE()))


def Z() -> Term:
    inner = Lam("x", apply(Var("g"), Lam("v", apply(Var("x"), Var("x"), Var("v")))))
    return Lam("g", App(inner, inner))


def SUCC() -> Term:
    return _lam(("n", "s", "z"), apply(Var("s"), apply(Var("n"), Var("s"), Var("z"))))


def PRED() -> Term:
    # Iterate (previous, current) -> (current, current + 1), from (0, 0).
    step = Lam("p", apply(PAIR(), apply(SND(), Var("p")),
                          apply(SUCC(), apply(SND(), Var("p")))))
    seed = apply(PAIR(), NUM(0), NUM(0))
    return Lam("n", apply(FST(), apply(Var("n"), step, seed)))


def ISZERO() -> Term:
    return Lam("n", apply(Var("n"), Lam("unused", FALSE()), TRUE()))


def ADD() -> Term:
    return _lam(("m", "n", "s", "z"),
                apply(Var("m"), Var("s"), apply(Var("n"), Var("s"), Var("z"))))


def SUB() -> Term:
    return _lam(("m", "n"), apply(Var("n"), PRED(), Var("m")))


def MUL() -> Term:
    return _lam(("m", "n", "s", "z"),
                apply(Var("m"), apply(Var("n"), Var("s")), Var("z")))


def NOT() -> Term:
    return Lam("b", apply(Var("b"), FALSE(), TRUE()))


def IF() -> Term:
    """Takes a boolean and two thunks; forces only the chosen thunk."""
    return _lam(("c", "t", "f"), apply(Var("c"), Var("t"), Var("f"), I()))


def AND() -> Term:
    """AND boolean right_thunk; the right thunk is forced only if true."""
    return _lam(("p", "q"), apply(IF(), Var("p"), Var("q"), delay(FALSE())))


def OR() -> Term:
    """OR boolean right_thunk; the right thunk is forced only if false."""
    return _lam(("p", "q"), apply(IF(), Var("p"), delay(TRUE()), Var("q")))


def LE() -> Term:
    return _lam(("m", "n"), apply(ISZERO(), apply(SUB(), Var("m"), Var("n"))))


def GE() -> Term:
    return _lam(("m", "n"), apply(LE(), Var("n"), Var("m")))


def LT() -> Term:
    return _lam(("m", "n"), apply(NOT(), apply(LE(), Var("n"), Var("m"))))


def GT() -> Term:
    return _lam(("m", "n"), apply(NOT(), apply(LE(), Var("m"), Var("n"))))


def EQ() -> Term:
    # The thunk binder is fresh against both free numeric variables.
    return _lam(("m", "n"), apply(AND(), apply(LE(), Var("m"), Var("n")),
                                  delay(apply(LE(), Var("n"), Var("m")))))


def NE() -> Term:
    return _lam(("m", "n"), apply(NOT(), apply(EQ(), Var("m"), Var("n"))))
