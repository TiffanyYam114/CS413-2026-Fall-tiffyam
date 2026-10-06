AI used: Codex

## Prompt 1

### Prompt:
Implement input logic: F1-F3.

### AI Output & Testing:
Codex added the Load source menu. I tested all four options of input and verified that the source name and revision number was correct. I tested invalid input by selecting manual input and applying changes with no input as well as only spaces, which did not go through. After applying changes on invalid input, the input was still in the text input area. I selected the factorial example and edited it, then applied changes. When I selected factorial again, my changes did not update the example. The actions buttons also went gray and uninteractable while changes had not been applied or discarded yet. 

## Prompt 2

### Prompt:
Implement button logic: F4-F7.

### AI Output & Testing:
Codex added functionality for all buttons. The buttons are uninteractable while changes have not been applied or discarded. I chose the factorial example and clicked the Lint button, and it said there were no undeclared variables. Then I changed one of the `n` variables to `x`, applied changes, and clicked the Lint button again, and it said `x` was an undeclared variable. I ran both factorial and fibonacci with the Interpret button and got the expected outputs, 120 and 55. Then I deleted a random thing to see if it would give me an input error, which it did. Both Type Check and Compile state that they have not been implemented yet. The Execute button is always uninteractable.

## Prompt 3

### Prompt:
Implement F8-F10.

### AI Output & Testing:
Selecting factorial or fibonacci increases the revision number by one. Adding input and applying changes also increases by one. Adding input but discarding changes does not change revision number. Having the same source and testing out many buttons creates multiple stacked outputs. Output shows the selected action, revision number, and outcome. Applying changes or choosing a different source type clears all outputs. Clicking on a button shows a "busy" message and makes all buttons uninteractable. Upon completion, restores button availability. Reloading preserves the source code, revision, and outputs.
