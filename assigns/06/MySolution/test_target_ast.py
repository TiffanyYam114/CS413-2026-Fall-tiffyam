"""Run from assigns/06 with python -m unittest MySolution.test_target_ast."""

import unittest

from .target_ast import (
    App, Lam, Var, all_names, evaluate, free_vars, fresh_name, pretty, substitute,
)
from . import lambda1_vp as s


class TargetOperationsTests(unittest.TestCase):
    def test_print_and_free_variables(self):
        term = Lam("x", App(Var("x"), Var("y")))
        self.assertEqual(pretty(term), "(lam x. (x y))")
        self.assertEqual(str(term), pretty(term))
        self.assertEqual(free_vars(term), {"y"})
        self.assertEqual(all_names(term), {"x", "y"})

    def test_identifiers_and_target_children(self):
        for name in ("", "1x", "x-y", "é"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                Var(name)
        with self.assertRaises(TypeError):
            Lam("x", s.D0Evar("x"))

    def test_smallest_positive_suffix(self):
        self.assertEqual(fresh_name("y", {"y", "y_1", "y_3"}), "y_2")
        self.assertEqual(fresh_name("y", {"y_2"}), "y_1")
        self.assertEqual(fresh_name("y_1", set()), "y_1_1")

    def test_capture_avoidance(self):
        original = Lam("y", Var("x"))
        result = substitute(original, "x", Var("y"))
        self.assertEqual(result, Lam("y_1", Var("y")))
        self.assertEqual(original, Lam("y", Var("x")))
        self.assertEqual(free_vars(result), {"y"})

    def test_renaming_avoids_bound_names_and_respects_shadowing(self):
        term = Lam("y", App(Var("x"), Lam("y_1", Var("y"))))
        self.assertEqual(
            substitute(term, "x", Var("y")),
            Lam("y_2", App(Var("y"), Lam("y_1", Var("y_2")))),
        )
        shadowed = Lam("x", App(Var("x"), Var("z")))
        self.assertEqual(substitute(shadowed, "x", Var("y")), shadowed)
        nested = Lam("y", App(Var("x"), Lam("y", Var("y"))))
        self.assertEqual(
            substitute(nested, "x", Var("y")),
            Lam("y_1", App(Var("y"), Lam("y", Var("y")))),
        )


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.identity = Lam("x", Var("x"))
        duplicator = Lam("x", App(Var("x"), Var("x")))
        self.omega = App(duplicator, duplicator)

    def test_weak_evaluation_and_zero_budget(self):
        term = Lam("unused", self.omega)
        result = evaluate(term, 0)
        self.assertTrue(result.completed)
        self.assertEqual(result.value, term)
        self.assertEqual(result.steps, 0)

    def test_budget_boundary(self):
        term = App(self.identity, self.identity)
        exhausted = evaluate(term, 0)
        self.assertEqual(exhausted.status, "exhausted")
        self.assertIsNone(exhausted.value)
        self.assertEqual(exhausted.steps, 0)
        result = evaluate(term, 1)
        self.assertTrue(result.completed)
        self.assertEqual(result.value, self.identity)
        self.assertEqual(result.steps, 1)

    def test_function_and_argument_are_evaluated_before_application(self):
        term = App(App(self.identity, self.identity), App(self.identity, self.identity))
        self.assertEqual(evaluate(term, 2).status, "exhausted")
        result = evaluate(term, 3)
        self.assertEqual(result.value, self.identity)
        self.assertEqual(result.steps, 3)
        self.assertEqual(evaluate(term, 3), result)

    def test_unused_divergent_argument_and_large_budget(self):
        term = App(Lam("unused", self.identity), self.omega)
        result = evaluate(term, 1500)
        self.assertEqual(result.status, "exhausted")
        self.assertEqual(result.steps, 1500)
        self.assertEqual(evaluate(self.omega, 12).steps, 12)

    def test_budget_validation_and_open_execution(self):
        for budget in (-1, 1.5, True):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                evaluate(self.identity, budget)
        with self.assertRaisesRegex(ValueError, "open target"):
            evaluate(Lam("x", Var("free")))

    def test_input_is_unchanged(self):
        term = App(self.identity, self.identity)
        before = pretty(term)
        evaluate(term)
        self.assertEqual(pretty(term), before)

    def test_source_scope_and_coincident_fix_names(self):
        term = s.D0Elet("x", s.D0Eint(3),
                       s.D0Eapp(s.D0Elam("y", s.D0Eop2("+", s.D0Evar("x"), s.D0Evar("y"))), s.D0Eint(4)))
        self.assertEqual(evaluate(term).value, 7)
        coincident = s.D0Eapp(s.D0Efix("x", "x", s.D0Evar("x")), s.D0Eint(8))
        self.assertEqual(evaluate(coincident).value, 8)
        initializer = s.D0Elet("x", s.D0Eint(2), s.D0Elet("x", s.D0Evar("x"), s.D0Evar("x")))
        self.assertEqual(evaluate(initializer).value, 2)

    def test_source_short_circuit_and_pairs(self):
        loop = s.D0Eapp(s.D0Efix("f", "x", s.D0Eapp(s.D0Evar("f"), s.D0Evar("x"))), s.D0Eint(0))
        self.assertEqual(evaluate(s.D0Eif0(s.D0Ebtf(True), s.D0Eint(1), loop)).value, 1)
        self.assertIs(evaluate(s.D0Eop2("and", s.D0Ebtf(False), loop)).value, False)
        self.assertIs(evaluate(s.D0Eop2("or", s.D0Ebtf(True), loop)).value, True)
        self.assertIs(evaluate(s.D0Eop1("not", s.D0Ebtf(True))).value, False)
        pair = s.D0Epair(s.D0Eint(2), s.D0Ebtf(True))
        self.assertEqual(evaluate(pair).value, (2, True))
        self.assertEqual(evaluate(s.D0Epfst(pair)).value, 2)
        self.assertIs(evaluate(s.D0Epsnd(pair)).value, True)

    def test_source_arithmetic_and_recursion(self):
        expected = {"+": 7, "-": 0, "*": 10, "<": True, "<=": True,
                    ">": False, ">=": False, "==": False, "!=": True}
        for op, answer in expected.items():
            with self.subTest(op=op):
                self.assertEqual(evaluate(s.D0Eop2(op, s.D0Eint(2), s.D0Eint(5))).value, answer)
        n = s.D0Evar("n")
        factorial = s.D0Efix("fact", "n", s.D0Eif0(
            s.D0Eop2("==", n, s.D0Eint(0)), s.D0Eint(1),
            s.D0Eop2("*", n, s.D0Eapp(s.D0Evar("fact"), s.D0Eop2("-", n, s.D0Eint(1))))))
        result = evaluate(s.D0Eapp(factorial, s.D0Eint(4)), 0)
        self.assertEqual(result.value, 24)
        self.assertEqual(result.steps, 0)


if __name__ == "__main__":
    unittest.main()
