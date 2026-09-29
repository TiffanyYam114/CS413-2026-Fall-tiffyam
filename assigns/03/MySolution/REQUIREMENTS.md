# Requirements Specification: A Web-Based Environment for Testing LAMBDA

## 1. Identify Stakeholders and Scope

### Stakeholders

| User | Goal |
| --- | --- |
| Professor | Write, compile, and run LAMBDA programs during lecture; create examples that students can edit without losing the original; choose to only compile or run a program; inspect compiler information, such as abstract syntax trees and generated code; view students' passed and failed test results; be able to stop a running program; view current and previous versions of programs |
| Students | Write, compile, and run LAMBDA programs; open a program from files; save and reopen programs; view the exact line of and understand compiler errors; understand the difference between compiler errors and failures running the program; run tests |
| Compiler Developers | Develop a compiler that works on the web environment |

### Scope

#### In the scope/things that should be in the first version
- Running locally on the user's computer
- Typing or pasting code directly into the text editor
- Saving a program into files
- Opening a program from files
- Creating multiple versions of a program and editing a version without losing the original
- Separate compile and run buttons
- Inspect compiler information
- Compiler errors show the exact line and a description of the error
- Compiler errors and failure running the program show different error messages
- Ability to stop a running program
- Output from running a program shows the version that produced the output
- Creating tests
- Test results show passing and failed tests
- Failed tests do not affect other tests
- Reloading does not wipe progress
- Be able to work with the current version of the compiler
- Simple to use with a keyboard

#### Not in the scope
- A public website
- User accounts and authentication
- Multiple users editing the same program at the same time
- Sharing examples with students - can be implemented in a later version
