"""Encoding tests; observation uses only pure contexts in the shared reducer."""

import unittest
from unittest.mock import patch

from . import church_encodings as c
from .target_ast import App, Lam, Var, evaluate, free_vars, pretty


BUILDERS = (c.I, c.TRUE, c.FALSE, c.PAIR, c.FST, c.SND, c.Z, c.SUCC,
            c.PRED, c.ISZERO, c.ADD, c.SUB, c.MUL, c.NOT, c.IF, c.AND,
            c.OR, c.LE, c.GE, c.LT, c.GT, c.EQ, c.NE)


def alpha_key(term, bound=()):
    """Structural comparison up to bound-name changes, not evaluation."""
    match term:
        case Var(name):
            return ("bound", bound.index(name)) if name in bound else ("free", name)
        case Lam(name, body):
            return ("lam", alpha_key(body, (name,) + bound))
        case App(fn, arg):
            return ("app", alpha_key(fn, bound), alpha_key(arg, bound))
    raise AssertionError("not a pure target node")


class ChurchEncodingTests(unittest.TestCase):
    execution_budget = 50000
    observation_budget = 50000

    def run_target(self, term, budget=None):
        result = evaluate(term, self.execution_budget if budget is None else budget)
        self.assertTrue(result.completed, f"budget exhausted after {result.steps} steps")
        self.assertIsInstance(result.value, Lam)
        return result.value

    def natural(self, term):
        value = self.run_target(term)
        step = Lam("tail", Lam("c", Lam("z", App(Var("c"), Var("tail")))))
        base = Lam("c", Lam("z", Var("z")))
        spine = self.run_target(c.apply(value, step, base), self.observation_budget)
        count = 0
        while True:
            self.assertIsInstance(spine, Lam)
            self.assertIsInstance(spine.body, Lam)
            outer, inner, body = spine.name, spine.body.name, spine.body.body
            self.assertNotEqual(outer, inner)
            if body == Var(inner):
                return count
            self.assertIsInstance(body, App)
            self.assertEqual(body.fn, Var(outer))
            spine = body.arg
            count += 1

    def boolean(self, term):
        value = self.run_target(term)
        yes, no = c.I(), Lam("a", Lam("b", Var("a")))
        marker = self.run_target(c.apply(value, yes, no), self.observation_budget)
        key = alpha_key(marker)
        self.assertIn(key, (alpha_key(yes), alpha_key(no)))
        return key == alpha_key(yes)

    def test_exact_required_representations(self):
        self.assertEqual(pretty(c.TRUE()), "(lam t. (lam f. t))")
        self.assertEqual(pretty(c.FALSE()), "(lam t. (lam f. f))")
        self.assertEqual(pretty(c.NUM(2)), "(lam s. (lam z. (s (s z))))")
        self.assertEqual(pretty(c.PAIR()), "(lam a. (lam b. (lam p. ((p a) b))))")
        self.assertEqual(pretty(c.Z()),
                         "(lam g. ((lam x. (g (lam v. ((x x) v)))) (lam x. (g (lam v. ((x x) v))))))")
        self.assertEqual(alpha_key(c.NUM(0)), alpha_key(c.FALSE()))

    def test_all_combinators_are_closed_pure_and_deterministic(self):
        def check_tree(term):
            self.assertIn(type(term), (Var, Lam, App))
            if isinstance(term, Lam):
                check_tree(term.body)
            elif isinstance(term, App):
                check_tree(term.fn)
                check_tree(term.arg)

        with patch("MySolution.target_ast.evaluate", side_effect=AssertionError("builder evaluated")):
            for builder in BUILDERS + (lambda: c.NUM(4),):
                with self.subTest(builder=builder):
                    term = builder()
                    check_tree(term)
                    self.assertEqual(free_vars(term), set())
                    self.assertEqual(term, builder())

    def test_numerals_successor_predecessor_zero_test(self):
        for n in range(6):
            with self.subTest(n=n):
                self.assertEqual(self.natural(c.NUM(n)), n)
                self.assertEqual(self.natural(c.apply(c.SUCC(), c.NUM(n))), n + 1)
                self.assertEqual(self.natural(c.apply(c.PRED(), c.NUM(n))), max(n - 1, 0))
                self.assertEqual(self.boolean(c.apply(c.ISZERO(), c.NUM(n))), n == 0)
        for invalid in (-1, True, 1.5, "2"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                c.NUM(invalid)

    def test_arithmetic_and_all_comparisons(self):
        operations = ((c.ADD, lambda m, n: m + n, self.natural),
                      (c.SUB, lambda m, n: max(m - n, 0), self.natural),
                      (c.MUL, lambda m, n: m * n, self.natural),
                      (c.LT, lambda m, n: m < n, self.boolean),
                      (c.LE, lambda m, n: m <= n, self.boolean),
                      (c.GT, lambda m, n: m > n, self.boolean),
                      (c.GE, lambda m, n: m >= n, self.boolean),
                      (c.EQ, lambda m, n: m == n, self.boolean),
                      (c.NE, lambda m, n: m != n, self.boolean))
        for builder, expected, observe in operations:
            for m in range(4):
                for n in range(4):
                    with self.subTest(operation=builder.__name__, m=m, n=n):
                        self.assertEqual(observe(c.apply(builder(), c.NUM(m), c.NUM(n))), expected(m, n))

    def test_boolean_truth_tables(self):
        for left in (False, True):
            boolean = c.TRUE if left else c.FALSE
            self.assertEqual(self.boolean(c.apply(c.NOT(), boolean())), not left)
            for right in (False, True):
                other = c.TRUE if right else c.FALSE
                for builder, expected in ((c.AND, left and right), (c.OR, left or right)):
                    with self.subTest(operation=builder.__name__, left=left, right=right):
                        self.assertEqual(self.boolean(c.apply(builder(), boolean(), c.delay(other()))), expected)

    def test_delayed_control_skips_divergence(self):
        dup = Lam("x", App(Var("x"), Var("x")))
        loop = App(dup, dup)
        self.assertFalse(self.boolean(c.apply(c.AND(), c.FALSE(), c.delay(loop))))
        self.assertTrue(self.boolean(c.apply(c.OR(), c.TRUE(), c.delay(loop))))
        self.assertEqual(self.natural(c.apply(c.IF(), c.TRUE(), c.delay(c.NUM(1)), c.delay(loop))), 1)
        self.assertEqual(self.natural(c.apply(c.IF(), c.FALSE(), c.delay(loop), c.delay(c.NUM(2)))), 2)
        for builder, left in ((c.AND, c.TRUE), (c.OR, c.FALSE)):
            result = evaluate(c.apply(builder(), left(), c.delay(loop)), 100)
            self.assertEqual(result.status, "exhausted")
            self.assertEqual(result.steps, 100)

    def test_pairs_and_nested_pairs(self):
        pair = c.apply(c.PAIR(), c.NUM(2), c.TRUE())
        self.assertEqual(self.natural(c.apply(c.FST(), pair)), 2)
        self.assertTrue(self.boolean(c.apply(c.SND(), pair)))
        nested = c.apply(c.PAIR(), pair, c.NUM(3))
        self.assertTrue(self.boolean(c.apply(c.SND(), c.apply(c.FST(), nested))))
        self.assertEqual(self.natural(c.apply(c.SND(), nested)), 3)

    def test_cbv_recursion_factorial(self):
        n = Var("n")
        body = c.apply(c.IF(), c.apply(c.ISZERO(), n), c.delay(c.NUM(1)),
                       c.delay(c.apply(c.MUL(), n,
                                       c.apply(Var("fact"), c.apply(c.PRED(), n)))))
        factorial = c.apply(c.Z(), Lam("fact", Lam("n", body)))
        self.assertIsInstance(self.run_target(factorial), Lam)
        self.assertEqual(self.natural(c.apply(factorial, c.NUM(0))), 1)
        self.assertEqual(self.natural(c.apply(factorial, c.NUM(4))), 24)

    def test_delay_is_fresh_and_application_preserves_free_names(self):
        original = App(Var("u"), Lam("u_1", Var("s")))
        delayed = c.delay(original)
        self.assertEqual(delayed.name, "u_2")
        self.assertEqual(delayed.body, original)
        self.assertEqual(free_vars(delayed), {"u", "s"})
        for builder in BUILDERS:
            self.assertEqual(free_vars(c.apply(builder(), original)), {"u", "s"})


if __name__ == "__main__":
    unittest.main()
