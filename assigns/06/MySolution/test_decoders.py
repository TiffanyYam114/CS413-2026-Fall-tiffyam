"""Run from assigns/06 with python -m unittest MySolution.test_decoders."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from . import church_encodings as c, demo
from .compiler import compile_expr
from .decoders import observe, observe_boolean, observe_natural, observe_pair, observe_value
from .examples import examples, factorial
from .target_ast import App, Lam, Var, evaluate, pretty


class DecoderTests(unittest.TestCase):
    def test_literals_expected_kind_and_alpha_renaming(self):
        for n in range(7):
            result = observe_natural(c.NUM(n))
            self.assertTrue(result.completed)
            self.assertEqual(result.value, n)
        self.assertEqual(observe_natural(c.FALSE()).value, 0)
        self.assertIs(observe_boolean(c.NUM(0)).value, False)
        alpha_one = Lam("step_1", Lam("zero_1", App(Var("step_1"), Var("zero_1"))))
        self.assertEqual(observe_natural(alpha_one).value, 1)
        for encoded, expected in ((Lam("a", Lam("b", Var("a"))), True),
                                  (Lam("a", Lam("b", Var("b"))), False)):
            self.assertIs(observe_boolean(encoded).value, expected)

    def test_computed_numeral_and_boolean_with_body_redexes(self):
        term = c.apply(c.ADD(), c.NUM(2), c.apply(c.MUL(), c.NUM(3), c.NUM(4)))
        value = evaluate(term).value
        before = pretty(value)
        self.assertEqual(observe_natural(value).value, 14)
        self.assertEqual(pretty(value), before)
        hidden = Lam("a", Lam("b", App(c.I(), Var("a"))))
        self.assertIs(observe_boolean(hidden).value, True)

    def test_execution_and_observation_have_independent_counts(self):
        term = c.apply(c.ADD(), c.NUM(2), c.NUM(3))
        result = observe(term, "num", 500, 500)
        self.assertTrue(result.execution.completed)
        self.assertTrue(result.observation.completed)
        self.assertEqual(result.observation.value, 5)
        self.assertEqual(result.execution.steps, evaluate(term, 500).steps)
        self.assertGreater(result.observation.steps, 0)
        failed_execution = observe(term, "num", 0, 500)
        self.assertFalse(failed_execution.execution.completed)
        self.assertIsNone(failed_execution.observation)
        failed_observation = observe(term, "num", 500, 0)
        self.assertTrue(failed_observation.execution.completed)
        self.assertEqual(failed_observation.observation.status, "exhausted")
        self.assertIsNone(failed_observation.observation.value)

    def test_observation_budget_exact_boundary(self):
        needed = observe_natural(c.NUM(3)).steps
        for budget in (0, needed - 1, needed, needed + 1):
            with self.subTest(budget=budget):
                result = observe_natural(c.NUM(3), budget)
                self.assertEqual(result.completed, budget >= needed)
                self.assertEqual(result.steps, min(budget, needed))
        needed = observe_boolean(c.TRUE()).steps
        self.assertTrue(observe_boolean(c.TRUE(), needed).completed)
        self.assertEqual(observe_boolean(c.TRUE(), needed - 1).status, "exhausted")

    def test_observation_of_divergent_body_is_bounded(self):
        dup = Lam("x", App(Var("x"), Var("x")))
        value = Lam("s", Lam("z", App(dup, dup)))
        self.assertTrue(evaluate(value, 0).completed)
        for kind in ("num", "bool"):
            result = observe_value(value, kind, 30)
            self.assertEqual(result.status, "exhausted")
            self.assertEqual(result.steps, 30)
            self.assertIsNone(result.value)

    def test_malformed_outputs_and_invalid_inputs(self):
        bad_nat = Lam("s", Lam("z", c.I()))
        bad_bool = Lam("a", Lam("b", Lam("c", Lam("d", Var("d")))))
        for value, kind in ((bad_nat, "num"), (bad_bool, "bool"), (Var("x"), "num"),
                            (Lam("x", Var("free")), "bool")):
            result = observe_value(value, kind)
            self.assertEqual(result.status, "malformed")
            self.assertIsNone(result.value)
            self.assertTrue(result.message)
        for budget in (-1, True, 0.5):
            with self.assertRaises(ValueError):
                observe_natural(c.NUM(0), budget)
        for kind in ("number", None, ("num",), ("num", "invalid")):
            with self.assertRaises(ValueError):
                observe_value(c.NUM(0), kind)

    def test_pair_evaluation_nested_observation_and_aggregate_budget(self):
        term = c.apply(c.PAIR(), c.apply(c.PAIR(), c.NUM(2), c.TRUE()), c.NUM(3))
        kind = (("num", "bool"), "num")
        result = observe_pair(term, kind)
        self.assertEqual(result.observation.value, ((2, True), 3))
        self.assertGreater(result.execution.steps, 0)
        steps = result.observation.steps
        exact = observe_pair(term, kind, observation_budget=steps)
        self.assertTrue(exact.observation.completed)
        short = observe_pair(term, kind, observation_budget=steps - 1)
        self.assertEqual(short.observation.status, "exhausted")
        self.assertEqual(short.observation.steps, steps - 1)
        self.assertIsNone(short.observation.value)
        self.assertEqual(observe_pair(term, kind, execution_budget=0).observation, None)
        with self.assertRaises(ValueError):
            observe_pair(term, "num")

    def test_all_examples_with_production_observers(self):
        for example in examples():
            with self.subTest(example=example.name):
                term = compile_expr(example.expression)
                if example.kind is None:
                    self.assertEqual(evaluate(term, 200).status, "exhausted")
                else:
                    self.assertEqual(evaluate(example.expression).value, example.expected)
                    result = observe(term, example.kind)
                    self.assertTrue(result.execution.completed)
                    self.assertTrue(result.observation.completed)
                    self.assertEqual(result.observation.value, example.expected)

    def test_recursive_function_stays_a_lambda_until_application(self):
        function = compile_expr(factorial())
        value = evaluate(function, 100).value
        self.assertIsInstance(value, Lam)
        self.assertEqual(evaluate(value, 0).steps, 0)
        self.assertEqual(observe(c.apply(value, c.NUM(4)), "num").observation.value, 24)


class DemoTests(unittest.TestCase):
    def test_complete_demo_and_saved_pure_terms(self):
        collection = examples()
        stream = StringIO()
        with TemporaryDirectory() as folder, redirect_stdout(stream), \
             patch.object(demo, "examples", return_value=collection), \
             patch.object(demo, "evaluate", wraps=evaluate) as tracked:
            self.assertEqual(demo.main(["--output-dir", folder]), 0)
            paths = list(Path(folder).glob("*.lambda.txt"))
            self.assertEqual(len(paths), 17)
            for path in paths:
                self.assertTrue(path.read_text(encoding="utf-8").startswith("("))
            self.assertEqual((Path(folder) / "report.txt").read_text(encoding="utf-8"), stream.getvalue())
            for example in collection:
                if example.kind is None:
                    self.assertFalse(any(call.args[0] is example.expression for call in tracked.call_args_list))
        text = stream.getvalue()
        self.assertIn("17/17 examples passed", text)
        self.assertIn("does not prove nontermination", text)
        for number in range(1, 15):
            self.assertIn(f"DEMO-{number:02}", text)
        self.assertIn("Observation: completed; beta-value steps:", text)
        self.assertIn("budget: 50000", text)

    def test_demo_fails_when_observation_budget_is_insufficient(self):
        stream = StringIO()
        with TemporaryDirectory() as folder, redirect_stdout(stream):
            self.assertEqual(demo.main(["--output-dir", folder, "--observation-budget", "0"]), 1)
        self.assertIn("Observation: exhausted", stream.getvalue())
        self.assertIn("Check: FAIL", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
