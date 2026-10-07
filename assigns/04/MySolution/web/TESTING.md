## Automated Tests

To run automated tests in MySolution/web directory, run 
`.\.venv\Scripts\python.exe manage.py test workbench.tests.<file name>`

| File | What it Tests |
| --- | --- |
| `workbench/tests1.py` | Manual input, original source replacement prevention, apply/discard edits, block actions while edits have not been applied, invalid input, file size limit. |
| `workbench/test_tools.py` | Free variables for every constructor, Lint does not run the program, evaluate arithmetic, factorial, and fibonacci, including base cases, input and runtime errors, type check and compile are not implemented, execute is unavailable. |
| `workbench/test_lifecycle.py` | Source change creates revision and clears outputs, rejected changes preserve revision and output, preserve source when backend failure, retry after failure. |
| `workbench/test_boundaries.py` | Tests model functionality without browser or web server, controller functionality without backend. |


## Browser Tests

To run browser tests in MySolution/web directory, run
`.\.venv\Scripts\python.exe -m workbench.tests.browser_smoke --channel chrome`

| Browser Check | What it Checks |
| --- | --- |
| B1 | Initial typing, button order, arithmetic result. |
| B2 | Manual input, apply/discard edits, Lint. |
| B3 | Factorial/fibonacci, new revisions, cleared results. |
| B4 | File upload, original file preservation, rejected edits. |
| B5 | Invalid input, source preservation, discard recovery. |
| B6 | Input/runtime errors, type check and compile placeholders, unavailable Execute. |
| B7 | Literal HTML-like text, line breaks, result details. |
| B8 | Busy status, blocked controls, timeout recovery. |
| B9 | Backend failure, source preservation, retry after failure. |
| B10 | Lost response recovery, no duplicate action. |
| B11 | Reloaded state, keyboard controls, JavaScript errors. |


## Requirement Traceability

| Requirement | Automated Tests | Browser Tests |
| --- | --- | --- |
| F1 | `tests.py`: manual input/uploads; `test_lifecycle.py`: factorial/fibonacci examples. | B2, B3, B4 |
| F2 | `tests.py`: apply/discard, edit guards, original file preservation. | B1, B2, B4 |
| F3 | `tests.py`: blank input, UTF-8, size limit, source preservation. | B4, B5 |
| F4 | `test_tools.py`: button order, unavailable Execute. | B1, B2, B6 |
| F5 | `test_tools.py`: undeclared names, no evaluation; `test_boundaries.py`: binding scope. | B2, B6, B7 |
| F6 | `test_tools.py`: arithmetic, factorial/fibonacci, input/runtime errors. | B1, B3, B6, B9 |
| F7 | `test_tools.py`: not-implemented results, no output, blocked Execute. | B6 |
| F8 | `test_lifecycle.py`: new revisions, cleared output. | B2, B3, B4, B5 |
| F9 | `tests.py`: literal source; `test_tools.py`: result details; `test_lifecycle.py`: literal output. | B7, B11 |
| F10 | `test_tools.py`, `test_lifecycle.py`: failures/timeouts, retry after failure. | B8, B9, B10 |