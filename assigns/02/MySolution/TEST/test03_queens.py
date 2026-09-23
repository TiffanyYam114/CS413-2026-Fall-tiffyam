"""Black-box tests for the lambda-term translation of ATS eight queens."""

import unittest

from lambda0 import T0Mbtf, T0Mint, T0Mpair, t0erm_fvset
from queens_lambda0 import make_queens_term, safety_test1_term, t0erm_cbv_evaluate0


def decode_pair_list(value):
    """Inspection only: it does not participate in object-language search."""
    items = []
    while isinstance(value, T0Mpair):
        items.append(value.arg1)
        value = value.arg2
    if not isinstance(value, T0Mint) or value.arg1 != -1:
        raise AssertionError("not a lambda0 pair-list")
    return items


def run(size):
    result = t0erm_cbv_evaluate0(make_queens_term(size))
    assert isinstance(result, T0Mpair) and isinstance(result.arg1, T0Mint)
    boards = [[cell.arg1 for cell in decode_pair_list(board)]
              for board in decode_pair_list(result.arg2)]
    return result.arg1.arg1, boards


def assert_legal_board(test, board, size):
    test.assertEqual(len(board), size)
    test.assertEqual(set(board), set(range(size)), "queens share a column")
    for row0 in range(size):
        for row1 in range(row0 + 1, size):
            test.assertNotEqual(abs(row0 - row1), abs(board[row0] - board[row1]),
                                "queens share a diagonal")


class QueensTranslationTests(unittest.TestCase):
    def test_eight_queens_matches_the_ats_count_and_enumeration(self):
        term = make_queens_term()
        self.assertEqual(t0erm_fvset(term), frozenset())
        count, boards = run(8)
        # The supplied ATS source prints every board and finally reports 92.
        self.assertEqual(count, 92)
        self.assertEqual(len(boards), 92)
        self.assertEqual(len({tuple(board) for board in boards}), 92)
        for board in boards:
            assert_legal_board(self, board, 8)

    def test_conflict_checking_is_reflected_in_every_generated_board(self):
        # These pairwise checks exercise column and diagonal exclusions, which
        # are the two clauses of the inlined ATS safety_test1.
        count, boards = run(4)
        self.assertEqual(count, 2)
        for board in boards:
            assert_legal_board(self, board, 4)

    def test_translated_safety_test1(self):
        def safe(i0, j0, i1, j1):
            value = t0erm_cbv_evaluate0(safety_test1_term(
                T0Mint(i0), T0Mint(j0), T0Mint(i1), T0Mint(j1)))
            self.assertIsInstance(value, T0Mbtf)
            return value.arg1

        self.assertFalse(safe(0, 0, 1, 0))  # common column
        self.assertFalse(safe(0, 0, 1, 1))  # common diagonal
        self.assertTrue(safe(0, 0, 1, 2))   # no queen conflict

    def test_smaller_supported_board_sizes(self):
        # Known n-queens counts; the search bound is a term constant, not a
        # Python search implementation.
        for size, expected in ((1, 1), (2, 0), (3, 0), (4, 2)):
            count, boards = run(size)
            self.assertEqual(count, expected)
            self.assertEqual(len(boards), expected)


if __name__ == "__main__":
    unittest.main()
