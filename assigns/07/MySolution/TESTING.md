# Testing the RPC service

## Run the tests

Use Python 3.12 or later. From the assignment directory (`assigns/07`), run:

```powershell
python -m pip install -r MySolution/requirements-test.txt
python -B -m unittest discover -s MySolution/tests -t . -v
```

You do not need to start the server. The tests use Flask's test client to
send HTTP requests directly to the app. They check both the HTTP response
and its JSON-RPC body.

The tests are in `tests/test_rpc.py`, in the `RpcHttpTests` class. Some tests
try several inputs using subtests. Every subtest must pass.

## Required behavior and test names

| Requirement | Tests | What they check |
| --- | --- | --- |
| 1. Health and IDs | `test_health_and_request_ids` | Status `ok`, version `1.0`, and unchanged string, number, and null IDs. |
| 2. Type-checking | `test_typecheck_formatted_types` | Expected types for integers, booleans, tuples, lists, and functions. |
| 3. Interpretation | `test_interpret_arithmetic`, `test_interpret_factorial`, `test_interpret_tuple`, `test_interpret_collection` | Expected types and formatted values, including factorial 6 = 720. |
| 4. Compilation | `test_compile_both_targets_returns_unchanged_code`, `test_compile_does_not_execute_generated_code` | Both targets return nonempty code, unchanged from LAMBDA3. Compiling `1 / 0` succeeds because the code is not run. |
| 5. Language errors | `test_syntax_errors`, `test_type_errors` | Syntax errors use `-32010`; type errors use `-32011`. All source methods return HTTP 200 and keep the ID. |
| 6. Invalid input | See the input checks below. | Invalid requests and parameters receive the documented error codes. |
| 7. Function values | `test_function_results_hide_closure_internals` | Functions return `<lam>` or `<fix>`, without captured variables or Python objects. |
| 8. Failure and timeout | `test_backend_failure_is_logged_without_leaking_details`, `test_timeout_stops_worker_and_batch_continues` | A backend failure returns `-32603`; a real timeout returns `-32012`. IDs are kept, the worker stops, and other calls still work. |
| 9. Unbound variable | `test_unbound_variable_rejected` | The real type-checker rejects `x + 1` in all source methods. |
| 10. Batches and notifications | See the batch checks below. | Responses keep IDs, omit notifications, and handle invalid members. |

Input checks for requirement 6:

| Test | What it checks |
| --- | --- |
| `test_malformed_json` | Broken JSON, empty bodies, invalid UTF-8, and nonstandard constants return `-32700`. |
| `test_invalid_envelopes` | Wrong request shapes and invalid IDs return `-32600`. |
| `test_invalid_envelope_preserves_usable_id` | A single invalid request keeps its ID when the ID has an allowed type. |
| `test_unknown_method_and_case_sensitive_names` | Unknown names and wrong capitalization return `-32601`. |
| `test_missing_or_nonobject_params` | Missing params or params with the wrong type return `-32602`. |
| `test_invalid_source_parameters` | Missing, blank, and non-string source values return `-32602`. |
| `test_extra_parameters_rejected` | Unexpected parameter fields return `-32602`. |
| `test_invalid_compile_target` | Missing or unsupported targets return `-32602`. |
| `test_oversized_source_rejected_in_bytes` | The source limit counts UTF-8 bytes, including multibyte characters. |
| `test_source_at_size_limit_is_accepted` | Exactly 65,536 bytes is allowed. |

Batch and notification checks for requirement 10:

| Test | What it checks |
| --- | --- |
| `test_batch_matches_ids_and_omits_notifications` | Results match the calls by ID; notifications have no result entry. |
| `test_invalid_batch_members_have_null_ids` | Invalid members receive `-32600` with `id: null`; valid calls still work. |
| `test_batch_method_error_keeps_id` | An unknown method in a valid request keeps its ID. |
| `test_batch_with_one_reply_still_returns_array` | A batch response stays an array when only one call needs a reply. |
| `test_empty_batch_returns_one_error_object` | `[]` receives one Invalid Request object, not an array. |
| `test_single_notification_has_no_body` | A single notification receives HTTP 204 with an empty body. |
| `test_notification_only_batch_has_no_body` | A notification-only batch receives HTTP 204 with an empty body. |
| `test_notifications_suppress_method_and_parameter_errors` | Notifications have no reply even when the method or parameters are invalid. |
| `test_notification_reaches_dispatch_handler` | The server processes a notification even though it sends no reply. |

Additional checks:

| Test | What it checks |
| --- | --- |
| `test_provided_list_library` | The supplied `mylib/list.lam` works inside a complete source expression. |
| `test_wrong_media_type_is_http_transport_error` | Wrong or missing media types use HTTP 415. |
| `test_utf8_content_type_parameter_is_accepted` | `application/json; charset=utf-8` is accepted. |
| `test_wrong_http_method_and_url` | Wrong HTTP methods use 405; unknown URLs use 404. |
| `test_documented_examples_match_schemas` | The JSON examples in `RPC.md` parse, and valid envelopes match the schemas. |

All checked JSON-RPC responses must also pass `response.schema.json`. Both
schema files are checked against JSON Schema Draft 2020-12. Empty HTTP 204
bodies are checked separately because they contain no JSON.

## Real LAMBDA3 calls and failure checks

Successful language tests use the provided parser, type-checker, interpreter,
and compilers. They do not use fake successful results.

Only two tests use mocks. One makes the backend raise an unexpected error
to check logging and the generic error response. The other records a call
to the real health handler to check notification dispatch.

The timeout test runs a real, slow recursive Fibonacci program. It checks
that the worker stops, the next batch member succeeds, and a later
interpretation succeeds. The service deadline is two seconds. The test
allows up to eight seconds for the full HTTP call, including scheduling and
cleanup. A timeout does not prove the program would run forever.

## Architecture

```text
HTTP client or Flask test client
              |
              v
app.py: HTTP and JSON decoding
              |
              v
dispatcher.py: envelopes, methods, IDs, batches, notifications
              |
              v
lambda_service.py: parameter checks and LAMBDA3 calls
              |
              +--> type-check / compile --> LAMBDA3/lambda3.py
              |
              +--> worker process -------> LAMBDA3/lambda3.py
                   interpretation
                   two-second deadline
```

`rpc_errors.py` provides shared error objects. The interpretation worker
writes a formatted result to a temporary file. The parent reads it after
the worker finishes, and the temporary file is removed.

## Observed results

All 38 tests passed with no failures or errors. This includes the real
timeout and worker cleanup, both compilers, the provided list library,
and the documented schema examples. Other Python versions were not tested.

```text
Ran 38 tests in 7.400s

OK
```

Test dependencies were installed in a temporary directory for verification.
Installed packages and test environments are not included in the submission.

The six PowerShell curl examples in `README.md` were also run against a
local server. Health, type-checking, factorial, both compile targets, and
the unbound-variable error all returned the expected results.
