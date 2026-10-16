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