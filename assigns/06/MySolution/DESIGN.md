## Translation rules

`C[e]` means the translation of expression `e`. Below, `A B C` means `App(App(A, B), C)`. Multiple lambda parameters mean nested one-argument functions. `D[T]` means a delayed expression, `lam u_k. T`, with a fresh variable. `I` is the identity function, `lam w. w`. 

```
C[D0Eint(n)]              = NUM(n), n >= 0
C[D0Ebtf(true)]           = TRUE
C[D0Ebtf(false)]          = FALSE
C[D0Evar(x)]              = x
C[D0Elam(x, e)]           = lam x. C[e]
C[D0Eapp(fn, arg)]        = C[fn] C[arg]
C[D0Elet(x, init, body)]  = (lam x. C[body]) C[init]
C[D0Efix(f, x, body)]     = Z (lam f. lam x. C[body])
C[D0Eif0(c, t, f)]        = (C[c] D[C[t]] D[C[f]]) I
C[D0Epair(a, b)]          = PAIR C[a] C[b]
C[D0Epfst(e)]             = FST C[e]
C[D0Epsnd(e)]             = SND C[e]
C[D0Eop1("not", e)]       = NOT C[e]
C[D0Eop2("+", a, b)]      = ADD C[a] C[b]
C[D0Eop2("-", a, b)]      = SUB C[a] C[b]
C[D0Eop2("*", a, b)]      = MUL C[a] C[b]
C[D0Eop2("<", a, b)]      = LT C[a] C[b]
C[D0Eop2("<=", a, b)]     = LE C[a] C[b]
C[D0Eop2(">", a, b)]      = GT C[a] C[b]
C[D0Eop2(">=", a, b)]     = GE C[a] C[b]
C[D0Eop2("==", a, b)]     = EQ C[a] C[b]
C[D0Eop2("!=", a, b)]     = NE C[a] C[b]
C[D0Eop2("and", a, b)]    = AND C[a] D[C[b]]
C[D0Eop2("or", a, b)]     = OR C[a] D[C[b]]
```

Negative literals and unsupported operators raise `CompilationError` with the bad input in the message. The compiler checks unused branches and unapplied function bodies too. Skipping code during execution does not make unsupported syntax acceptable. Input shapes and operation types are assumed valid; the compiler does not check types.

## Predecessor Explanation

To get the predecessor means to subtract one. However, since negative numbers are not supported, the predecessor of zero is zero. This implementation builds the predecessor using incrementing pairs of type `Var`. The first pair starts at `(0, 0)`. We will call the first argument `previous`, and the second argument `current`. In each step, perform a `SND` projection to get `current`. Build a new `PAIR` with `(current, SUCC(current))`, where `SUCC(current)` is `current + 1`. So after one step we would have `(0, 1)`. The Church numeral itself represents how many times to repeat the step. Church 3 means to apply the step three times. Once we have performed that many steps, perform a `FST` projection to get the predecessor.

Examples:
- Church 3 means to apply the step three times. The sequence is `(0, 0)`, `(0, 1)`, `(1, 2)`, `(2, 3)`. So the predecessor of 3 is 2.
- Church 0 means to apply the step three times. The sequence is `(0, 0)`. So the predecessor of 0 is 0.

### Subtraction with Predecessor

Subtraction applies predecessor repeatedly, which prevents negative answers. 
To calculate `m - n`, start with `m` and apply predecessor `n` times.

Examples:
- For `5 - 3`:
```
5 → 4 → 3 → 2
```
- For `2 - 5`:
```
2 → 1 → 0 → 0 → 0 → 0
```

Since predecessor of zero is zero, subtraction never produces a negative number.

## Fresh-name Policy

A binder introduces a name, such as a function parameter. The compiler keeps source binders and their scopes. A let name applies only to its body, not its initializer. A fix binds its function name and parameter in its body. If those names match, the parameter is the inner binding and takes priority.

New names use the smallest available positive suffix. Renaming `y` tries `y_1`, `y_2`, and so on. If `y_1` and `y_3` are taken, it chooses `y_2`. Renaming an existing `y_1` tries `y_1_1`, then `y_1_2`. Delayed expressions use `u_1`, `u_2`, and so on, avoiding every name in the wrapped expression. Substitution also avoids names in the replacement and the variable being replaced. Repeating the same operation therefore gives the same names.

This prevents capture: accidentally changing a free variable into a bound one. Library functions are closed, meaning they have no free variables, and arguments are placed outside their binders. Common source names such as `s`, `z`, `t`, `f`, and `x` remain usable. Translation preserves free variables: `FV(C[e]) = FV(e)`. The compiler does not change source objects, and target objects are immutable.

## Evaluation and control

The implementation uses weak, left-to-right call-by-value evaluation.

“Weak” means evaluation stops when it reaches a lambda. The evaluator does not enter the function’s body until the function is called. When applying a target lambda, the evaluator substitutes the argument value for the parameter in the body. This substitution avoids accidentally changing which binder a variable belongs to.

“Left-to-right” specifies the order of evaluation. In a function application, the evaluator handles the function expression on the left first, then the argument expression on the right.

“Call-by-value” means the argument must be evaluated before the function is applied, even if the function does not use that argument. For example, `(lam x. 0) LOOP` exhausts its step budget because the looping argument runs before the function can return zero.

Together, these rules mean: evaluate the function until it becomes a lambda, evaluate the argument until it becomes a lambda, then substitute the argument into the function’s body and continue.

Let initializers are evaluated before their bodies, and arithmetic operands and pair components are evaluated from left to right. Conditionals evaluate only the selected branch: `true` evaluates the first branch, and `false` evaluates the second branch. Boolean operations also skip unnecessary work: if the operation is `and` and the left operand is `false`, it will return `false`; if the operation is `or` and the left operand is `true`, it will return `true`. `and` and `or` will only evaluate the right operand when evaluating the left operand is not enough to produce a value. The compiler preserves this behavior by wrapping expressions in delayed functions called thunks, then running only the selected thunk.

Execution and observation have separate budgets and step counts. A value needs zero steps, and reaching a value on the last step counts as completion. If another step is needed after the budget is spent, the evaluator returns `exhausted`. This means the computation needs a larger budget, but it does not prove that the program runs forever. The demo allows 50,000 execution steps, 50,000 observation steps, and 200 steps for looping examples.

## Correctness argument

The compiler preserves the meaning of a source program. For a well-typed program that evaluates to a natural number, boolean, or pair, running and decoding the compiled program should produce the same answer, provided enough evaluation steps are available. For example, if the source program returns `5`, its compiled version should return a Church-encoded value that decodes to `5`.

The translation rules preserve how expressions are evaluated and how variables are bound. Function applications evaluate the function first and then the argument. A let expression becomes a function call, so its initializer is evaluated before its body, and its name is bound only inside the body. Capture-avoiding substitution and fresh names prevent the compiler from accidentally changing which binding a variable refers to. 

Conditionals and boolean operations preserve which expressions actually run. The compiler implements delayed branches called thunks, then runs only the selected thunk. This allows an expression such as `if true then 1 else LOOP` to return `1` without entering the loop. Pairs evaluate both components before storing their values. Recursion uses the call-by-value `Z` combinator to supply the function’s own name for recursive calls. 

Lastly, tests on given examples compare expected answers with computed results, so the program is guaranteed to be correct for these examples and similar expressions. See `TEST_COVERAGE.md` for test coverage.

## Design tradeoffs and limitations

Pair-based predecessor makes sense, since negative numbers are not supported, but it requires extra work. Keeping `(previous, current)` makes subtraction and the zero case straightforward, but building and accessing pairs creates extra function calls. Subtracting by a large number would require a lot of extra steps.

Step budgets limit the number of operations a program can do, so programs can be terminated if they exhaust the budget, even if the program is valid. 

The decoder requires the user to input whether a value is expected to be a `num` or `bool`. This keeps decoding simple but requires a little more work from the user.