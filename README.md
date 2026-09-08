# CS413-2026-Fall

## AI Reflection

Codex followed the initial prompt well and translated the source code into Python-3 
quite accurately. Some of the ATS functions, like `board_set` `search`, were 
difficult to understand, but the AI seemed to handle them pretty well. It also used 
a different approach than the ATS code to implement the `search` function because 
Python does not optimize tail recursion, which I would not have known.

There were some errors I found in the AI code, such as it not implementing 
`int8 = tuple[int, int, int, int, int, int, int, int]`. You could say this was a 
major error, since the original code uses this type a lot, but Codex's code replaced 
every instance of the `int8` type with `tuple[int, int, int, int, int, int, int, int]`, 
so there was practically no difference. The code was a bit longer, but it still worked. 

Additionally, in the `board_get` function, it translated an if-elif-else statement 
into only if statements, but that would not have affected the functionality. 

Since these errors were minor and did not affect the overall accurateness of the 
program, I believe the AI-generated code could have been trusted without testing. 
However, that's because it was given already written, specific code to translate. 
If we had just told the AI to write Python-3 code to solve the eight-queens problem, 
it may not have been completely correct, or the code may have been unnecessarily long.

Having AI translate the code for me decreased the amount of work I had to do by a lot. 
It would take me a while to understand the ATS code, then translate it into Python. 
I do have to review the AI code, but I am more familiar with Python than ATS. 
Having the AI write Python code for me to review and find errors is a lot easier than 
translating the code myself.
