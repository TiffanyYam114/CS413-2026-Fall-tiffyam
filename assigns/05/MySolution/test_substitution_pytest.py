"""Run: python -B -m pytest -p no:cacheprovider MySolution/test_substitution_pytest.py"""

from copy import deepcopy
from unittest.mock import patch

import pytest
import lambda1_vp as ast

from lambda1_vp import D0Evar, d0exp_fvset
from MySolution.assignment_examples import SUBSTITUTION_EXAMPLES
from MySolution.pretty_print_visitor import d0exp_pretty
from MySolution.substitution_cases import CASES
from MySolution.substitution_visitor import SubstitutionVisitor, d0exp_substitute


@pytest.mark.parametrize("expression,variable,replacement,expected_ast,expected",
                         SUBSTITUTION_EXAMPLES.values(), ids=SUBSTITUTION_EXAMPLES)
def test_assignment_examples(expression, variable, replacement, expected_ast, expected):
    result = d0exp_substitute(expression, variable, replacement)
    assert result == expected_ast
    assert d0exp_pretty(result) == expected


def test_lambda_capture_counterexample_is_rejected():
    expression, variable, replacement, expected, _ = SUBSTITUTION_EXAMPLES["task2_lambda_capture"]
    result = d0exp_substitute(expression, variable, replacement)
    assert result == expected
    assert d0exp_pretty(result) != "(lam y. (y + y))"
    assert d0exp_fvset(result) == frozenset({"y"})


def test_no_evaluation():
    with patch.object(ast, "d0exp_evaluate", side_effect=AssertionError("evaluated")), \
         patch.object(ast.EvaluateVisitor, "__init__", side_effect=AssertionError("evaluated")):
        for expression, variable, replacement, expected in CASES:
            assert d0exp_pretty(d0exp_substitute(expression, variable, replacement)) == expected


@pytest.mark.parametrize("expression,variable,replacement,expected", CASES)
def test_examples_and_free_variable_property(expression, variable, replacement, expected):
    original = deepcopy(expression)
    original_replacement = deepcopy(replacement)
    result = d0exp_substitute(expression, variable, replacement)
    assert d0exp_pretty(result) == expected
    assert d0exp_substitute(expression, variable, replacement) == result
    visitor = SubstitutionVisitor(variable, replacement)
    assert expression.accept(visitor) == result
    assert expression.accept(visitor) == result
    assert expression == original
    assert replacement == original_replacement
    free = d0exp_fvset(expression)
    expected_free = ((free - {variable}) | d0exp_fvset(replacement)
                     if variable in free else free)
    assert d0exp_fvset(result) == expected_free
    if variable not in free:
        assert result == expression


def test_inserted_replacement_is_reused_without_substitution():
    replacement = CASES[5][2]
    assert d0exp_substitute(D0Evar("x"), "x", replacement) is replacement
