"""Unit tests for the eight-queens translation.

Run with: python -m unittest tests.py
"""

import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("AI-translation.py")
SPEC = importlib.util.spec_from_file_location("ai_translation", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load {MODULE_PATH}")
queens = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(queens)


class EightQueensTests(unittest.TestCase):
    """Tests for every top-level function in AI-translation.py."""

    def test_print_dots(self) -> None:
        output = io.StringIO()
        with patch.object(queens.sys, "stdout", output):
            queens.print_dots(3)
            queens.print_dots(0)
            queens.print_dots(-1)

        self.assertEqual(output.getvalue(), ". . . ")

    def test_print_row(self) -> None:
        output = io.StringIO()
        with patch.object(queens.sys, "stdout", output):
            queens.print_row(0)
            queens.print_row(2)
            queens.print_row(7)

        self.assertEqual(
            output.getvalue(),
            "Q . . . . . . . \n"
            ". . Q . . . . . \n"
            ". . . . . . . Q \n",
        )

    def test_print_board(self) -> None:
        board = (0, 1, 2, 3, 4, 5, 6, 7)
        expected = "".join(
            ". " * column + "Q " + ". " * (queens.N - column - 1) + "\n"
            for column in board
        ) + "\n"
        output = io.StringIO()
        with patch.object(queens.sys, "stdout", output):
            queens.print_board(board)

        self.assertEqual(output.getvalue(), expected)

    def test_board_get(self) -> None:
        board = (7, 6, 5, 4, 3, 2, 1, 0)

        self.assertEqual([queens.board_get(board, i) for i in range(8)], list(board))
        self.assertEqual(queens.board_get(board, -1), -1)
        self.assertEqual(queens.board_get(board, 8), -1)

    def test_board_set(self) -> None:
        board = (0, 0, 0, 0, 0, 0, 0, 0)

        moved_board = queens.board_set(board, 3, 5)
        self.assertEqual(moved_board, (0, 0, 0, 5, 0, 0, 0, 0))
        self.assertEqual(board, (0, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(queens.board_set(board, 0, 7), (7, 0, 0, 0, 0, 0, 0, 0))
        self.assertEqual(queens.board_set(board, 7, 4), (0, 0, 0, 0, 0, 0, 0, 4))
        self.assertEqual(queens.board_set(board, 4, -3), (0, 0, 0, 0, -3, 0, 0, 0))
        self.assertIs(queens.board_set(board, -1, 5), board)
        self.assertIs(queens.board_set(board, 8, 5), board)

    def test_safety_test1(self) -> None:
        self.assertTrue(queens.safety_test1(0, 0, 1, 2))
        self.assertFalse(queens.safety_test1(0, 0, 1, 0))
        self.assertFalse(queens.safety_test1(0, 0, 1, 1))
        self.assertFalse(queens.safety_test1(0, 0, 0, 0))
        self.assertFalse(queens.safety_test1(0, 1, 4, 5))

    def test_safety_test2(self) -> None:
        board = (0, 4, 7, 5, 2, 6, 1, 3)

        self.assertTrue(queens.safety_test2(1, 4, board, 0))
        self.assertFalse(queens.safety_test2(1, 0, board, 0))
        self.assertFalse(queens.safety_test2(1, 1, board, 0))
        self.assertTrue(queens.safety_test2(0, 0, board, -1))
        self.assertTrue(queens.safety_test2(4, 2, board, 3))
        self.assertFalse(queens.safety_test2(4, 4, board, 3))

    def test_search_finds_all_eight_queen_solutions(self) -> None:
        output = io.StringIO()
        empty_board = (0, 0, 0, 0, 0, 0, 0, 0)
        with patch.object(queens.sys, "stdout", output):
            solution_count = queens.search(empty_board, 0, 0, 0)

        self.assertEqual(solution_count, 92)
        self.assertEqual(output.getvalue().count("Solution #"), 92)

    def test_search_handles_completed_or_offset_states(self) -> None:
        empty_board = (0, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(queens.search(empty_board, 0, queens.N, 0), 0)

        output = io.StringIO()
        with patch.object(queens.sys, "stdout", output):
            solution_count = queens.search(empty_board, 0, 0, 5)

        self.assertEqual(solution_count, 97)
        self.assertTrue(output.getvalue().startswith("Solution #6:"))
        self.assertIn("Solution #97:", output.getvalue())


if __name__ == "__main__":
    unittest.main()
