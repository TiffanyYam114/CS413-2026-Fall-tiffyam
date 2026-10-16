### AI used: Codex

## Prompt 1

### Prompt: 
Implement the pretty privilege visitor.

### Output Review and Test:
I checked that all LAMBDA constructors were included in PrettyPrintVisitor and that every function used the correct argument names for each type. I compared the required output format to the formatted strings and made sure they were the same in parentheses, spaces, periods, etc.

## Prompt 2

### Prompt:
Implement the substitution visitor. Use the fresh name policy where the new variable name is the old one with the smallest possible subscript. Document the fresh name policy in README.md.

### Output Review and Test:
I checked that all LAMBDA constructors were included in SubstitutionVisitor and that all binding rules were followed. I checked to see if the solution used the fresh name policy I gave it. I also read the fresh name policy it documented in README.md to see if it was correct.

## Prompt 3

### Prompt:
Implement the tests. Make sure all specific examples given in task 1 and 2 are included.

## Output Review and Test:
I checked if both the pretty print and substitution test cases included all LAMBDA constructors, which they do in pretty_cases.py and substitution_cases.py. It also added the specific examples in the assignment to assignment_examples.py. Both pytest and unittest test on their corresponding cases.py and assignment_examples.py. All tests passed.
