# Assignment 6

Requires Python 3.12 or later.

## Test and Demo Commands

Run commands from `assigns/06/`.
To test a single file `test_target_ast`, `test_church_encodings`, `test_compiler`, `test_decoders`, 
run the following command:
```
python -B -m unittest <file name> -v
```

To test all files, run the following command:
```
python -B -m unittest MySolution.test_target_ast MySolution.test_church_encodings MySolution.test_compiler MySolution.test_decoders -v
```

To run the demo, run the following command:
```
python -B -m MySolution.demo
```

## Modules and documents

- `lambda1_vp.py`: Supplied source AST and visitor interfaces.
- `target_ast.py`: AST with only `Var`, `Lam`, and `App`. Has printing, substitution, and evaluation with a number of steps.
- `church_encodings.py`: Builds target ASTs for specific encodings.
- `compiler.py`: Translates a source AST into pure lambda calculus.
- `decoders.py`: Computes the result of the compiled program and returns a value or no value if the all steps are exhausted.
- `examples.py`: Source AST examples.
- `demo.py`: Runs explicit examples and records output.
- `test_*.py`: Unittest suites for their corresponding files.
- `DESIGN.md`: complete translation rules, naming, evaluation, and correctness.
- `TEST_COVERAGE.md`: Checklist mapping all required tests to test methods.
- `AI-TRANSCRIPT.md`: AI usage record.

## Budgets

A budget limits the number of beta-value steps. Running a compiled program and decoding its result have
separate budgets and step counts.

| Operation | Default step budget |
| --- | ---: |
| Demo execution of terminating examples | 50,000 |
| Demo execution of known looping examples | 200 |
| Decoding with `observe()` or the individual observers | 50,000 |
| Execution through `observe()` | 50,000 |
| Calling `evaluate()` directly | 10,000 |

All terminating demo examples finish within the default budgets. Change the demo budgets with:

```
python -B -m MySolution.demo --execution-budget 50000 --observation-budget 50000 --loop-budget 200
```

Budgets must be nonnegative integers. A lambda value needs zero steps, and a result reached on the last allowed step still counts as completed. Running out of steps reports `exhausted`; it does not prove that the program loops forever. If execution runs out of steps, decoding is skipped. If decoding runs out of steps, no decoded answer is returned. 

## Limitations

- Programs must be built as Python AST objects.
- Numbers are natural numbers only: `0`, `1`, `2`, and so on. Negative literals, division, and unsupported operators are rejected. Subtraction stops at zero.
- The decoder needs the expected result kind: `"num"`, `"bool"`, or a pair of kinds such as `("num", "bool")`. It does not infer types. This is because Church zero and false have the same representation.
- Invalid decoded shapes report `malformed`, but the decoder cannot recognize every invalid untyped encoding. Programs are assumed to use supported operations with the correct types; there is no static type checker.
- Large Church numerals or recursive programs can use substantial time and memory or reach Python's recursion limit during tree operations. Step budgets limit beta-value steps, not elapsed time or memory use.