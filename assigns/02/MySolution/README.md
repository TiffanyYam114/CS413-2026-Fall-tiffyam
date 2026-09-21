## 1. Extend the AST operations

`t0erm_size`
- `T0Mpair` - The pair constructor is a node, so the size is 1 + the sizes of `arg1` and `arg2`.
- `T0Mpfst` - The projection constructor is a node, so the size is 1 + the size of `arg1`.
- `T0Mpsnd` - The projection constructor is a node, so the size is 1 + the size of `arg1`.

`t0erm_fvset`
- `T0Mpair` - Collect the free variables from both `arg1` and `arg2`.
- `T0Mpfst` - Collect the free variables from only `arg1`.
- `T0Mpsnd` - Collect the free variables from only `arg1`.
