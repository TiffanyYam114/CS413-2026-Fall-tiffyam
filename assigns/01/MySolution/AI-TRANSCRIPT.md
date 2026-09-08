AI used: Codex


## Initial Prompt:

Read OriginalSourceProgram.md, which contains code to solve the Eight-Queens 
problem. Translate the code in this file to Python-3 and write the new code 
in AI-translation.py. Preserve the behavior of the original program as much as possible.

## AI Response:

Codex wrote code to AI-translation.py. When translating the `search` function, 
Codex said Python does not optimize tail recursion, so it did not use tail 
recursion like the ATS code when writing a new `search` function.

## Follow-Up Prompt:

Codex did not implement the type `int8`, so it was passing a long argument 
`bd: tuple[int, int, int, int, int, int, int, int]` to several functions. 
I asked Codex to make a `int8` type and pass it to those functions.

In AI-translation.py, instead of passing in `bd: tuple[int, int, int, int, int, int, int, int]` 
to several functions, create a type `int8` for a tuple of 8 integers. Then pass `int8` into the functions.

## AI Response: 

Codex implemented `int8` and passed it as an argument in the necessary functions.
