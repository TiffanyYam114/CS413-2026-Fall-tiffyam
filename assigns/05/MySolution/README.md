Requires Python 3.12 or later.


## Fresh-Name Policy

The deterministic fresh-name policy chooses the smallest positive suffix
available for a binder: `y_1`, `y_2`, and so on. Reserved names include every
variable occurrence and binder in both original inputs, the substitution target,
and all names generated earlier in the call. `AllNamesVisitor` inherits the
nonbinding methods of `FreeVariableVisitor` and overrides each binding method
to retain bound names as well.

## Testing

Run all commands in PowerShell from the assignment directory (`assigns/05`),
which contains `MySolution` and the supplied `lambda1_vp.py`.

Install pytest locally if needed:

```powershell
python -m pip install --target MySolution/.deps pytest
```

Before running pytest, set its location in each new PowerShell session:

```powershell
$env:PYTHONPATH = (Resolve-Path MySolution/.deps).Path
```

### Run each test file individually

**Pretty-Printing**

Unittest:
```powershell
python -B -m unittest -v MySolution.test_pretty_unittest
```

Pytest:
```powershell
python -B -m pytest -p no:cacheprovider MySolution/test_pretty_pytest.py
```

**Substitution**

Unittest:
```powershell
python -B -m unittest -v MySolution.test_substitution_unittest
```

Pytest:
```powershell
python -B -m pytest -p no:cacheprovider MySolution/test_substitution_pytest.py
```

### Run all tests together

Alternatively, collect all four files in a single pytest run:

```powershell
python -B -m pytest -p no:cacheprovider MySolution/test_pretty_unittest.py MySolution/test_substitution_unittest.py MySolution/test_pretty_pytest.py MySolution/test_substitution_pytest.py
```


## Design Explanation

The visitor class lets each visitor choose its result type based on its input type. 
This lets the same visitor class support different operations. PrettyPrintVisitor 
returns a string, while SubstitutionVisitor returns an expression. 

Substitution needs information as it moves through the tree. The visitor stores the 
target variable, the replacement expression, and the replacement's free variable names. 
It also keeps a set of names that cannot be used for new binder names, including names 
from all variable and binder names in the original expression, the target variable, the 
replacement variable, and already generated names. Each new substitution call starts 
with a new set of reserved names, so different substitution calls do not affect each other.

Renaming prevents binders from capturing free variables in the replacement. A body 
stays unchanged if its binder is the target or the the binder is not in the original 
expression. Otherwise, conflicting binders get unused names, and only their own variable 
uses are renamed. Nested binders with the same name are handled separately. A `let` 
binds its name only in its body, so its initializer is processed separately. A `fix` 
binds both its function name and parameter in its body; if they match, renaming keeps 
them equal, so the parameter still takes priority.

Adding an operation means writing another visitor with a method for each constructor. 
The constructors stay unchanged. However, adding a new constructor requires adding a 
new function to each visitor class so that all visitor classes include that constructor. 
This design makes new operations easy to add, while new constructors need changes in several places. 