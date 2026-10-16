"""Every concrete worked example from Tasks 1 and 2 of Assign05.md."""

from lambda1_vp import (
    D0Eint as Int, D0Evar as Var, D0Eop2 as Op,
    D0Elam as Lam, D0Efix as Fix, D0Eapp as App, D0Elet as Let,
)

x, y, z, f, n = (Var(name) for name in ("x", "y", "z", "f", "n"))

PRETTY_EXAMPLES = {
    "task1_lambda_application": (
        App(Lam("x", Op("+", x, Int(1))), Int(4)),
        "((lam x. (x + 1)) 4)",
    ),
    "task1_division_by_zero": (Op("/", Int(1), Int(0)), "(1 / 0)"),
}

# Input, target, replacement, expected AST, expected pretty output.
SUBSTITUTION_EXAMPLES = {
    "task2_free_variable": (
        Op("+", x, z), "x", Int(3), Op("+", Int(3), z), "(3 + z)",
    ),
    "task2_lambda_shadowing": (
        Lam("x", Op("+", x, y)), "x", Int(3),
        Lam("x", Op("+", x, y)), "(lam x. (x + y))",
    ),
    "task2_lambda_capture": (
        Lam("y", Op("+", x, y)), "x", y,
        Lam("y_1", Op("+", y, Var("y_1"))), "(lam y_1. (y + y_1))",
    ),
    "task2_let_shadowing": (
        Let("x", x, Op("+", x, y)), "x", Int(3),
        Let("x", Int(3), Op("+", x, y)), "(let x = 3 in (x + y))",
    ),
    "task2_let_capture": (
        Let("y", x, Op("+", x, y)), "x", y,
        Let("y_1", y, Op("+", y, Var("y_1"))), "(let y_1 = y in (y + y_1))",
    ),
    "task2_fix_capture": (
        Fix("f", "n", Op("+", x, App(f, n))), "x", f,
        Fix("f_1", "n", Op("+", f, App(Var("f_1"), n))),
        "(fix f_1(n). (f + (f_1 n)))",
    ),
    "task2_single_substitution": (
        x, "x", Op("+", x, Int(1)), Op("+", x, Int(1)), "(x + 1)",
    ),
}
