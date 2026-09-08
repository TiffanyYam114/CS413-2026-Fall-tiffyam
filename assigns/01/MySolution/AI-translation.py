"""A Python 3 translation of the ATS eight-queens example."""

import sys


N = 8
int8 = tuple[int, int, int, int, int, int, int, int]


def print_dots(i: int) -> None:
    """Print i empty board positions."""
    if i > 0:
        sys.stdout.write(". ")
        print_dots(i - 1)


def print_row(i: int) -> None:
    print_dots(i)
    sys.stdout.write("Q ")
    print_dots(N - i - 1)
    sys.stdout.write("\n")


def print_board(bd: int8) -> None:
    for i in range(N):
        print_row(bd[i])
    # The ATS print_newline call also flushes standard output.
    sys.stdout.write("\n")
    sys.stdout.flush()


def board_get(bd: int8, i: int) -> int:
    """Return a queen's column, or -1 for an invalid row."""
    if i == 0:
        return bd[0]
    if i == 1:
        return bd[1]
    if i == 2:
        return bd[2]
    if i == 3:
        return bd[3]
    if i == 4:
        return bd[4]
    if i == 5:
        return bd[5]
    if i == 6:
        return bd[6]
    if i == 7:
        return bd[7]
    return -1


def board_set(
    bd: int8, i: int, j: int
) -> int8:
    """Return bd with the queen in row i moved to column j."""
    if 0 <= i < N:
        board = list(bd)
        board[i] = j
        return tuple(board)  # type: ignore[return-value]
    return bd


def safety_test1(i0: int, j0: int, i1: int, j1: int) -> bool:
    return j0 != j1 and abs(i0 - i1) != abs(j0 - j1)


def safety_test2(
    i0: int, j0: int, bd: int8, i: int
) -> bool:
    if i >= 0:
        if safety_test1(i0, j0, i, board_get(bd, i)):
            return safety_test2(i0, j0, bd, i - 1)
        return False
    return True


def search(
    bd: int8, i: int, j: int, nsol: int
) -> int:
    """Perform the original tail-recursive DFS and return its solution count."""
    # ATS optimizes this tail-recursive function.  Python does not, so this
    # loop keeps the same state transitions without growing the call stack.
    while True:
        if j < N:
            if safety_test2(i, j, bd, i - 1):
                bd1 = board_set(bd, i, j)
                if i + 1 == N:
                    sys.stdout.write(f"Solution #{nsol + 1}:\n\n")
                    print_board(bd1)
                    j += 1
                    nsol += 1
                else:
                    bd, i, j = bd1, i + 1, 0
            else:
                j += 1
        elif i > 0:
            i, j = i - 1, board_get(bd, i - 1) + 1
        else:
            return nsol


if __name__ == "__main__":
    search((0, 0, 0, 0, 0, 0, 0, 0), 0, 0, 0)
