# Django LAMBDA web interface

Use Python 3.12 or later and Django 6.0.9. 

From the assignment folder in PowerShell:
To run the assignment, navigate to `MySolution/web` in a terminal and run the following:

```
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8001
```

Open **http://127.0.0.1:8001/** in a browser to view the server. Press Ctrl+C 
in the terminal to stop the server.



The source menu supports UTF-8 uploads, a blank manual editor, and editable
factorial and fibonacci examples. You can also type directly into the initial
editor. **Apply changes** accepts the draft as the new source and creates a new 
revision. **Discard changes** does not create a new revision and reverts the 
source to the most recently applied source. Editing an uploaded copy does not 
change the original file. While changes are unapplied, action buttons are 
disabled. Applying or discarding changes enables the buttons again. 

## Demonstration

Loading the Factorial and Fibonacci examples and clicking Interpret outputs 
`D0Vint(arg1=120)` and `D0Vint(arg1=55)`. Select manual input and enter 
`D0Evar("x")`, then click Lint. There is an undeclared variable `x`. Change 
the input to `D0Eint(10)`, apply changes, and click Lint again. Now no free 
variables were found. 

To show the difference between an input and runtime error, first enter `D0Eint()`. 
It expects an integer, but there is nothing inside the parentheses, so Lint will 
return an input error: `Missing D0Eint argument`. Now enter 
`D0Eop2("/", D0Eint(1), D0Eint(0))`, which is division by 0. There are no free 
variables, so Lint passes, while Interpret returns a runtime error: `ZeroDivisionError`. 

Click Type-check and Compile, which will both say they have not been implemented 
yet. The Execute button is always disabled because it is reserved for executing 
code produced by a compiler. The Compile button is not implemented yet, so we cannot 
execute.

## Reflection

MVC helped keep the application organized by giving each part a clear job.
The model stores the applied source, draft, revision, and results. It also
decides whether an edit or action is allowed. The view is handled by Django 
and shows the source code, buttons, revision, and output. The controller 
handles requests and connects the model to the language tools. The separation 
makes it so that the model can be tested without a browser or web server, and 
the controller can substitute a test backend.

Managing revisions was the most difficult part of the separation. The model needed 
to keep unapplied source separate from the applied source. Invalid edits had to be 
preserved without losing the previous source, revision, or results. The view also 
needed to disable action buttons until the user applied or discarded those edits.

The architecture makes it easier to change the page layout later. Right now, my 
layout does not have much styling, but if I decide to add styling later, the editor, 
buttons, and results could be rearranged without changing how source is stored or 
how programs are checked and evaluated. This makes UI updates easier to manage.