# Task 2: Church encoding library

`church_encodings.py` implements ENC-01 through ENC-04 in REQUIREMENTS.md.
The representations for booleans, numerals, pairs, and `Z` come from
Assign06.md and REQUIREMENTS.md section 3.3. All other constructions below
are compositions of these representations. No third-party code is used.

## Interface

Every uppercase function is a zero-argument builder for a closed target term,
except `NUM(n)`, which takes a nonnegative Python integer literal. Calling a
builder expands its complete implementation into `Var`, `Lam`, and `App`
nodes. There are no target constants, unresolved library variables, source
nodes, or evaluator hooks. Builders never evaluate their inputs.

Use `apply(fn, *args)` for left-associated application. For example:

```python
from MySolution.church_encodings import ADD, NUM, apply
from MySolution.target_ast import evaluate

term = apply(ADD(), NUM(2), NUM(3))
result = evaluate(term, max_steps=1000)
```

The result is an encoded lambda value; it is not a Python integer. Results
can retain redexes inside their bodies under weak evaluation. Task 4's
`decoders.py` provides bounded natural, boolean, and recursive pair observers.
Encoding tests also use pure observation contexts without normalizing beneath
lambdas.

| Builder | Target argument contract | Meaning |
| --- | --- | --- |
| `I` | one value | Identity / dummy forcing value |
| `TRUE`, `FALSE` | two values | Select first / second |
| `NUM(n)` | step function, initial value | Apply step n times |
| `PAIR` | first value, second value, selector | Apply selector to both components |
| `FST`, `SND` | encoded pair | Select first / second component |
| `Z` | recursive function generator | Call-by-value fixed point |
| `SUCC`, `PRED`, `ISZERO` | numeral | Successor, saturated predecessor, zero test |
| `ADD`, `SUB`, `MUL` | two numerals | Addition, truncated subtraction, multiplication |
| `LT`, `LE`, `GT`, `GE`, `EQ`, `NE` | two numerals | `<`, `<=`, `>`, `>=`, `==`, `!=` |
| `NOT` | boolean | Negation |
| `IF` | boolean, true thunk, false thunk | Force the selected branch |
| `AND`, `OR` | boolean, right-operand thunk | Short-circuit boolean operation |

`delay(term)` wraps any term, including an open term, in an unused lambda
parameter. Its name is the first available `u_1`, `u_2`, etc., checked against
all free and bound names of the term. `apply` introduces no binders. Consequently
neither helper captures names in its arguments. Fixed names inside closed
combinators bind only the combinator's own code; they do not reserve source
identifiers. Returned terms are immutable and repeated builds are deterministic.

## Arithmetic and predecessor

The following notation abbreviates expanded target terms. Multiple lambda
parameters stand for nested single-parameter lambdas; application associates
to the left.

```text
SUCC = lam n s z. s (n s z)
ADD  = lam m n s z. m s (n s z)
MUL  = lam m n s z. m (n s) z
SUB  = lam m n. n PRED m
ISZERO = lam n. n (lam unused. FALSE) TRUE
```

Predecessor uses a pair to remember the previous count alongside the current
count. Start with `(0, 0)` and repeat this transition n times:

```text
STEP = lam p. PAIR (SND p) (SUCC (SND p))
PRED = lam n. FST (n STEP (PAIR NUM(0) NUM(0)))
```

The successive pairs are `(0, 0)`, `(0, 1)`, `(1, 2)`, `(2, 3)`, and so on.
After n transitions the first component is `max(n - 1, 0)`. At zero there
are no transitions, so projecting the first component correctly returns zero.
The second component advances entirely through the Church successor term.
Subtraction applies predecessor n times to m, so it also stops at zero.

Comparisons compose subtraction, zero testing, and boolean operations:

```text
LE m n = ISZERO (SUB m n)
GE m n = LE n m
LT m n = NOT (LE n m)
GT m n = NOT (LE m n)
EQ m n = AND (LE m n) (delay (LE n m))
NE m n = NOT (EQ m n)
```

## Call-by-value control and recursion

```text
IF  = lam c t f. (c t f) I
AND = lam p q. IF p q (delay FALSE)
OR  = lam p q. IF p (delay TRUE) q
```

For `AND` and `OR`, q must be a lambda thunk, not an already executing
right-hand expression. For example, use
`apply(AND(), TRUE(), delay(FALSE()))`. Both branch thunks are values, so
ordinary call-by-value application evaluates neither branch body. The
selected thunk alone is applied to `I`. The compiler must preserve this
interface when translating source `and` and `or`.

`Z` uses exactly the call-by-value construction prescribed in the assignment.
Its recursive self-application is delayed beneath `lam v`, allowing the
recursive function to become a lambda value before recursive calls occur.
The factorial test uses `Z`, delayed conditional branches, `ISZERO`, `PRED`,
and `MUL` to compute factorial(4) = 24 entirely by target beta reduction.

## Verification

Run from `assigns/06/` with Python 3.12 or later:

```powershell
python -B -m unittest MySolution.test_church_encodings MySolution.test_target_ast -v
```

Tests validate every combinator's closedness and pure target structure, exact
required representations, all boolean truth tables, arithmetic/comparison
grids including zero and equal operands, predecessor of zero, nested pairs,
and recursion. They also check that unused divergent branches terminate while
selected divergent boolean operands exhaust a finite budget.

Tests allow 50,000 execution steps and a separate 50,000 observation steps
per observation context. Natural observation applies the assignment's pure
`STEP` and `BASE` context, then counts the resulting finite spine structurally.
Boolean observation selects one of two distinct closed markers and compares
its structure up to alpha-renaming. Host arithmetic occurs only in literal
construction and test expectations, never to execute generated arithmetic.
