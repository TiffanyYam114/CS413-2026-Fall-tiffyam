"""Task 3 acceptance tests using the shared evaluator and pure observations."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from . import church_encodings as c
from . import compiler, lambda1_vp as s, target_ast
from .compiler import CompilationError, CompileVisitor, compile_expr
from .target_ast import App, Lam, Var, evaluate, free_vars
from . import test_church_encodings as observation_helpers
from . import examples as demo_examples
from .decoders import observe


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


class CompilerTests(unittest.TestCase):
    def setUp(self):
        self.observers = observation_helpers.ChurchEncodingTests()

    def assertPureTerm(self, term):
        pending = [term]
        while pending:
            node = pending.pop()
            self.assertIn(type(node), (Var, Lam, App))
            if isinstance(node, Lam):
                pending.append(node.body)
            elif isinstance(node, App):
                pending.extend((node.fn, node.arg))

    def check(self, expression, expected):
        before = deepcopy(expression)
        source = evaluate(expression)
        self.assertTrue(source.completed)
        self.assertEqual(source.value, expected)
        target = compile_expr(expression)
        self.assertEqual(expression, before)
        self.assertEqual(free_vars(target), s.d0exp_fvset(expression))
        observed = (self.observers.boolean(target) if type(expected) is bool
                    else self.observers.natural(target))
        self.assertEqual(observed, expected)

    def test_required_terminating_demonstrations(self):
        pair = s.D0Epair(s.D0Eint(2), s.D0Ebtf(True))
        examples = [
            (s.D0Eop2("+", s.D0Eint(2), s.D0Eop2("*", s.D0Eint(3), s.D0Eint(4))), 14),
            (s.D0Eop2("-", s.D0Eint(2), s.D0Eint(5)), 0),
            (s.D0Eif0(s.D0Eop2("<=", s.D0Eint(2), s.D0Eint(3)), s.D0Eint(7), s.D0Eint(9)), 7),
            (s.D0Elet("x", s.D0Eint(3), s.D0Eapp(s.D0Elam("y", s.D0Eop2("+", s.D0Evar("x"), s.D0Evar("y"))), s.D0Eint(4))), 7),
            (s.D0Epfst(pair), 2), (s.D0Epsnd(pair), True),
            (s.D0Eapp(s.D0Elam("f", s.D0Eapp(s.D0Evar("f"), s.D0Eint(3))), s.D0Elam("x", s.D0Eop2("+", s.D0Evar("x"), s.D0Eint(1)))), 4),
            (s.D0Eop2("and", s.D0Ebtf(True), s.D0Ebtf(False)), False),
            (s.D0Eop2("or", s.D0Ebtf(False), s.D0Ebtf(True)), True),
            (s.D0Eif0(s.D0Ebtf(True), s.D0Eint(1), loop()), 1),
            (s.D0Eapp(factorial(), s.D0Eint(4)), 24),
            (s.D0Eapp(fibonacci(), s.D0Eint(5)), 5),
        ]
        for expression, answer in examples:
            with self.subTest(expression=expression):
                self.check(expression, answer)

    def test_every_operator_and_comparison_outcome(self):
        expected = {"+": lambda a,b: a+b, "-": lambda a,b: max(a-b, 0),
                    "*": lambda a,b: a*b, "<": lambda a,b: a<b,
                    "<=": lambda a,b: a<=b, ">": lambda a,b: a>b,
                    ">=": lambda a,b: a>=b, "==": lambda a,b: a==b, "!=": lambda a,b: a!=b}
        for op, operation in expected.items():
            for a, b in ((0, 0), (0, 2), (2, 0), (2, 2)):
                with self.subTest(op=op, a=a, b=b):
                    self.check(s.D0Eop2(op, s.D0Eint(a), s.D0Eint(b)), operation(a, b))
        for a in (True, False):
            self.check(s.D0Eop1("not", s.D0Ebtf(a)), not a)
            for b in (True, False):
                self.check(s.D0Eop2("and", s.D0Ebtf(a), s.D0Ebtf(b)), a and b)
                self.check(s.D0Eop2("or", s.D0Ebtf(a), s.D0Ebtf(b)), a or b)

    def test_shadowing_initializer_scope_and_fix_binders(self):
        examples = [
            (s.D0Elet("x", s.D0Eint(3), s.D0Elet("x", s.D0Eop2("+", s.D0Evar("x"), s.D0Eint(1)), s.D0Evar("x"))), 4),
            (s.D0Eapp(s.D0Elam("x", s.D0Eapp(s.D0Elam("x", s.D0Evar("x")), s.D0Eint(2))), s.D0Eint(1)), 2),
            (s.D0Eapp(s.D0Efix("x", "x", s.D0Evar("x")), s.D0Eint(8)), 8),
            (s.D0Elet("x", s.D0Eint(9), s.D0Elet("f", s.D0Elam("y", s.D0Evar("x")), s.D0Elet("x", s.D0Eint(2), s.D0Eapp(s.D0Evar("f"), s.D0Eint(0))))), 9),
        ]
        for expr, answer in examples:
            self.check(expr, answer)
        for name in ("s", "z", "t", "f", "x", "u", "u_1", "u_2"):
            self.check(s.D0Elet(name, s.D0Eint(3), s.D0Eif0(s.D0Ebtf(True), s.D0Evar(name), s.D0Eint(0))), 3)

    def test_each_fix_binder_shadows_outer_bindings_and_respects_inner_bindings(self):
        x = s.D0Evar("x")
        countdown = s.D0Efix("f", "x", s.D0Eif0(
            s.D0Eop2("==", x, s.D0Eint(0)), s.D0Eint(7),
            s.D0Eapp(s.D0Evar("f"), s.D0Eop2("-", x, s.D0Eint(1)))))
        cases = [
            # The recursive f must shadow the outer numeric f.
            (s.D0Elet("f", s.D0Eint(99), s.D0Eapp(countdown, s.D0Eint(2))), 7),
            # The parameter must shadow the outer x.
            (s.D0Elet("x", s.D0Eint(99),
                      s.D0Eapp(s.D0Efix("f", "x", x), s.D0Eint(3))), 3),
            # A lambda's f shadows the function name without changing x.
            (s.D0Eapp(s.D0Efix("f", "x", s.D0Eapp(
                s.D0Elam("f", s.D0Eop2("+", x, s.D0Evar("f"))), s.D0Eint(1))), s.D0Eint(3)), 4),
            # A lambda's x shadows the parameter; f still denotes recursion.
            (s.D0Eapp(s.D0Efix("f", "x", s.D0Eif0(
                s.D0Eop2("==", x, s.D0Eint(0)), s.D0Eint(7),
                s.D0Eapp(s.D0Elam("x", s.D0Eapp(s.D0Evar("f"), x)), s.D0Eint(0)))), s.D0Eint(2)), 7),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                self.check(expression, expected)

    def test_free_variables_and_purity_for_every_source_form(self):
        x, y = s.D0Evar("x"), s.D0Evar("y")
        cases = [
            (s.D0Eint(0), set()), (s.D0Ebtf(True), set()),
            (s.D0Ebtf(False), set()), (x, {"x"}),
            (s.D0Elam("x", s.D0Epair(x, y)), {"y"}),
            (s.D0Eapp(x, y), {"x", "y"}),
            (s.D0Eop1("not", x), {"x"}),
            (s.D0Eif0(s.D0Evar("c"), s.D0Evar("u_1"), s.D0Evar("u_2")), {"c", "u_1", "u_2"}),
            (s.D0Elet("x", x, s.D0Epair(x, y)), {"x", "y"}),
            (s.D0Epair(x, y), {"x", "y"}),
            (s.D0Epfst(x), {"x"}), (s.D0Epsnd(y), {"y"}),
            (s.D0Efix("f", "x", s.D0Eapp(s.D0Evar("f"), s.D0Epair(x, y))), {"y"}),
            (s.D0Efix("x", "x", s.D0Epair(x, y)), {"y"}),
        ]
        cases.extend((s.D0Eop2(op, x, y), {"x", "y"})
                     for op in ("+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "and", "or"))
        for expression, expected_free in cases:
            with self.subTest(expression=expression):
                before = deepcopy(expression)
                target = compile_expr(expression)
                self.assertPureTerm(target)
                # Explicit sets avoid relying on source and target analyses
                # having the same binding mistake.
                self.assertEqual(s.d0exp_fvset(expression), expected_free)
                self.assertEqual(free_vars(target), expected_free)
                self.assertEqual(expression, before)
                self.assertEqual(compile_expr(expression), target)

    def test_open_terms_free_names_purity_and_determinism(self):
        examples = [s.D0Evar(name) for name in ("s", "z", "t", "f", "x", "u_1")]
        examples += [
            s.D0Elet("x", s.D0Evar("x"), s.D0Evar("x")),
            s.D0Efix("f", "x", s.D0Epair(s.D0Evar("f"), s.D0Epair(s.D0Evar("x"), s.D0Evar("outside")))),
            s.D0Efix("x", "x", s.D0Epair(s.D0Evar("x"), s.D0Evar("f"))),
            s.D0Eif0(s.D0Evar("t"), s.D0Evar("u_1"), s.D0Evar("u_2")),
            s.D0Eop2("and", s.D0Evar("p"), s.D0Evar("u_1")),
            s.D0Elam("s", s.D0Eop2("+", s.D0Evar("s"), s.D0Evar("z"))),
        ]

        def pure(term):
            self.assertIn(type(term), (Var, Lam, App))
            if isinstance(term, Lam): pure(term.body)
            if isinstance(term, App):
                pure(term.fn)
                pure(term.arg)

        for expression in examples:
            before = deepcopy(expression)
            result = compile_expr(expression)
            pure(result)
            self.assertEqual(free_vars(result), s.d0exp_fvset(expression))
            self.assertEqual(result, compile_expr(expression))
            self.assertEqual(expression, before)

    def test_rejection_in_dead_code_and_unapplied_bodies(self):
        bad = [s.D0Eint(-2), s.D0Eop1("+1", s.D0Eint(0)),
               s.D0Eop2("/", s.D0Eint(4), s.D0Eint(2)),
               s.D0Eop2("AND", s.D0Ebtf(True), s.D0Ebtf(False))]
        for invalid in bad:
            for wrapped in (invalid, s.D0Elam("x", invalid), s.D0Efix("f", "x", invalid),
                            s.D0Eif0(s.D0Ebtf(True), s.D0Eint(1), invalid),
                            s.D0Eop2("and", s.D0Ebtf(False), invalid),
                            s.D0Eop2("or", s.D0Ebtf(True), invalid)):
                with self.subTest(wrapped=wrapped), self.assertRaises(CompilationError) as error:
                    compile_expr(wrapped)
                token = str(invalid.arg1) if isinstance(invalid, s.D0Eint) else invalid.name
                self.assertIn(token, str(error.exception))

    def test_divergence_and_strict_constructs(self):
        expressions = [loop(), s.D0Eapp(s.D0Elam("x", s.D0Eint(0)), loop()),
                       s.D0Elet("x", loop(), s.D0Eint(0)),
                       s.D0Epfst(s.D0Epair(s.D0Eint(1), loop())),
                       s.D0Epsnd(s.D0Epair(loop(), s.D0Eint(1))),
                       s.D0Eop2("and", s.D0Ebtf(True), loop()),
                       s.D0Eop2("or", s.D0Ebtf(False), loop()),
                       s.D0Eif0(s.D0Ebtf(True), loop(), s.D0Eint(0)),
                       s.D0Eif0(s.D0Ebtf(False), s.D0Eint(0), loop())]
        for expr in expressions:
            result = evaluate(compile_expr(expr), 200)
            self.assertEqual(result.status, "exhausted")
            self.assertEqual(result.steps, 200)
        self.check(s.D0Eop2("and", s.D0Ebtf(False), loop()), False)
        self.check(s.D0Eop2("or", s.D0Ebtf(True), loop()), True)
        self.check(s.D0Eif0(s.D0Ebtf(False), loop(), s.D0Eint(2)), 2)

    def test_nested_pairs(self):
        expr = s.D0Epair(s.D0Epair(s.D0Eint(2), s.D0Ebtf(True)), s.D0Eint(3))
        self.assertEqual(evaluate(expr).value, ((2, True), 3))
        value = evaluate(compile_expr(expr)).value
        first = evaluate(c.apply(c.FST(), value)).value
        self.assertEqual(self.observers.natural(c.apply(c.FST(), first)), 2)
        self.assertTrue(self.observers.boolean(c.apply(c.SND(), first)))
        self.assertEqual(self.observers.natural(c.apply(c.SND(), value)), 3)

    def test_left_to_right_order_of_strict_source_constructs(self):
        def tagged(name, body):
            return s.D0Eapp(s.D0Elam(name, body), s.D0Eint(0))

        cases = [
            (s.D0Eapp(tagged("trace_function", s.D0Elam("x", s.D0Evar("x"))),
                       tagged("trace_argument", s.D0Eint(4))), "nat", 4,
             ["trace_function", "trace_argument"]),
            (s.D0Elet("x", tagged("trace_init", s.D0Eint(2)),
                      tagged("trace_body", s.D0Evar("x"))), "nat", 2,
             ["trace_init", "trace_body"]),
            (s.D0Epair(tagged("trace_left", s.D0Eint(2)),
                       tagged("trace_right", s.D0Ebtf(True))), ("nat", "bool"), (2, True),
             ["trace_left", "trace_right"]),
        ]
        cases.extend((s.D0Eop2(op, tagged("trace_left", s.D0Eint(2)),
                              tagged("trace_right", s.D0Eint(3))), kind, expected,
                      ["trace_left", "trace_right"])
                     for op, kind, expected in (("+", "nat", 5), ("<", "bool", True)))
        original_substitute = target_ast.substitute
        for expression, kind, expected, order in cases:
            with self.subTest(expression=expression):
                events = []

                def record(body, name, replacement):
                    if name.startswith("trace_"):
                        events.append(name)
                    return original_substitute(body, name, replacement)

                with patch.object(target_ast, "substitute", side_effect=record):
                    result = observe(compile_expr(expression), kind)
                self.assertTrue(result.execution.completed)
                self.assertTrue(result.observation.completed)
                self.assertEqual(result.observation.value, expected)
                self.assertEqual(events, order)

    def test_visitor_dispatch_and_no_evaluation_during_compilation(self):
        self.assertIsInstance(CompileVisitor(), s.D0ExpVisitor)
        with patch.object(target_ast, "evaluate", side_effect=AssertionError("target evaluation")), \
             patch.object(s, "d0exp_evaluate", side_effect=AssertionError("source evaluation")), \
             patch.object(s.EvaluateVisitor, "visit_app", side_effect=AssertionError("source visitor")):
            # Covers arithmetic and every mandatory demo, including LOOP,
            # with evaluator entry points disabled throughout compilation.
            for example in demo_examples.examples():
                with self.subTest(example=example.name):
                    before = deepcopy(example.expression)
                    target = compile_expr(example.expression)
                    self.assertPureTerm(target)
                    self.assertEqual(free_vars(target), set())
                    self.assertEqual(example.expression, before)
        self.assertNotIn("evaluate", compiler.__dict__)


if __name__ == "__main__":
    unittest.main()
