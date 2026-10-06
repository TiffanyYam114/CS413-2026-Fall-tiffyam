"""Canned constructor expressions, supplied as data rather than executable code."""
EXAMPLES = {
    "factorial": ("Factorial (canned)", '''# Factorial of 5: D0Vint(arg1=120).
D0Eapp(
    D0Efix("fact", "n",
        D0Eif0(D0Eop2("<=", D0Evar("n"), D0Eint(0)),
            D0Eint(1),
            D0Eop2("*", D0Evar("n"),
                D0Eapp(D0Evar("fact"),
                    D0Eop2("-", D0Evar("n"), D0Eint(1))))
        )
    ),
    D0Eint(5)
)'''),
    "fibonacci": ("Fibonacci (canned)", '''# Fibonacci of 10: D0Vint(arg1=55).
D0Eapp(
    D0Efix("fib", "n",
        D0Eif0(D0Eop2("<=", D0Evar("n"), D0Eint(1)),
            D0Evar("n"),
            D0Eop2("+",
                D0Eapp(D0Evar("fib"),
                    D0Eop2("-", D0Evar("n"), D0Eint(1))),
                D0Eapp(D0Evar("fib"),
                    D0Eop2("-", D0Evar("n"), D0Eint(2))))
        )
    ),
    D0Eint(10)
)'''),
}
