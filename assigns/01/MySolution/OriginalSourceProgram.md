# Example: The Eight-Queens Puzzle

The eight-queens puzzle is the problem of positioning on a 8x8 chessboard 
8 queen pieces so that none of them can capture any other pieces using the 
standard chess moves defined for a queen piece. I will present as follows 
a solution to this puzzle in ATS, reviewing some of the programming features 
that have been covered so far. In particular, please note that every recursive 
function implemented in this solution is tail-recursive.

First, let us introduce a name for the integer constant 8 as follows:

```
#define N 8
```

After this declaration, each occurrence of the name `N` is to be replaced with 8. 
For representing board configurations, we define a type `int8` as follows:

```
typedef int8 =
(
  int, int, int, int, int, int, int, int
) // end of [int8]
```

A value of the type `int8` is a tuple of 8 integers where the first integer states 
the column position of the queen piece on the first row (row 0), and the second 
integer states the column position of the queen piece on the second row (row 1), 
and so on.

In order to print out a board configuration, we define the following functions:

```
fun print_dots (i: int): void =
  if i > 0 then (print ". "; print_dots (i-1)) else ()
// end of [print_dots]

fun print_row (i: int): void =
(
	print_dots (i); print "Q "; print_dots (N-i-1); print "\n";
) // end of [print_row]

fun print_board (bd: int8): void =
(
  print_row (bd.0); print_row (bd.1); print_row (bd.2); print_row (bd.3);
  print_row (bd.4); print_row (bd.5); print_row (bd.6); print_row (bd.7);
  print_newline ()
) // end of [print_board]
```

The function `print_newline` prints out a newline symbol and then flushes the 
buffer associated with the standard output. If the reader is unclear about 
what buffer flushing means, please feel free to ignore this aspect of `print_newline`.

As an example, if `print_board` is called on the board configuration represented by 
@(0, 1, 2, 3, 4, 5, 6, 7), then the following 8 lines are printed out:

```
Q . . . . . . . 
. Q . . . . . . 
. . Q . . . . . 
. . . Q . . . . 
. . . . Q . . . 
. . . . . Q . . 
. . . . . . Q . 
. . . . . . . Q
```

Given a board and the row number of a queen piece on the board, the following 
function `board_get` returns the column number of the piece:

```
fun board_get
  (bd: int8, i: int): int =
  if i = 0 then bd.0
  else if i = 1 then bd.1
  else if i = 2 then bd.2
  else if i = 3 then bd.3
  else if i = 4 then bd.4
  else if i = 5 then bd.5
  else if i = 6 then bd.6
  else if i = 7 then bd.7
  else ~1 // end of [if]
// end of [board_get]
```

Given a board, a row number `i` and a column number `j`, the following function 
`board_set` returns a new board that are the same as the original board except 
for `j` being the column number of the queen piece on row `i`:

```
fun board_set
  (bd: int8, i: int, j:int): int8 = let
  val (x0, x1, x2, x3, x4, x5, x6, x7) = bd
in
  if i = 0 then let
    val x0 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 1 then let
    val x1 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 2 then let
    val x2 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 3 then let
    val x3 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 4 then let
    val x4 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 5 then let
    val x5 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 6 then let
    val x6 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else if i = 7 then let
    val x7 = j in (x0, x1, x2, x3, x4, x5, x6, x7)
  end else bd // end of [if]
end // end of [board_set]
```

Clearly, the functions `board_get` and `board_set` are defined in a rather 
unwieldy fashion. This is entirely due to the use of tuples for representing 
board configurations. If we could use an array to represent a board configuration, 
then the implementation would be much simpler and cleaner. However, we have not 
yet covered arrays at this point.

Let us now implement two testing functions `safety_test1` and `safety_test2` as follows:

```
fun safety_test1
(
  i0: int, j0: int, i1: int, j1: int
) : bool =
(*
** [abs]: the absolute value function
*)
  j0 != j1 andalso abs (i0 - i1) != abs (j0 - j1)
// end of [safety_test1]

fun safety_test2
(
  i0: int, j0: int, bd: int8, i: int
) : bool =
  if i >= 0 then
    if safety_test1 (i0, j0, i, board_get (bd, i))
      then safety_test2 (i0, j0, bd, i-1) else false
    // end of [if]
  else true // end of [if]
// end of [safety_test2]
```

The functionalities of these two functions can be described as such:
- The function `safety_test1` tests whether a queen piece on row `i0` and column `j0`
  can capture another one on row `i` and column `j`.
- The function `safety_test2` tests whether a queen piece on row `i0` and column `j0`
  can capture any other pieces on a given board with a row number less than or equal to `i`.

We are now ready to implement the following function `search` based on a standard 
depth-first search (DFS) algorithm:

```
fun search
(
  bd: int8, i: int, j: int, nsol: int
) : int = (
//
if
j < N
then let
  val test = safety_test2 (i, j, bd, i-1)
in
  if test
    then let
      val bd1 = board_set (bd, i, j)
    in
      if i+1 = N
        then let
          val () = print! ("Solution #", nsol+1, ":\n\n")
          val () = print_board (bd1)
        in
          search (bd, i, j+1, nsol+1)
        end // end of [then]
        else (
          search (bd1, i+1, 0(*j*), nsol) // positioning next piece
        ) (* end of [else] *)
      // end of [if]
    end // end of [then]
    else search (bd, i, j+1, nsol)
  // end of [if]
end // end of [then]
else (
  if i > 0
    then search (bd, i-1, board_get (bd, i-1) + 1, nsol) else nsol
  // end of [if]
) (* end of [else] *)
//
) (* end of [search] *)
```

The return value of `search` is the number of distinct solutions to the eight queens 
puzzle. The symbol `print!` in the body of `search` is a special identifier in ATS: 
It takes an indefinite number of arguments and then applies `print` to each of them. 
Following is the first solution printed out by `print_board` during a call to the 
function `search`:

```
Q . . . . . . . 
. . . . Q . . . 
. . . . . . . Q 
. . . . . Q . . 
. . Q . . . . . 
. . . . . . Q . 
. Q . . . . . . 
. . . Q . . . .
```

There are 92 distinct solutions in total.
