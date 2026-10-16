"""Run from assigns/05: python -B -m unittest MySolution.test_pretty_unittest"""

from copy import deepcopy
import unittest
from unittest.mock import patch

import lambda1_vp as ast
from MySolution.pretty_print_visitor import PrettyPrintVisitor, d0exp_pretty


from MySolution.pretty_cases import CASES
from MySolution.assignment_examples import PRETTY_EXAMPLES


class PrettyPrintTests(unittest.TestCase):
    def test_assignment_examples(self):
        for name, (expression, expected) in PRETTY_EXAMPLES.items():
            with self.subTest(example=name):
                self.assertEqual(d0exp_pretty(expression), expected)

    def test_no_evaluation(self):
        with patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("evaluated")), \
             patch.object(ast.EvaluateVisitor, "__init__", side_effect=AssertionError("evaluated")):
            for expression, expected in CASES:
                with self.subTest(expected=expected):
                    self.assertEqual(d0exp_pretty(expression), expected)

    def test_exact_output_and_preservation(self):
        visitor = PrettyPrintVisitor()
        for expression, expected in CASES:
            with self.subTest(expected=expected):
                original = deepcopy(expression)
                self.assertEqual(d0exp_pretty(expression), expected)
                self.assertEqual(expression.accept(visitor), expected)
                self.assertEqual(d0exp_pretty(expression), expected)
                self.assertEqual(expression, original)


if __name__ == "__main__":
    unittest.main()
