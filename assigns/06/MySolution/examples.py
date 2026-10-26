"""Source AST examples and explicit expectations; no parsing or evaluation."""

from dataclasses import dataclass

if __package__:
    from . import lambda1_vp as s
    from .decoders import DataKind
else:
    import lambda1_vp as s
    from decoders import DataKind


@dataclass(frozen=True)
class Example:
    name: str
    description: str
    expression: s.d0exp
    kind: DataKind | None
    expected: object


def loop():
    return s.D0Eapp(s.D0Efix("loop", "x", s.D0Eapp(s.D0Evar("loop"), s.D0Evar("x"))), s.D0Eint(0))


def factorial():
    n = s.D0Evar("n")
    return s.D0Efix("fact", "n", s.D0Eif0(
        s.D0Eop2("==", n, s.D0Eint(0)), s.D0Eint(1),
        s.D0Eop2("*", n, s.D0Eapp(s.D0Evar("fact"), s.D0Eop2("-", n, s.D0Eint(1))))))


def fibonacci():
    n = s.D0Evar("n")
    return s.D0Efix("fib", "n", s.D0Eif0(
        s.D0Eop2("<=", n, s.D0Eint(1)), n,
        s.D0Eop2("+", s.D0Eapp(s.D0Evar("fib"), s.D0Eop2("-", n, s.D0Eint(1))),
                 s.D0Eapp(s.D0Evar("fib"), s.D0Eop2("-", n, s.D0Eint(2))))))


def examples() -> list[Example]:
    pair = s.D0Epair(s.D0Eint(2), s.D0Ebtf(True))
    return [
        Example("DEMO-01", "2 + 3 * 4", s.D0Eop2("+", s.D0Eint(2), s.D0Eop2("*", s.D0Eint(3), s.D0Eint(4))), "num", 14),
        Example("DEMO-02", "2 - 5", s.D0Eop2("-", s.D0Eint(2), s.D0Eint(5)), "num", 0),
        Example("DEMO-03", "if 2 <= 3 then 7 else 9", s.D0Eif0(s.D0Eop2("<=", s.D0Eint(2), s.D0Eint(3)), s.D0Eint(7), s.D0Eint(9)), "num", 7),
        Example("DEMO-04", "let x = 3 in (lam y. x + y) 4", s.D0Elet("x", s.D0Eint(3), s.D0Eapp(s.D0Elam("y", s.D0Eop2("+", s.D0Evar("x"), s.D0Evar("y"))), s.D0Eint(4))), "num", 7),
        Example("DEMO-05", "fst (pair 2 true)", s.D0Epfst(pair), "num", 2),
        Example("DEMO-06", "snd (pair 2 true)", s.D0Epsnd(pair), "bool", True),
        Example("DEMO-07", "(lam f. f 3) (lam x. x + 1)", s.D0Eapp(s.D0Elam("f", s.D0Eapp(s.D0Evar("f"), s.D0Eint(3))), s.D0Elam("x", s.D0Eop2("+", s.D0Evar("x"), s.D0Eint(1)))), "num", 4),
        Example("DEMO-08", "if true then 1 else LOOP", s.D0Eif0(s.D0Ebtf(True), s.D0Eint(1), loop()), "num", 1),
        Example("DEMO-09", "(lam x. 0) LOOP", s.D0Eapp(s.D0Elam("x", s.D0Eint(0)), loop()), None, "budget exhaustion"),
        Example("DEMO-10", "factorial(4)", s.D0Eapp(factorial(), s.D0Eint(4)), "num", 24),
        Example("DEMO-11", "Fibonacci(5)", s.D0Eapp(fibonacci(), s.D0Eint(5)), "num", 5),
        Example("DEMO-12", "LOOP", loop(), None, "budget exhaustion"),
        Example("DEMO-13", "true and false", s.D0Eop2("and", s.D0Ebtf(True), s.D0Ebtf(False)), "bool", False),
        Example("DEMO-14", "false or true", s.D0Eop2("or", s.D0Ebtf(False), s.D0Ebtf(True)), "bool", True),
        Example("EXTRA-01", "pair (pair 2 true) 3", s.D0Epair(pair, s.D0Eint(3)), (("num", "bool"), "num"), ((2, True), 3)),
        Example("EXTRA-02", "false and LOOP", s.D0Eop2("and", s.D0Ebtf(False), loop()), "bool", False),
        Example("EXTRA-03", "true or LOOP", s.D0Eop2("or", s.D0Ebtf(True), loop()), "bool", True),
    ]
