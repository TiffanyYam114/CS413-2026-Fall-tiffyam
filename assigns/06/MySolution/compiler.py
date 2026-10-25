"""Compositional source-to-Church compilation using the supplied visitor API.

No evaluation is performed. All source children (including unused branches)
are visited. See DESIGN.md for translation rules and the naming policy.
"""

from __future__ import annotations

if __package__:
    from . import church_encodings as church
    from . import lambda1_vp as source
    from .target_ast import App, Lam, Term, Var
else:
    import church_encodings as church
    import lambda1_vp as source
    from target_ast import App, Lam, Term, Var


class CompilationError(ValueError):
    """An unsupported source literal, operator, or expression form."""


_BINARY_BUILDERS = {
    "+": church.ADD, "-": church.SUB, "*": church.MUL,
    "<": church.LT, "<=": church.LE, ">": church.GT, ">=": church.GE,
    "==": church.EQ, "!=": church.NE,
}


class CompileVisitor(source.D0ExpVisitor[Term]):
    """Stateless visitor: a source expression maps directly to a target term."""

    def visit_int(self, dexp: source.D0Eint) -> Term:
        if type(dexp.arg1) is not int or dexp.arg1 < 0:
            raise CompilationError(f"unsupported natural-number literal: {dexp.arg1!r}")
        return church.NUM(dexp.arg1)

    def visit_btf(self, dexp: source.D0Ebtf) -> Term:
        return church.TRUE() if dexp.arg1 else church.FALSE()

    def visit_var(self, dexp: source.D0Evar) -> Term:
        return Var(dexp.arg1)

    def visit_lam(self, dexp: source.D0Elam) -> Term:
        return Lam(dexp.arg1, dexp.arg2.accept(self))

    def visit_app(self, dexp: source.D0Eapp) -> Term:
        return App(dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_let(self, dexp: source.D0Elet) -> Term:
        init = dexp.arg2.accept(self)
        body = dexp.arg3.accept(self)
        return App(Lam(dexp.arg1, body), init)

    def visit_fix(self, dexp: source.D0Efix) -> Term:
        # Nested lambdas preserve the parameter's priority if names coincide.
        body = dexp.arg3.accept(self)
        return App(church.Z(), Lam(dexp.arg1, Lam(dexp.arg2, body)))

    def visit_if0(self, dexp: source.D0Eif0) -> Term:
        condition = dexp.arg1.accept(self)
        yes = dexp.arg2.accept(self)
        no = dexp.arg3.accept(self)
        return church.apply(condition, church.delay(yes), church.delay(no), church.I())

    def visit_pair(self, dexp: source.D0Epair) -> Term:
        return church.apply(church.PAIR(), dexp.arg1.accept(self), dexp.arg2.accept(self))

    def visit_pfst(self, dexp: source.D0Epfst) -> Term:
        return App(church.FST(), dexp.arg1.accept(self))

    def visit_psnd(self, dexp: source.D0Epsnd) -> Term:
        return App(church.SND(), dexp.arg1.accept(self))

    def visit_op1(self, dexp: source.D0Eop1) -> Term:
        if dexp.name != "not":
            raise CompilationError(f"unsupported unary operator: {dexp.name!r}")
        return App(church.NOT(), dexp.arg1.accept(self))

    def visit_op2(self, dexp: source.D0Eop2) -> Term:
        if dexp.name not in _BINARY_BUILDERS and dexp.name not in {"and", "or"}:
            raise CompilationError(f"unsupported binary operator: {dexp.name!r}")
        left = dexp.arg1.accept(self)
        right = dexp.arg2.accept(self)
        if dexp.name in {"and", "or"}:
            builder = church.AND if dexp.name == "and" else church.OR
            return church.apply(builder(), left, church.delay(right))
        return church.apply(_BINARY_BUILDERS[dexp.name](), left, right)


def compile_expr(source_expression: source.d0exp) -> Term:
    """Translate an open or closed source AST, preserving it and its free names.

    Unsupported syntax raises CompilationError even in dead branches and
    unapplied functions. Constructor argument shapes and typing are assumed
    valid, as permitted by the assignment.
    """
    if not isinstance(source_expression, source.D0E000):
        raise CompilationError(f"unsupported source expression: {type(source_expression).__name__}")
    try:
        return source_expression.accept(CompileVisitor())
    except TypeError as error:
        raise CompilationError(str(error)) from error
