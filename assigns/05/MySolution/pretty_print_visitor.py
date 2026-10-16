from lambda1_vp import *


class PrettyPrintVisitor(D0ExpVisitor[str]):
    def visit_int(self, dexp: D0Eint) -> str:
        return str(dexp.arg1)

    def visit_btf(self, dexp: D0Ebtf) -> str:
        return "true" if dexp.arg1 else "false"

    def visit_var(self, dexp: D0Evar) -> str:
        return dexp.arg1

    def visit_op1(self, dexp: D0Eop1) -> str:
        return f"({dexp.name} {dexp.arg1.accept(self)})"

    def visit_op2(self, dexp: D0Eop2) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.name} {dexp.arg2.accept(self)})"

    def visit_lam(self, dexp: D0Elam) -> str:
        return f"(lam {dexp.arg1}. {dexp.arg2.accept(self)})"

    def visit_fix(self, dexp: D0Efix) -> str:
        return f"(fix {dexp.arg1}({dexp.arg2}). {dexp.arg3.accept(self)})"

    def visit_app(self, dexp: D0Eapp) -> str:
        return f"({dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_if0(self, dexp: D0Eif0) -> str:
        return (f"(if {dexp.arg1.accept(self)} then {dexp.arg2.accept(self)} else {dexp.arg3.accept(self)})")

    def visit_let(self, dexp: D0Elet) -> str:
        return (f"(let {dexp.arg1} = {dexp.arg2.accept(self)} in {dexp.arg3.accept(self)})")

    def visit_pair(self, dexp: D0Epair) -> str:
        return f"(pair {dexp.arg1.accept(self)} {dexp.arg2.accept(self)})"

    def visit_pfst(self, dexp: D0Epfst) -> str:
        return f"(fst {dexp.arg1.accept(self)})"

    def visit_psnd(self, dexp: D0Epsnd) -> str:
        return f"(snd {dexp.arg1.accept(self)})"


def d0exp_pretty(dexp: d0exp) -> str:
    return dexp.accept(PrettyPrintVisitor())