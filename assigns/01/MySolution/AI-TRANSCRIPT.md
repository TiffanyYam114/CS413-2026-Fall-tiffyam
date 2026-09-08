AI used: Codex


### Initial Prompt:

Read OriginalSourceProgram.md, which contains code to solve the Eight-Queens 
problem. Translate the code in this file to Python-3 and write the new code 
in AI-translation.py. Preserve the behavior of the original program as much as possible.

### AI Response:

Codex wrote code to AI-translation.py. When translating the `search` function, 
Codex said Python does not optimize tail recursion, so it did not use tail 
recursion like the ATS code when writing a new `search` function.

### Follow-Up Prompt:

Codex did not implement the type `int8`, so it was passing a long argument 
`bd: tuple[int, int, int, int, int, int, int, int]` to several functions. 
I asked Codex to make a `int8` type and pass it to those functions.

In AI-translation.py, instead of passing in `bd: tuple[int, int, int, int, int, int, int, int]` 
to several functions, create a type `int8` for a tuple of 8 integers. Then pass `int8` into the functions.

### AI Response: 

Codex implemented `int8` and passed it as an argument in the necessary functions.

### Manual Changes:

The ATS code for the function `board_get` contains else if statements, but the 
Codex translation is a bunch of if statements. I manually changed the function 
to have else if statements. 

### Generate Test Cases Prompt:

Generate code to test the top-level functions in AI-translation.py. Put the test cases in tests.py.

### AI Response:

Codex generated a couple of test cases for each function in tests.py. All tests pass.

### Follow-Up Prompt:

Add some more boundary or unusual test cases to tests.py.

### AI Response: 

Codex added more test cases to `print_row`, `board_set`, `safety_test1`, `safety_test2`. 
All tests pass. 

For some reason, Codex added another test for `search` that starts with `nsol` at 5, and 
it tests if `nsol` at the end of the function is 97. I thought that was unnecessary 
because 92 + 5 = 97, and you don't need to make another test case to confirm that.

### Add my own test cases

Added my own test cases to the bottom of tests.py. All tests pass.
