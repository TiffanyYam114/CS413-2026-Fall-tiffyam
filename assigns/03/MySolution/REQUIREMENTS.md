# Requirements Specification: A Web-Based Environment for Testing LAMBDA

## 1. Identify Stakeholders and Scope

### Stakeholders

| User | Goal |
| --- | --- |
| Professor | Write, compile, and run LAMBDA programs during lecture; create examples that students can edit without losing the original; choose to only compile or run a program; inspect compiler information, such as abstract syntax trees and generated code; view students' passed and failed test results; be able to stop a running program; view current and previous versions of programs |
| Students | Write, compile, and run LAMBDA programs; open a program from files; save and reopen programs; view the exact line of and understand compiler errors; understand the difference between compiler errors and runtime errors; run tests |
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
- Compiler errors and runtime errors show different error messages
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

## 2. Identify Questions and Assumptions

| # | Stakeholder Question | Why the answer matters | Stakeholder Answer |
| --- | --- | --- | --- |
| 1 | How should students preserve the original example while creating their edited version? | I can think of several ways this would work: 1. Students can edit an example but still revert the program back to its original version. But this would make the edited version unavailable, and students probably still want to keep the edited version. 2. Be able to add another text editor on the page. One of them has the original example, the other has the student's edited version. Now students have access to both versions at the same time. 3. Download the example, create a copy, and edit the copy. Then students can have both the original and edited version but only one open at a time. | No stakeholder answer. I would choose option 3, as it is the most logical option and is a feature that most existing text editors have. |
| 2 | How should the environment help the student find the place of the compiler error? | "When the compiler reports where the problem occurred, the environment should help the student find that place in the source." When the compiler shows the line of the error, the student can just go to that line in the file. Would the LAMBDA editor also provide a direct link to the error line? | No stakeholder answer. Since the direct link to the error line is a feature in many existing text editors, I assume that we should also add a direct link. |
| 3 | How should compiler errors and runtime errors be formatted? | The requirements state compiler errors and runtime errors should not look like the same thing but does not specify what they should look like. Since we want the users to understand the errors they get, we should specify what they look like. | No stakeholder answer. Question remains unresolved. |
| 4 | What browser(s) should the environment be able to run on? | The requirements state it should work in a browser students normally use but does not specify which browsers. We want to determine which browsers to include so that later on, students don't have a problem with being unable to access the environment. | No stakeholder answer. I assume we want to have the environment accessible to the most popular browsers, like Chrome, Safari, Edge, and Firefox. |
| 5 | How much color do we want to add? | The requirements state, "messages should make sense without depending only on colors." Does this mean we don't want colors at all? I believe colors are a useful tool for determining whether a piece of code is a variable, function, comment, etc, so I would like to know how much colors to add. | No stakeholder answer. Question remains unresolved. |
