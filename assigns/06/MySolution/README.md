## Recording link
https://drive.google.com/file/d/1CFYz8WWIZd4iwg9nX-Td84Pnb3coyvqp/view?usp=sharing




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

## Presentation files

- PDF slides: `MySolution/presentation/Project_Slides.pdf` (19 slides).
- Editable PowerPoint: `MySolution/presentation/Project_Slides.pptx`.
- Speaker script: `MySolution/presentation/Presenter_Script.md`, with slide
  timings and live commands for a roughly 17 minute 45 second presentation.
- Budget experiment results: `MySolution/presentation/Budget_Demo_Transcript.txt`.
- Recording: not created. Record the presentation with readable slides,
  audible narration, and your face visible; add the video file or accessible
  recording link here before submission.

Run a focused example with different budgets from `assigns/06/`:

```powershell
python -B -m MySolution.budget_demo
python -B -m MySolution.budget_demo --execution-budget 100
python -B -m MySolution.budget_demo --observation-budget 100
python -B -m MySolution.budget_demo --execution-budget 353 --observation-budget 333
python -B -m MySolution.budget_demo --example loop --execution-budget 20
```

To run all budget comparisons, optionally pausing between them:

```powershell
./MySolution/presentation/Budget_Demo_Commands.ps1 -PauseBetween
```

The focused budget demo reports exhaustion as an intended demonstration
outcome and returns exit code 0. The full `MySolution.demo` still returns
nonzero if an example fails its expected check. Current factorial(4) requires
353 execution steps and 333 observation steps; exact counts depend on the
implementation. Increasing a budget never changes the intended answer.

Rebuild the slides and measured result tables with no extra Python packages:

```powershell
python -B -m MySolution.build_presentation
```

Run the full test suite including the three focused budget-demo tests:

```powershell
python -B -m unittest MySolution.test_target_ast MySolution.test_church_encodings MySolution.test_compiler MySolution.test_decoders MySolution.test_budget_demo
```

## Module overview

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

