# Testing and correctness coverage

This checklist maps all seven testing obligations in Assign06.md to unittest
cases. It also checks the related examples in REQUIREMENTS.md section 7.2.
Test names below are methods in the indicated files.

Run from `assigns/06/`:

```powershell
python -B -m unittest MySolution.test_target_ast MySolution.test_church_encodings MySolution.test_compiler MySolution.test_decoders -v
```

The reviewed suite passes all 52 test methods.

| Assignment obligation | Test coverage |
| --- | --- |
| 1. Independent substitution tests for shadowing and capture avoidance | `test_target_ast.py`: `test_capture_avoidance`, `test_renaming_avoids_bound_names_and_respects_shadowing`, `test_substitution_changes_free_occurrences_only`, and `test_substitution_preserves_replacement_and_avoids_its_bound_names`. Includes substituting x := y in lam y. x, nested binders, smallest available suffixes, and unchanged replacement terms. |
| 2. Left-to-right call-by-value, weak evaluation, zero-step values, determinism, and divergent budget exhaustion | `test_target_ast.py`: `test_exact_left_to_right_beta_contraction_order`, `test_weak_evaluation_and_zero_budget`, `test_no_eta_reduction`, `test_budget_boundary`, `test_every_budget_boundary_in_nested_evaluation`, `test_unused_divergent_argument_and_large_budget`, `test_input_is_unchanged`, and `test_exhaustion_is_deterministic_and_preserves_input`. `test_compiler.py`: `test_left_to_right_order_of_strict_source_constructs` traces compiled application, let, pair, arithmetic, and comparison evaluation. |
| 3. Every source constructor/operator, zero, predecessor of zero, equal/unequal operands, both comparison outcomes, booleans, and truth tables | `test_compiler.py`: `test_required_terminating_demonstrations`, `test_every_operator_and_comparison_outcome`, and `test_free_variables_and_purity_for_every_source_form`. `test_church_encodings.py`: `test_numerals_successor_predecessor_zero_test`, `test_arithmetic_and_all_comparisons`, `test_boolean_truth_tables`, `test_pairs_and_nested_pairs`, and `test_cbv_recursion_factorial`. Every comparison has true and false cases, including equality boundaries. |
| 4. Scope, both fix binders, coincident names, open terms, encoding-name collisions, free variables, and immutability | `test_compiler.py`: `test_shadowing_initializer_scope_and_fix_binders`, `test_each_fix_binder_shadows_outer_bindings_and_respects_inner_bindings`, `test_open_terms_free_names_purity_and_determinism`, and `test_free_variables_and_purity_for_every_source_form`. Explicit free-name sets independently check both source and target analysis. Includes let x = x in x, outer f/x collisions, inner lambdas shadowing each distinct fix binder, and coincident fix binders. |
| 5. Skip unselected divergence; evaluate unused function arguments, let initializers, and either pair component | `test_compiler.py`: `test_divergence_and_strict_constructs` tests both conditional selections, both unselected branches, all short-circuit/selected boolean cases, an unused divergent argument, an unused divergent initializer, and divergence in either discarded pair component. `test_church_encodings.py`: `test_delayed_control_skips_divergence`. Divergent source examples are compiled and run only with a bounded target evaluator. |
| 6. All mandatory demonstrations, nested pairs, and invalid syntax in unused code | `test_decoders.py`: `test_all_examples_with_production_observers` and `DemoTests.test_complete_demo_and_saved_pure_terms` exercise all 14 mandatory demonstrations plus three extras, including nested pairs. `test_compiler.py`: `test_nested_pairs` and `test_rejection_in_dead_code_and_unapplied_bodies` cover negative literals, division, unsupported unary/binary spellings, unused conditional/boolean operands, and unapplied lambda/fix bodies. |
| 7. Only target constructors in output; closed combinators; no evaluation during compilation | `test_compiler.py`: `test_free_variables_and_purity_for_every_source_form` validates every constructor/operator's output. `test_visitor_dispatch_and_no_evaluation_during_compilation` disables evaluator entry points while compiling every demo, validates all output nodes, and compares source snapshots. `test_church_encodings.py`: `test_all_combinators_are_closed_pure_and_deterministic` checks every library combinator. `test_target_ast.py`: `test_target_execution_does_not_load_source_operations`. |

Additional observer tests in `test_decoders.py` cover alpha-renaming, computed
encodings with unevaluated body redexes, malformed outputs, independent
execution/observation budgets, exact budget boundaries, and aggregate nested
pair budgets. They verify that exhaustion never returns a partial decoded
answer and that recursive functions remain lambda values until applied.