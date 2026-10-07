## Automated Tests

| File | What it Tests |
| --- | --- |
| `workbench/tests1.py` | Manual input, original source replacement prevention, apply/discard edits, block actions while edits have not been applied, invalid input, file size limit. |
| `workbench/test_tools.py` | Free variables for every constructor, Lint does not run the program, evaluate arithmetic, factorial, and fibonacci, including base cases, input and runtime errors, type check and compile are not implemented, execute is unavailable. |
| `workbench/test_lifecycle.py` | Source change creates revision and clears outputs, rejected changes preserve revision and output, preserve source when backend failure, retry after failure. |
| `workbench/test_boundaries.py` | Tests model functionality without browser or web server, controller functionality without backend. |

## Browser Tests

| File | What it Tests |
| --- | --- |
| `browser_smoke.py` | Manual input, file upload, factorial, and fibonacci from the source menu. Apply/discard edits, preserve original file, reject blank, invalid, or oversized input. Link and Interpret results, Type Check and Compile not implemented, Execute unavailable. Preserve source after backend failure, retry after failure. Restore source and results after reloading. |