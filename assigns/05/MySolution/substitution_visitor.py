"""Single, capture-avoiding substitution using the supplied visitor interface."""

from functools import wraps

from lambda1_vp import *


class AllNamesVisitor(FreeVariableVisitor):
    """Collect variable occurrences and binder names, including shadowed names."""

    def visit_lam(self, dexp: D0Elam) -> frozenset[str]:
        return dexp.arg2.accept(self) | {dexp.arg1}

    def visit_fix(self, dexp: D0Efix) -> frozenset[str]:
        return dexp.arg3.accept(self) | {dexp.arg1, dexp.arg2}

    def visit_let(self, dexp: D0Elet) -> frozenset[str]:
        return dexp.arg2.accept(self) | dexp.arg3.accept(self) | {dexp.arg1}


def _with_context(method):
    """Reserve all input names once per root accept, even for visitor reuse."""
    @wraps(method)
    def visit(self, expression):
        if self._used is not None:
            return method(self, expression)
        self._used = set(expression.accept(AllNamesVisitor()))
        self._used.update(self.replacement.accept(AllNamesVisitor()))
        self._used.add(self.variable)
        try:
            return method(self, expression)
        finally:
            self._used = None
    return visit


class SubstitutionVisitor(D0ExpVisitor[d0exp]):
    """Replace free occurrences; insert replacement without traversing it.

    Fresh names use the smallest available positive suffix: name_1, name_2, ...
    All original/replacement names, the target, and generated names are reserved.
    Each root accept starts a fresh context, so this visitor can be reused.
    """

    def __init__(self, variable: str, replacement: d0exp):
        self.variable = variable
        self.replacement = replacement
        self._replacement_fv = d0exp_fvset(replacement)
        self._used: set[str] | None = None

    def _fresh(self, name: str) -> str:
        index = 1
        while f"{name}_{index}" in self._used:
            index += 1
        result = f"{name}_{index}"
        self._used.add(result)
        return result

    def _rename(self, body: d0exp, old: str, new: str) -> d0exp:
        # Substitution by a globally fresh variable is scope-aware renaming.
        visitor = SubstitutionVisitor(old, D0Evar(new))
        visitor._used = self._used
        return body.accept(visitor)

    def _scope(self, names: list[str], body: d0exp) -> tuple[list[str], d0exp]:
        if self.variable in names or self.variable not in d0exp_fvset(body):
            return names, body
        renamed = []
        # Equal fix binders receive the same fresh name, preserving shadowing.
        mapping = {}
        for name in names:
            if name not in mapping:
                fresh = self._fresh(name) if name in self._replacement_fv else name
                mapping[name] = fresh
                if fresh != name:
                    body = self._rename(body, name, fresh)
            renamed.append(mapping[name])
        return renamed, body.accept(self)

    @_with_context
    def visit_int(self, dexp: D0Eint) -> d0exp:
        return dexp

    @_with_context
    def visit_btf(self, dexp: D0Ebtf) -> d0exp:
        return dexp

    @_with_context
    def visit_var(self, dexp: D0Evar) -> d0exp:
        return self.replacement if dexp.arg1 == self.variable else dexp

    @_with_context
    def visit_op1(self, dexp: D0Eop1) -> d0exp:
        return D0Eop1(dexp.name, dexp.arg1.accept(self))

    @_with_context
    def visit_op2(self, dexp: D0Eop2) -> d0exp:
        return D0Eop2(dexp.name, dexp.arg1.accept(self), dexp.arg2.accept(self))

    @_with_context
    def visit_lam(self, dexp: D0Elam) -> d0exp:
        names, body = self._scope([dexp.arg1], dexp.arg2)
        return D0Elam(names[0], body)

    @_with_context
    def visit_fix(self, dexp: D0Efix) -> d0exp:
        names, body = self._scope([dexp.arg1, dexp.arg2], dexp.arg3)
        return D0Efix(names[0], names[1], body)

    @_with_context
    def visit_app(self, dexp: D0Eapp) -> d0exp:
        return D0Eapp(dexp.arg1.accept(self), dexp.arg2.accept(self))

    @_with_context
    def visit_if0(self, dexp: D0Eif0) -> d0exp:
        return D0Eif0(dexp.arg1.accept(self), dexp.arg2.accept(self), dexp.arg3.accept(self))

    @_with_context
    def visit_let(self, dexp: D0Elet) -> d0exp:
        initializer = dexp.arg2.accept(self)
        names, body = self._scope([dexp.arg1], dexp.arg3)
        return D0Elet(names[0], initializer, body)

    @_with_context
    def visit_pair(self, dexp: D0Epair) -> d0exp:
        return D0Epair(dexp.arg1.accept(self), dexp.arg2.accept(self))

    @_with_context
    def visit_pfst(self, dexp: D0Epfst) -> d0exp:
        return D0Epfst(dexp.arg1.accept(self))

    @_with_context
    def visit_psnd(self, dexp: D0Epsnd) -> d0exp:
        return D0Epsnd(dexp.arg1.accept(self))


def d0exp_substitute(dexp: d0exp, variable: str, replacement: d0exp) -> d0exp:
    """Return expression[variable := replacement] without mutating either input."""
    return dexp.accept(SubstitutionVisitor(variable, replacement))
