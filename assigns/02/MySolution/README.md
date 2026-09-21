## 1. Extend the AST operations

`t0erm_size`
- `T0Mpair` - The pair constructor is a node, so the size is 1 + the sizes of `arg1` and `arg2`.
- `T0Mpfst` - The projection constructor is a node, so the size is 1 + the size of `arg1`.
- `T0Mpsnd` - The projection constructor is a node, so the size is 1 + the size of `arg1`.

`t0erm_fvset`
- `T0Mpair` - Collect the free variables from both `arg1` and `arg2`.
- `T0Mpfst` - Collect the free variables from only `arg1`.
- `T0Mpsnd` - Collect the free variables from only `arg1`.

`t0erm_subst0`
- `T0Mpair` - Keep the pair constructor but substitute both `arg1` and `arg2`.
- `T0Mpfst` - Keep the projection constructor but substitute `arg1`.
- `T0Mpsnd` - Keep the projection constructor but substitute `arg1`.

After completing these, I asked Codex to check my answers. Codex confirmed that my answers were correct.

## 2. Extend call-by-value evaluation

`t0erm_cbv_evaluate0`
- `T0Mpair` - Evaluate `t1` and `t2`, then create a new `T0Mpair(t1, t2)`.
- `T0Mpfst` - Evaluate `t1`, then return `t1.arg1`.
- `T0Mpsnd` - Evaluate `t2`, then return `t1.arg2`.

After completing these, I asked Codex to check my answers. Codex confirmed that my answers were correct.

## 3. Test your implementation

I asked Codex to create the test cases listed as well as the three specific assertions. I checked the test 
cases and found the first and second assertions, but the third one was missing. I prompted Codex to add the 
third assertion. 

In the MySolution directory, run tests with `python -m unittest MySolution.TEST.test02_lambda0`.
