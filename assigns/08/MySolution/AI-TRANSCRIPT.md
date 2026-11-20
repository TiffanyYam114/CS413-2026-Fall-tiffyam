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

## Prompt 3

### Prompt:
Implement the browser client.

### Output Review and Testing:
I ran the browser and tested the animation. During the animation, some rows of the board became smaller. Clicking "start" would not start the animation; I had to click "next solution" to start it. The board size dropdown would not change the board size until I clicked "start." I asked Codex to fix these in the next prompt.

## Prompt 4

### Prompt:
The squares on the chessboard should not change size during the animation. Changing the board size in the dropdown should change the board automatically. Clicking start should start the first solution.

### Output Review and Testing:
I reviewded the new browser. All requested features were added. However, the screen size would randomly change during the animation, and it was difficult to distinguist try, place, reject, backtrack, and solution events. I asked Codex to fix these in the next prompt.

## Prompt 5:

### Prompt:
The website should stay the same size in width when the animation is played. Also make the try, place, reject, backtrack, and solution events more distinct with colors.

### Output Review and Testing:
The browser now stayed the same size, and the events were distinguishable with colors. 