AI used: Codex

## Prompt 1

# Prompt: 
Implement task 1. The fresh-name policy is to choose the smallest positive suffix available for a binder: `y_1`, `y_2`, and so on.

# Output Review and Testing:
Only Var, Lam, and App were used. There is a `fresh_name` function that generates a fresh variable according to the policy I gave it. Includes a printer function `pretty` using `x`, `(lam x. body)`, and `(fn arg)`. Also includes functions `free_vars` to return free variables and `substitute` for capture-avoiding substitution. The function `evaluate` takes as parameters an expression and a number of steps. If the expression is completed, it returns "completed", the completed value, and the number of steps it took; if the expression is not completed, it returns "exhausted", None, and the number of steps it took. Also provided tests in `test_target_ast.py`. Running the file passes all tests. 
