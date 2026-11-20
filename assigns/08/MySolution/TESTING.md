# Testing and requirement coverage

Run commands from `assigns/08/`. Use Python 3.12+ and Node.js 18+.

```text
python -m unittest discover -s MySolution -p "test_*.py" -v
```

| File / class | Tests | Purpose |
| --- | --- | --- |
| `test_solver.py` / `SolverTests` | 12 | Actual LAMBDA3 safety, CPS search, events, and laziness |
| `test_rpc.py` / `StreamTests` | 9 | Limits, independent positions, cleanup, and atomic reads |
| `test_rpc.py` / `RpcTests` | 7 | JSON-RPC validation, IDs, errors, and notifications |
| `test_rpc.py` / `HttpTests` | 9 | Real HTTP requests, static assets, errors, and all 92 solutions |
| `test_client.py` / `ClientTests` | 1 | Runs 20 checks in `client.test.mjs` |

## All ten required test areas

Names below refer to methods in the files listed above. The final row
also names JavaScript checks from `client.test.mjs`.

| Assignment requirement | Tests | Observed result |
| --- | --- | --- |
| 1. Same row, both diagonals, safe placement | `test_cps_safety_same_row_with_different_columns`; `test_cps_safety_both_diagonals_column_and_safe` | Correct conflict or safe continuation. Also checks repeated columns and an older queen. |
| 2. CPS success, failure, next candidate | `test_solution_resume_is_delayed_and_calls_failure_continuation`; `test_cps_failure_resumes_next_candidate_after_solution` | Success leaves resume delayed; resuming backtracks, tries the next column, and eventually calls exhaustion. |
| 3. All 92 solutions, deterministic order, no duplicates | `test_full_eight_queens_run`; `test_complete_small_traces_match_depth_first_specification` | 92 distinct valid size-8 boards in expected order. Repeated size-4 and size-5 runs match each other and an independent reference. |
| 4. All event kinds, coordinates, snapshots | `test_complete_small_traces_match_depth_first_specification`; `test_full_eight_queens_run`; `test_done_is_last_and_tail_is_empty` | Complete small traces match exact event objects. Size-8 snapshots obey board rules; exactly one final done. |
| 5. Lazy open, one cell, bounded prefix | `test_open_and_bounded_prefix_do_not_run_later_search`; `test_delayed_failure_in_unrequested_tail`; `test_bounded_prefix_leaves_delayed_failure_unexecuted` | No search activity during open for sizes 4–10. One force leaves its tail untouched. Reading 32 events succeeds; forcing event 33 triggers its delayed division by zero. |
| 6. Exhaustion, repeated next, close, unknown ID, cleanup, expiration | `test_exhaustion_releases_closures_and_repeated_next_is_empty`; `test_streams_are_independent_and_close_removes_state`; `test_expiration_refresh_and_cleanup_on_health`; `test_completed_record_expires` | Closures released, later reads empty, closed/unknown IDs rejected, active reads refresh lifetime, inactive and completed IDs expire at 600 seconds. |
| 7. IDs, malformed RPC, methods, parameters, notifications, application errors | `test_health_and_request_ids`; `test_invalid_envelopes_and_batches`; `test_malformed_json`; `test_exact_parameter_shapes`; `test_unknown_method_and_stream_errors_preserve_id`; notification and HTTP tests below | Correct standard codes and preserved IDs. Unknown/expired IDs use -32001. Notifications execute without replies; internal failures expose no details. |
| 8. Limits 1 and 32; never more than requested | `test_open_is_lazy_and_next_respects_one_and_32`; `test_all_limits_and_board_sizes_match_exact_requested_prefixes` | Exact force counts at boundaries. Every limit 1–32 checked for every size 4–10 against the LAMBDA3 trace; exhausted streams return fewer or no events. |
| 9. Full HTTP flow through 92 solutions and done | `test_http_flow_all_92_solutions_and_final_done` | Real open/next/close requests return all 92 valid distinct solutions, bounded batches, final done, and repeated empty completion replies. |
| 10. Browser controls and visible errors | `test_javascript_client` runs checks including `Start automatically animates to the first solution and pauses`, `reset cancels timers, closes the stream, and clears board and counts`, `open leaves search suspended; step consumes exactly one`, `play fetches bounded batches and pause preserves unshown events`, `next solution pauses at each solution; done is separate; restart works`, and `RPC failure stops playback, renders an error, and allows restart` | All 20 JavaScript checks pass. `UI-CHECKLIST.md` provides the allowed manual browser checklist for actual clicks, keyboard use, and layout. |

Same-row safety is tested with different columns and row distance zero, not
substituted with a same-column test. Normal search always starts safety at
distance one, so it cannot itself create a same-row candidate.

## Additional service and client checks

- `test_concurrent_requests_consume_separate_contiguous_batches`: concurrent
  reads consume separate, complete batches without overlap.
- `test_invalid_parameters_do_not_allocate_or_advance`: bad input leaves
  solver state untouched.
- `test_failed_force_removes_partly_advanced_stream` and
  `test_http_internal_error_hides_details_and_invalidates_stream`: a failed
  batch removes its stream and returns only the documented generic error.
- `test_notifications_execute_and_suppress_success_and_errors`,
  `test_open_notification_is_lazy_and_unused_stream_expires`, and
  `test_http_notifications_advance_and_close_without_response_body`: calls
  without IDs execute correctly, force no work at open, and use empty HTTP 204.
- `test_http_expiration_returns_application_error_with_original_id` and
  `test_http_ids_include_null_and_invalid_notifications_receive_errors`:
  expiration preserves IDs, null is a call ID, and malformed notifications
  receive an invalid-request error.
- `test_browser_assets_are_local_and_only_allowed_files_are_served`: the
  page and assets load; source-file and path-traversal requests get 404.
- JavaScript checks cover size changes, stale replies after reset, concurrent
  control clicks, timeouts, network failures, event visuals, and a bounded log.

Successful solver checks run `queens.lam` through the supplied LAMBDA3
interpreter and type checker. The Python reference is only an expected
result, not the implementation under test. JavaScript tests replay a complete
trace produced by LAMBDA3. Injected clocks and failures test error paths
without replacing successful search computation. Laziness checks use observed
interpreter lookups, force counters, and delayed failing computations; they
do not rely on the printed `<lazy>` representation.