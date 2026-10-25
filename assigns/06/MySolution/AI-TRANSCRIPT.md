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

## Prompt 4

### Prompt:
Implement task 4.

### Output Review and Testing:
The decoders turn Church-encoded results into Python numbers, booleans, and pairs. They use the same evaluator as the rest of the project. Running a program and decoding its result have separate step limits and counts. Decoding a nested pair shares one step limit across all its parts. If decoding runs out of steps or finds an invalid result, it reports the problem instead of returning an answer. `examples.py` contains the given demonstrations. `test_decoders.py` contains tests for invalid results, nested pairs, recursion, and insufficient step budgets. Running the file passes all tests. 

Running the command `python -B -m MySolution.demo` runs all examples in `examples.py` through compilation, target reduction, and decoding. All output is saved in `demo_output`. Each example saves its own file with the pure lambda terms, and `report.txt` shows the complete results. 

## Prompt 5

### Prompt:
Take a look at the testing and correctness argument section and verify that the test files include all required tests. If a test is not included, add it.

### Output Review and Testing:
Provided `TEST_COVERAGE.md`, which maps all 7 required tests to the corresponding file and method. 
