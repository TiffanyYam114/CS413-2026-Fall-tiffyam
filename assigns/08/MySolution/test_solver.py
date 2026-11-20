"""Task 2 checks against the supplied LAMBDA3 interpreter."""

from itertools import islice
import unittest
from unittest.mock import patch

from solver import Solver, L, event_to_dict, force_cell


def reference_events(size):
    """Small independent specification used to compare complete small traces."""
    def visit(board):
        row = len(board)
        if row == size:
            yield {"event": "solution", "board": board}
            return
        for column in range(size):
            fields = {"column": column, "row": row, "board": board}
            yield {"event": "try", **fields}
            if any(column == old or abs(column - old) == row - r
                   for r, old in enumerate(board)):
                yield {"event": "reject", **fields}
            else:
                placed = board + [column]
                yield {"event": "place", **fields, "board": placed}
                yield from visit(placed)
                yield {"event": "backtrack", **fields}
    yield from visit([])
    yield {"event": "done"}


class SolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = Solver()  # Parses and type-checks the actual source.

    def evaluate(self, expression):
        expr = L.D0Elets(self.solver.declarations, L.d0exp_parse(expression))
        L.d0exp_typecheck(expr)
        return L.d0exp_evaluate(expr)

    def test_cps_safety_both_diagonals_column_and_safe(self):
        # A same-row placement cannot arise: every candidate is in a new row.
        # The corresponding list collision is a repeated column.
        for column, previous, safe in [(2, 2, False), (2, 1, False),
                                        (2, 3, False), (2, 0, True)]:
            with self.subTest(column=column, previous=previous):
                stream = self.evaluate(
                    f"check_safe({column}, 1, list_cons({previous}, list_nil()), "
                    "lam (u: unit) => emit_lazy(make_event(1, 0, 0, list_nil()), "
                    "lam (v: unit) => empty_stream()), "
                    "lam (u: unit) => emit_lazy(make_event(2, 0, 0, list_nil()), "
                    "lam (v: unit) => empty_stream()))")
                self.assertEqual(event_to_dict(force_cell(stream).head)["event"],
                                 "place" if safe else "reject")
        # Continue past the newest queen and find an older diagonal conflict.
        stream = self.evaluate(
            "check_safe(2, 1, list_cons(4, list_cons(0, list_nil())), "
            "lam (u: unit) => empty_stream(), root_exhausted)")
        self.assertEqual(event_to_dict(force_cell(stream).head), {"event": "done"})

    def test_complete_small_traces_match_depth_first_specification(self):
        for size in (4, 5):
            with self.subTest(size=size):
                actual = list(self.solver.events(size))
                self.assertEqual(actual, list(reference_events(size)))
                self.assertEqual({e["event"] for e in actual},
                                 {"try", "place", "reject", "backtrack", "solution", "done"})

    def test_solution_resume_is_delayed_and_calls_failure_continuation(self):
        # A complete board calls success, which emits a solution. Resuming
        # that event invokes our supplied failure continuation (here: done).
        stream = self.evaluate(
            "search(4, 4, list_cons(2, list_cons(0, list_cons(3, "
            "list_cons(1, list_nil())))), on_solution, root_exhausted)")
        cell = force_cell(stream)
        self.assertEqual(event_to_dict(cell.head),
                         {"event": "solution", "board": [1, 3, 0, 2]})
        self.assertFalse(cell.tail.evaluated)
        self.assertEqual(event_to_dict(force_cell(cell.tail).head), {"event": "done"})

    def test_full_eight_queens_run(self):
        solutions = []
        board = []
        kinds = set()
        done_count = 0
        for event in self.solver.events(8):
            kind = event["event"]
            kinds.add(kind)
            if kind in ("try", "reject"):
                self.assertEqual(event["board"], board)
                self.assertEqual(event["row"], len(board))
                self.assertIn(event["column"], range(8))
                if kind == "reject":
                    self.assertTrue(any(event["column"] == c or
                                        abs(event["column"] - c) == len(board) - r
                                        for r, c in enumerate(board)))
            elif kind == "place":
                self.assertEqual(event["row"], len(board))
                self.assertEqual(event["board"], board + [event["column"]])
                board = event["board"]
            elif kind == "backtrack":
                self.assertEqual(event["column"], board[-1])
                self.assertEqual(event["row"], len(board) - 1)
                self.assertEqual(event["board"], board[:-1])
                board = event["board"]
            elif kind == "solution":
                self.assertEqual(event["board"], board)
                self.assertEqual(len(board), 8)
                solutions.append(tuple(board))
            else:
                self.assertEqual(kind, "done")
                self.assertEqual(board, [])
                done_count += 1
            for row, column in enumerate(board):
                self.assertTrue(all(column != old and abs(column - old) != row - r
                                    for r, old in enumerate(board[:row])))
        self.assertEqual(len(solutions), 92)
        self.assertEqual(len(set(solutions)), 92)
        self.assertEqual(solutions, sorted(solutions))
        self.assertEqual(solutions[0], (0, 4, 7, 5, 2, 6, 1, 3))
        self.assertEqual(solutions[-1], (7, 3, 0, 2, 5, 1, 6, 4))
        self.assertEqual(done_count, 1)
        self.assertEqual(len(kinds), 6)

    def test_open_and_bounded_prefix_do_not_run_later_search(self):
        original_lookup = L.d0env_search
        for size in range(4, 11):
            calls = []
            def observe(env, name):
                if name in ("search", "try_column", "safe", "check_safe"):
                    calls.append(name)
                return original_lookup(env, name)
            with self.subTest(size=size), patch.object(L, "d0env_search", observe):
                stream = self.solver.open(size)
                self.assertEqual(calls, [])
                self.assertFalse(stream.evaluated)
                first = force_cell(stream)
                self.assertEqual(event_to_dict(first.head)["event"], "try")
                self.assertNotIn("check_safe", calls)
                self.assertFalse(first.tail.evaluated)
                before = calls.copy()
                self.assertIs(force_cell(stream), first)  # Memoized cell.
                self.assertEqual(calls, before)
                second = force_cell(first.tail)
                self.assertIn("check_safe", calls)
                self.assertEqual(event_to_dict(second.head)["event"], "place")
                self.assertFalse(second.tail.evaluated)
                # Stop after exactly 32 cells; do not inspect cell 33.
                current = second.tail
                for _ in range(30):
                    cell = force_cell(current)
                    current = cell.tail
                self.assertFalse(current.evaluated)

    def test_delayed_failure_in_unrequested_tail(self):
        stream = self.evaluate(
            "emit_lazy(make_event(0, 0, 0, list_nil()), "
            "lam (u: unit) => lazy_make(lam (v: unit) => "
            "stcn_cons(make_event(0, 1 / 0, 0, list_nil()), empty_stream())))")
        first = force_cell(stream)
        self.assertEqual(event_to_dict(first.head)["event"], "try")
        self.assertFalse(first.tail.evaluated)
        with self.assertRaises(ZeroDivisionError):
            force_cell(first.tail)

    def test_done_is_last_and_tail_is_empty(self):
        stream = self.solver.open(4)
        count = 0
        while True:
            cell = force_cell(stream)
            if not cell.is_cons:
                break
            if event_to_dict(cell.head)["event"] == "done":
                count += 1
                self.assertFalse(cell.tail.evaluated)
                self.assertFalse(force_cell(cell.tail).is_cons)
            stream = cell.tail
        self.assertEqual(count, 1)

    def test_iterator_stops_at_requested_prefix(self):
        prefix = list(islice(self.solver.events(10), 1))
        self.assertEqual(prefix, [{"event": "try", "column": 0, "row": 0, "board": []}])

    def test_invalid_sizes(self):
        for size in (3, 11, True, 8.0, "8", None):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.solver.open(size)


if __name__ == "__main__":
    unittest.main()
