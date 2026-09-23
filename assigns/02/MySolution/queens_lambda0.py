"""Eight queens, translated from original_ATS_eight_queens.md.

Representation
--------------
An ATS ``int8`` tuple is represented here by a (fixed length) pair-list:
``T0Mpair(column, rest)``, with ``T0Mint(-1)`` as the terminator.  Thus the
first pair is row 0 and each later pair is the next row.  A search state is
``(board, (row, (column, (solution_count, solutions))))``. ``solutions`` is
an object-language pair-list of completed boards. These are all object-language
values, not Python data structures used by the search.

``make_queens_term`` constructs one closed t0erm.  Its object-language
functions are:

* ``get`` and ``set``: the tuple operations in the ATS program;
* ``safe``: ATS's tail-recursive ``safety_test2`` (with ``safety_test1``
  inlined); and
* ``search``: the depth-first search from the ATS program.

The supplied lambda0.py already has the only primitive extensions this
translation needs: integer comparisons (<, >, ==, !=) return ``T0Mbtf``.
No Python function below searches for, filters, or counts solutions.
"""

from lambda0 import (
    T0M000, T0Mapp, T0Mbtf, T0Mfix, T0Mif0, T0Mint, T0Mlam,
    T0Mop1, T0Mop2, T0Mpair, T0Mpfst, T0Mpsnd, T0Mvar,
    t0erm_fvset,
)
import sys


def v(name): return T0Mvar(name)
def app(fun, arg): return T0Mapp(fun, arg)
def lam(name, body): return T0Mlam(name, body)
def let(name, value, body): return app(lam(name, body), value)
def pair(left, right): return T0Mpair(left, right)
def fst(term): return T0Mpfst(term)
def snd(term): return T0Mpsnd(term)
def op(name, left, right): return T0Mop2(name, left, right)
def neg(term): return T0Mop1("-", term)
def if_(condition, yes, no): return T0Mif0(condition, yes, no)
def call2(fun, a, b): return app(app(fun, a), b)


def state(board, row, column, count, solutions):
    return pair(board, pair(row, pair(column, pair(count, solutions))))


def board0(size):
    """An initial fixed-size board; values are overwritten before being read."""
    result = T0Mint(-1)
    for _ in range(size):
        result = pair(T0Mint(0), result)
    return result


def safety_test1_term(i0, j0, i1, j1):
    """The ATS safety_test1 expressed directly as a boolean LAMBDA0 term."""
    row_delta = op("-", i0, i1)
    col_delta = op("-", j0, j1)
    abs_row = if_(op("<", row_delta, T0Mint(0)), neg(row_delta), row_delta)
    abs_col = if_(op("<", col_delta, T0Mint(0)), neg(col_delta), col_delta)
    return if_(op("!=", j0, j1), op("!=", abs_row, abs_col), T0Mbtf(False))


class _Closure:
    """A lambda value plus its lexical environment for the extended evaluator."""
    def __init__(self, parameter, body, environment):
        self.parameter, self.body, self.environment = parameter, body, environment


class _FixClosure:
    """A recursive function value plus its lexical environment."""
    def __init__(self, function, parameter, body, environment):
        self.function, self.parameter = function, parameter
        self.body, self.environment = body, environment


def t0erm_cbv_evaluate0(term: T0M000) -> T0M000:
    """Evaluate lambda0 terms using environments instead of AST duplication.

    This is an extension of lambda0's evaluator, retained here because the
    assignment prohibits editing lambda0.py.  It preserves call-by-value and
    supports every constructor used by this translation.  Integer relational
    operations produce T0Mbtf values, as required for T0Mif0 conditions.
    """
    # The translated ATS program is tail-recursive, but Python does not
    # eliminate tail calls.  This evaluator's direct implementation therefore
    # needs headroom for the DFS continuation chain.
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 200_000))

    def evaluate(node, environment):
        if isinstance(node, (T0Mint, T0Mbtf)):
            return node
        if isinstance(node, T0Mvar):
            return environment[node.arg1]
        if isinstance(node, T0Mlam):
            return _Closure(node.arg1, node.arg2, environment.copy())
        if isinstance(node, T0Mfix):
            return _FixClosure(node.arg1, node.arg2, node.arg3, environment.copy())
        if isinstance(node, T0Mapp):
            function, argument = evaluate(node.arg1, environment), evaluate(node.arg2, environment)
            if isinstance(function, _Closure):
                call_environment = function.environment.copy()
                call_environment[function.parameter] = argument
                return evaluate(function.body, call_environment)
            if isinstance(function, _FixClosure):
                call_environment = function.environment.copy()
                call_environment[function.function] = function
                call_environment[function.parameter] = argument
                return evaluate(function.body, call_environment)
            raise TypeError("application expects a lambda or fixpoint")
        if isinstance(node, T0Mif0):
            condition = evaluate(node.arg1, environment)
            if not isinstance(condition, T0Mbtf):
                raise TypeError("condition expects a boolean")
            return evaluate(node.arg2 if condition.arg1 else node.arg3, environment)
        if isinstance(node, T0Mpair):
            return T0Mpair(evaluate(node.arg1, environment), evaluate(node.arg2, environment))
        if isinstance(node, T0Mpfst):
            value = evaluate(node.arg1, environment)
            if not isinstance(value, T0Mpair): raise TypeError("fst expects a pair")
            return value.arg1
        if isinstance(node, T0Mpsnd):
            value = evaluate(node.arg1, environment)
            if not isinstance(value, T0Mpair): raise TypeError("snd expects a pair")
            return value.arg2
        if isinstance(node, T0Mop1):
            value = evaluate(node.arg2, environment)
            if node.arg1 == "-" and isinstance(value, T0Mint): return T0Mint(-value.arg1)
            if node.arg1 == "+" and isinstance(value, T0Mint): return T0Mint(value.arg1)
            raise TypeError(f"invalid unary operation {node.arg1}")
        if isinstance(node, T0Mop2):
            left, right = evaluate(node.arg2, environment), evaluate(node.arg3, environment)
            if not isinstance(left, T0Mint) or not isinstance(right, T0Mint):
                raise TypeError(f"{node.arg1} expects integers")
            arithmetic = {"+": lambda: left.arg1 + right.arg1,
                          "-": lambda: left.arg1 - right.arg1,
                          "*": lambda: left.arg1 * right.arg1,
                          "/": lambda: left.arg1 // right.arg1,
                          "%": lambda: left.arg1 % right.arg1}
            comparisons = {"<": lambda: left.arg1 < right.arg1,
                           ">": lambda: left.arg1 > right.arg1,
                           "<=": lambda: left.arg1 <= right.arg1,
                           ">=": lambda: left.arg1 >= right.arg1,
                           "==": lambda: left.arg1 == right.arg1,
                           "!=": lambda: left.arg1 != right.arg1}
            if node.arg1 in arithmetic: return T0Mint(arithmetic[node.arg1]())
            if node.arg1 in comparisons: return T0Mbtf(comparisons[node.arg1]())
            raise TypeError(f"invalid binary operation {node.arg1}")
        raise TypeError(f"cannot evaluate {node}")
    result = evaluate(term, {})
    # Internal closures are evaluator implementation details.  A completed
    # program must expose a lambda0 value, never one of those closures.
    if not isinstance(result, T0M000):
        raise TypeError("top-level evaluation produced a function value")
    return result


def make_queens_term(size: int = 8) -> T0M000:
    """Build a closed search term for a positive board size (default: eight)."""
    if size < 1:
        raise ValueError("the translation supports positive board sizes")
    # get : (board, index) -> column
    bi = v("bi")
    get = T0Mfix("get", "bi",
        if_(op("==", snd(bi), T0Mint(0)), fst(fst(bi)),
            app(v("get"), pair(snd(fst(bi)), op("-", snd(bi), T0Mint(1)))))
    )

    # set : (board, (index, column)) -> board
    sij = v("sij")
    set_ = T0Mfix("set", "sij",
        if_(op("==", fst(snd(sij)), T0Mint(0)),
            pair(snd(snd(sij)), snd(fst(sij))),
            pair(fst(fst(sij)),
                 app(v("set"), pair(snd(fst(sij)),
                     pair(op("-", fst(snd(sij)), T0Mint(1)), snd(snd(sij)))))))
    )

    # safe : (row, (column, (board, last_row))) -> bool
    # abs(a-b) is written as: if a-b < 0 then -(a-b) else a-b.
    s = v("s")
    row, col = fst(s), fst(snd(s))
    board, last = fst(snd(snd(s))), snd(snd(snd(s)))
    old_col = app(v("get"), pair(board, last))
    conflict_free = safety_test1_term(row, col, last, old_col)
    safe = T0Mfix("safe", "s",
        if_(op(">=", last, T0Mint(0)),
            if_(conflict_free,
                app(v("safe"), pair(row, pair(col, pair(board,
                    op("-", last, T0Mint(1)))))),
                T0Mbtf(False)),
            T0Mbtf(True))
    )

    # search -> (count, solutions): store ATS's printed boards as data.
    q = v("q")
    bd, i = fst(q), fst(snd(q))
    j = fst(snd(snd(q)))
    nsol, solutions = fst(snd(snd(snd(q)))), snd(snd(snd(snd(q))))
    safe_call = app(v("safe"), pair(i, pair(j, pair(bd, op("-", i, T0Mint(1))))))
    bd1 = app(v("set"), pair(bd, pair(i, j)))
    next_column = app(v("search"), state(bd, i, op("+", j, T0Mint(1)), nsol, solutions))
    finished = app(v("search"), state(bd, i, op("+", j, T0Mint(1)),
                                        op("+", nsol, T0Mint(1)), pair(bd1, solutions)))
    next_row = app(v("search"), state(bd1, op("+", i, T0Mint(1)), T0Mint(0), nsol, solutions))
    backtrack = app(v("search"), state(bd, op("-", i, T0Mint(1)),
        op("+", app(v("get"), pair(bd, op("-", i, T0Mint(1)))), T0Mint(1)), nsol, solutions))
    search = T0Mfix("search", "q",
        if_(op("<", j, T0Mint(size)),
            if_(safe_call,
                if_(op("==", op("+", i, T0Mint(1)), T0Mint(size)), finished, next_row),
                next_column),
            if_(op(">", i, T0Mint(0)), backtrack, pair(nsol, solutions)))
    )

    # These lexical bindings substitute closed helper values before search runs.
    return let("get", get,
           let("set", set_,
           let("safe", safe,
           let("search", search,
               app(v("search"), state(board0(size), T0Mint(0), T0Mint(0),
                                      T0Mint(0), T0Mint(-1)))))))


def main():
    # Primitive-operation regression checks: comparisons feed T0Mif0 as booleans.
    assert t0erm_cbv_evaluate0(op("<", T0Mint(2), T0Mint(3))) == T0Mbtf(True)
    assert t0erm_cbv_evaluate0(if_(op("==", T0Mint(8), T0Mint(8)),
                                   T0Mint(1), T0Mint(0))) == T0Mint(1)
    term = make_queens_term()
    assert not t0erm_fvset(term), "the translated program must be closed"
    answer = t0erm_cbv_evaluate0(term)
    assert isinstance(answer, T0Mpair) and isinstance(answer.arg1, T0Mint)
    assert answer.arg1.arg1 == 92
    print(f"eight-queens solutions: {answer.arg1.arg1}")


if __name__ == "__main__":
    main()
