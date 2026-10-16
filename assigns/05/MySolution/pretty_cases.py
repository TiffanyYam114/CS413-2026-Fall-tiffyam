"""Shared pretty-printing inputs and explicit expected outputs."""

import lambda1_vp as ast


# Shared inputs and explicit expected results for the two independent suites.
CASES = [
    (ast.D0Eint(0), "0"),
    (ast.D0Eint(-42), "-42"),
    (ast.D0Eint(10**100), "1" + "0" * 100),
    (ast.D0Ebtf(True), "true"),
    (ast.D0Ebtf(False), "false"),
    (ast.D0Evar("_name42"), "_name42"),
    (ast.D0Eop1("+1", ast.D0Eint(4)), "(+1 4)"),
    (ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)), "(x + 1)"),
    (ast.D0Elam("x", ast.D0Evar("x")), "(lam x. x)"),
    (ast.D0Efix("f", "x", ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("x"))),
     "(fix f(x). (f x))"),
    (ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(4)), "(f 4)"),
    (ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), ast.D0Eint(2)),
     "(if true then 1 else 2)"),
    (ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), "(let x = 3 in x)"),
    (ast.D0Epair(ast.D0Eint(1), ast.D0Ebtf(False)), "(pair 1 false)"),
    (ast.D0Epfst(ast.D0Epair(ast.D0Eint(1), ast.D0Eint(2))),
     "(fst (pair 1 2))"),
    (ast.D0Epsnd(ast.D0Epair(ast.D0Eint(1), ast.D0Eint(2))),
     "(snd (pair 1 2))"),
    (ast.D0Eapp(ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
                ast.D0Eint(4)), "((lam x. (x + 1)) 4)"),
    (ast.D0Eop2("/", ast.D0Eint(1), ast.D0Eint(0)), "(1 / 0)"),
    (ast.D0Eop1("custom", ast.D0Evar("free")), "(custom free)"),
    (ast.D0Eop2("custom", ast.D0Eint(1), ast.D0Eint(2)), "(1 custom 2)"),
]
