AI used: Codex

## Prompt 1

### Prompt: 
Implement task 1. The fresh-name policy is to choose the smallest positive suffix available for a binder: `y_1`, `y_2`, and so on.

### Output Review and Testing:
Only Var, Lam, and App were used. There is a `fresh_name` function that generates a fresh variable according to the policy I gave it. Includes a printer function `pretty` using `x`, `(lam x. body)`, and `(fn arg)`. Also includes functions `free_vars` to return free variables and `substitute` for capture-avoiding substitution. The function `evaluate` takes as parameters an expression and a number of steps. If the expression is completed, it returns "completed", the completed value, and the number of steps it took; if the expression is not completed, it returns "exhausted", None, and the number of steps it took. Also provided tests in `test_target_ast.py`. Running the file passes all tests. 

## Prompt 2

### Prompt:
Implement task 2.

### Output Review and Testing:
`church_encodings.py` contains all required functions. `TRUE`, `PAIR`, and `Z` do not use the target ast constructors and are instead expanded into pure terms. Predecessor iterates pairs from `(0, 0)` to `(current, current + 1)`, then returns a projection of the first argument. Also provided tests in `test_church_encodings.py` for arithmetic, comparisons, truth tables, pairs, and factorial. Running the file passes all tests.

## Prompt 3

### Prompt:
Implement task 3.

### Output Review and Testing:
Provides an entry point `compile_expr(source_expression)`. The compiler recursively translates all required
constructors through the supplied visitor interface without evaluating them. Uses the translation rules given, as well as the remaining rules documented in `DESIGN.md`. The fresh-name policy used is the same as before: choose the smallest positive suffix available for a binder: `y_1`, `y_2`, and so on. Also provided tests in `test_compiler.py` for all operators and comparisons, factorial, Fibonacci, and invalid source code. Running the file passes all tests.
