"""Small interface to the fixed, type-checked LAMBDA3 solver; no HTTP code."""

from pathlib import Path
import sys

LAMBDA_DIR = Path(__file__).resolve().parents[1] / "LAMBDA3"
if str(LAMBDA_DIR) not in sys.path:
    sys.path.insert(0, str(LAMBDA_DIR))
import lambda3 as L
from basics0 import fnlist_cons

SOURCE = Path(__file__).with_name("queens.lam")
KINDS = ("try", "place", "reject", "backtrack", "solution", "done")


def force_cell(stream):
    """Force exactly this cell through the supplied interpreter."""
    return L.d0exp_evaluate(L.D0Eop1("lazy_eval", L.D0Evar("stream")),
                            L.ENVcns("stream", stream, L.ENVnil()))


def event_to_dict(value):
    """Convert an event value, without touching its stream tail."""
    kind, column, row, board = value.arg1
    name = KINDS[kind.arg1]
    event = {"event": name}
    if name in KINDS[:4]:
        event.update(column=column.arg1, row=row.arg1)
    if name != "done":
        columns = []
        items = board.arg1
        while isinstance(items, fnlist_cons):
            columns.append(items.arg1.arg1)
            items = items.arg2
        event["board"] = columns
    return event


class Solver:
    """Load trusted source once; each open creates an independent lazy stream."""

    def __init__(self):
        self.declarations = L.d0cls_parse(SOURCE.read_text(encoding="utf-8"))
        L.d0cls_typecheck(self.declarations)
        self.entry = L.d0exp_evaluate(
            L.D0Elets(self.declarations, L.D0Evar("queens_open")))

    def open(self, size=8):
        if type(size) is not int or not 4 <= size <= 10:
            raise ValueError("size must be an integer from 4 through 10")
        return L.d0exp_evaluate(
            L.D0Eapp(L.D0Evar("open"), L.D0Eint(size)),
            L.ENVcns("open", self.entry, L.ENVnil()))

    def events(self, size=8):
        """Iterate on demand, leaving the tail after each yield unforced."""
        stream = self.open(size)
        while True:
            cell = force_cell(stream)
            if not cell.is_cons:
                return
            event = event_to_dict(cell.head)
            yield event
            if event["event"] == "done":
                return
            stream = cell.tail


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Consume the lazy LAMBDA3 solver")
    parser.add_argument("--size", type=int, choices=range(4, 11), default=8)
    parser.add_argument("--limit", type=int, help="Print only this many events")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    solver = Solver()
    if args.limit is not None:
        from itertools import islice
        for event in islice(solver.events(args.size), args.limit):
            print(json.dumps(event))
    else:
        solutions = 0
        for event in solver.events(args.size):
            if event["event"] == "solution":
                solutions += 1
                print(json.dumps(event))
            elif event["event"] == "done":
                print(json.dumps({"event": "done", "solutions": solutions}))
