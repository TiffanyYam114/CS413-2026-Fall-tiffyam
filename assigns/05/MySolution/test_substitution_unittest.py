"""Run: python -B -m unittest MySolution.test_substitution_unittest"""

from copy import deepcopy
import unittest
from unittest.mock import patch

import lambda1_vp as ast
from lambda1_vp import D0Evar, d0exp_fvset
from MySolution.assignment_examples import SUBSTITUTION_EXAMPLES
from MySolution.pretty_print_visitor import d0exp_pretty
from MySolution.substitution_cases import CASES
from MySolution.substitution_visitor import SubstitutionVisitor, d0exp_substitute


class SubstitutionTests(unittest.TestCase):
    def test_assignment_examples(self):
        for name, (expression, variable, replacement, expected_ast, expected) in SUBSTITUTION_EXAMPLES.items():
            with self.subTest(example=name):
                result = d0exp_substitute(expression, variable, replacement)
                self.assertEqual(result, expected_ast)
                self.assertEqual(d0exp_pretty(result), expected)

    def test_lambda_capture_counterexample_is_rejected(self):
        expression, variable, replacement, expected, _ = SUBSTITUTION_EXAMPLES["task2_lambda_capture"]
        result = d0exp_substitute(expression, variable, replacement)
        self.assertEqual(result, expected)
        self.assertNotEqual(d0exp_pretty(result), "(lam y. (y + y))")
        self.assertEqual(d0exp_fvset(result), frozenset({"y"}))

    def test_no_evaluation(self):
        with patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("evaluated")), \
             patch.object(ast.EvaluateVisitor, "__init__", side_effect=AssertionError("evaluated")):
            for expression, variable, replacement, expected in CASES:
                with self.subTest(expected=expected):
                    self.assertEqual(d0exp_pretty(d0exp_substitute(expression, variable, replacement)), expected)

    def test_examples_and_free_variable_property(self):
        for expression, variable, replacement, expected in CASES:
            with self.subTest(expected=expected, variable=variable):
                original = deepcopy(expression)
                original_replacement = deepcopy(replacement)
                result = d0exp_substitute(expression, variable, replacement)
                self.assertEqual(d0exp_pretty(result), expected)
                self.assertEqual(d0exp_substitute(expression, variable, replacement), result)
                visitor = SubstitutionVisitor(variable, replacement)
                self.assertEqual(expression.accept(visitor), result)
                self.assertEqual(expression.accept(visitor), result)
                self.assertEqual(expression, original)
                self.assertEqual(replacement, original_replacement)
                free = d0exp_fvset(expression)
                expected_free = ((free - {variable}) | d0exp_fvset(replacement)
                                 if variable in free else free)
                self.assertEqual(d0exp_fvset(result), expected_free)
                if variable not in free:
                    self.assertEqual(result, expression)

    def test_inserted_replacement_is_reused_without_substitution(self):
        replacement = CASES[5][2]
        self.assertIs(d0exp_substitute(D0Evar("x"), "x", replacement), replacement)


if __name__ == "__main__":
    unittest.main()
