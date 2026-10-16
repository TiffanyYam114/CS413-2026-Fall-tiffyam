## Fresh-Name Policy

The deterministic fresh-name policy chooses the smallest positive suffix
available for a binder: `y_1`, `y_2`, and so on. Reserved names include every
variable occurrence and binder in both original inputs, the substitution target,
and all names generated earlier in the call. `AllNamesVisitor` inherits the
nonbinding methods of `FreeVariableVisitor` and overrides each binding method
to retain bound names as well.