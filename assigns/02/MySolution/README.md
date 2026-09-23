## 1. Extend the AST operations

`t0erm_size`
- `T0Mpair` - The pair constructor is a node, so the size is 1 + the sizes of `arg1` and `arg2`.
- `T0Mpfst` - The projection constructor is a node, so the size is 1 + the size of `arg1`.
- `T0Mpsnd` - The projection constructor is a node, so the size is 1 + the size of `arg1`.

`t0erm_fvset`
- `T0Mpair` - Collect the free variables from both `arg1` and `arg2`.
- `T0Mpfst` - Collect the free variables from only `arg1`.
- `T0Mpsnd` - Collect the free variables from only `arg1`.

`t0erm_subst0`
- `T0Mpair` - Keep the pair constructor but substitute both `arg1` and `arg2`.
- `T0Mpfst` - Keep the projection constructor but substitute `arg1`.
- `T0Mpsnd` - Keep the projection constructor but substitute `arg1`.

After completing these, I asked Codex to check my answers. Codex confirmed that my answers were correct.

## 2. Extend call-by-value evaluation

`t0erm_cbv_evaluate0`
- `T0Mpair` - Evaluate `t1` and `t2`, then create a new `T0Mpair(t1, t2)`.
- `T0Mpfst` - Evaluate `t1`, then return `t1.arg1`.
- `T0Mpsnd` - Evaluate `t2`, then return `t1.arg2`.

After completing these, I asked Codex to check my answers. Codex confirmed that my answers were correct.

## 3. Test your implementation

I asked Codex to create the test cases listed as well as the three specific assertions. I checked the test 
cases and found the first and second assertions, but the third one was missing. I prompted Codex to add the 
third assertion. 

In the MySolution directory, run tests with `python -m unittest TEST.test02_lambda0`.

## 4. Translate an ATS2 eight-queens solution into a lambda-term

I prompted Codex to translate the source code in `original_ATS_eight_queens.md` to the lambda0 type and to 
create test03_queens.py. The tests return 92 solutions, the same as the original program.

Some of the notable functions and data structures translated to lambda0:
- In ATS, the board is represented by `int8 = (int, int, int, int, int, int, int, int)`. 
The first int represents the column position of the queen on row 0, the second int represents 
the column position of the queen on row 1, etc. 
In lambda0, the board is represented by a fixed length of nested pairs. So if we had 
`T0Mpair(5, T0Mpair(4, ...T0Mpair(3, T0Mint(-1))))`, that would mean the queen on row 0 is in 
column 5, the queen on row 1 is in column 4, the queen on row 7 is in column 3. The last `T0Mint(-1)` 
terminates the pair. 
- `board_get` and `board_set` are translated to `get` and `set` recursive T0Mfix functions in lambda0. 
`get` receives a board and a row index. It uses snd projection to get the second item in the tuple (the 
remaining rows), then once it reaches the requested row it returns the index of the queen on that row. 
`set` also uses snd projection to get to the requested row, then it changes the index of the queen on that row.
- `search` in ATS is a `T0Mfix` recursive function in lambda0. It returns `(count, solutions)` where `count` 
is the number of solutions and `solutions` is the complete list of 92 solutions.

In the MySolution directory, run tests with 
```
python queens_lambda0.py
python -m unittest TEST.test03_queens
```