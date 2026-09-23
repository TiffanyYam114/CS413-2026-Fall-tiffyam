"""Tests for LAMBDA0 pairs and projections.

Run from the MySolution directory with:
    python -m unittest TEST.test02_lambda0
"""

import sys
import unittest
from pathlib import Path


# This test file must exercise MySolution/lambda0.py, not the starter copy.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lambda0 import (
    T0Mint, T0Mstr, T0Mvar, T0Mlam, T0Mfix, T0Mapp, T0Mop1, T0Mop2,
    T0Mpair, T0Mpfst, T0Mpsnd,
    t0erm_size, t0erm_fvset, t0erm_subst0, t0erm_cbv_evaluate0,
)


class TestPairAstOperations(unittest.TestCase):
    def test_size_of_pair_projection_and_nested_term(self):
        self.assertEqual(t0erm_size(T0Mpair(T0Mint(1), T0Mint(2))), 3)
        term = T0Mpfst(T0Mpair(T0Mint(1), T0Mpsnd(T0Mpair(T0Mint(2), T0Mint(3)))))
        self.assertEqual(t0erm_size(term), 7)

    def test_free_variables_of_pair_projection_and_nested_term(self):
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_fvset(term), frozenset({"x", "y"}))
        nested = T0Mpair(T0Mlam("x", T0Mvar("x")), T0Mpsnd(T0Mpair(T0Mvar("y"), T0Mvar("z"))))
        self.assertEqual(t0erm_fvset(nested), frozenset({"y", "z"}))

    def test_substitution_in_pair_components_and_projection_operand(self):
        term = T0Mpfst(T0Mpair(T0Mvar("x"), T0Mpsnd(T0Mpair(T0Mvar("y"), T0Mvar("x")))))
        expected = T0Mpfst(T0Mpair(T0Mint(9), T0Mpsnd(T0Mpair(T0Mvar("y"), T0Mint(9)))))
        self.assertEqual(t0erm_subst0(term, "x", T0Mint(9)), expected)

    def test_substitution_respects_lambda_and_fix_binders(self):
        replacement = T0Mint(42)
        lam = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("y")))
        self.assertEqual(t0erm_subst0(lam, "x", replacement), lam)
        fix = T0Mfix("f", "x", T0Mpfst(T0Mpair(T0Mvar("x"), T0Mvar("z"))))
        self.assertEqual(t0erm_subst0(fix, "x", replacement), fix)
        changed = t0erm_subst0(fix, "z", replacement)
        self.assertEqual(changed, T0Mfix("f", "x", T0Mpfst(T0Mpair(T0Mvar("x"), replacement))))


class TestPairEvaluation(unittest.TestCase):
    def test_pair_construction_and_both_projections(self):
        pair = T0Mpair(T0Mop2("+", T0Mint(2), T0Mint(3)), T0Mop1("-", T0Mint(4)))
        self.assertEqual(t0erm_cbv_evaluate0(pair), T0Mpair(T0Mint(5), T0Mint(-4)))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpfst(pair)), T0Mint(5))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(pair)), T0Mint(-4))
        self.assertEqual(
            t0erm_cbv_evaluate0(
                T0Mpsnd(T0Mpair(T0Mint(1), T0Mop2("+", T0Mint(2), T0Mint(3))))
            ),
            T0Mint(5),
        )

    def test_nested_pairs_and_mixed_values(self):
        identity = T0Mlam("x", T0Mvar("x"))
        pair = T0Mpair(T0Mpair(T0Mint(1), identity), T0Mstr("right"))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpfst(T0Mpfst(pair))), T0Mint(1))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(T0Mpfst(pair))), identity)
        self.assertEqual(t0erm_cbv_evaluate0(T0Mpsnd(pair)), T0Mstr("right"))

    def test_functions_accept_and_return_pairs(self):
        # (lambda p. snd(p))(3, 4) = 4; application substitutes p into a projection.
        second = T0Mlam("p", T0Mpsnd(T0Mvar("p")))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(second, T0Mpair(T0Mint(3), T0Mint(4)))), T0Mint(4))
        # A function can construct a pair from its argument.
        duplicate = T0Mlam("x", T0Mpair(T0Mvar("x"), T0Mvar("x")))
        self.assertEqual(t0erm_cbv_evaluate0(T0Mapp(duplicate, T0Mint(8))), T0Mpair(T0Mint(8), T0Mint(8)))

    def test_projection_of_non_pair_raises_type_error(self):
        for projection in (T0Mpfst, T0Mpsnd):
            with self.subTest(projection=projection.__name__):
                with self.assertRaises(TypeError):
                    t0erm_cbv_evaluate0(projection(T0Mint(1)))

    def test_pair_evaluates_left_to_right_and_projection_evaluates_both(self):
        # The left error occurs before the right error, demonstrating left-to-right order.
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(T0Mpair(
                T0Mop2("/", T0Mint(1), T0Mint(0)),
                T0Mop1("-", T0Mstr("not an integer")),
            ))
        # Although fst selects the first component, constructing its pair evaluates the second.
        with self.assertRaises(ZeroDivisionError):
            t0erm_cbv_evaluate0(T0Mpfst(T0Mpair(
                T0Mint(1), T0Mop2("/", T0Mint(1), T0Mint(0)),
            )))


if __name__ == "__main__":
    unittest.main(verbosity=2)
