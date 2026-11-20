AI used: Codex

## Prompt 1

### Prompt:
Implement the solver.

### Output Review and Testing:
Codex included `test_solver.py`, which tests the solver. Tests include safe placement of queens, exactly 92 solutions and one done, and board sizes 4-10. Running the file with `python -m unittest discover -s MySolution -p test_solver.py -v` passes all tests. 

## Prompt 2

### Prompt:
Implement the RDC adapter.

### Output Review and Testing:
Codex included `test_rpc.py`, which tests the RDC adapter. Tests include stream management, JSON-RPC, and HTTP requests. Running the file with `python -m unittest discover -s MySolution -p test_rpc.py -v` passes all tests.
