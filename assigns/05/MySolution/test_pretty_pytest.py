"""Run from assigns/05: python -B -m pytest -p no:cacheprovider MySolution/test_pretty_pytest.py"""

from copy import deepcopy
from unittest.mock import patch

import pytest
import lambda1_vp as ast

from MySolution.pretty_print_visitor import PrettyPrintVisitor, d0exp_pretty
from MySolution.pretty_cases import CASES
from MySolution.assignment_examples import PRETTY_EXAMPLES


@pytest.mark.parametrize("expression,expected", PRETTY_EXAMPLES.values(), ids=PRETTY_EXAMPLES)
def test_assignment_examples(expression, expected):
    assert d0exp_pretty(expression) == expected


def test_no_evaluation():
    with patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("evaluated")), \
         patch.object(ast.EvaluateVisitor, "__init__", side_effect=AssertionError("evaluated")):
        for expression, expected in CASES:
            assert d0exp_pretty(expression) == expected


@pytest.mark.parametrize("expression,expected", CASES)
def test_exact_output_and_preservation(expression, expected):
    original = deepcopy(expression)
    assert d0exp_pretty(expression) == expected
    assert expression.accept(PrettyPrintVisitor()) == expected
    assert d0exp_pretty(expression) == expected
    assert expression == original
