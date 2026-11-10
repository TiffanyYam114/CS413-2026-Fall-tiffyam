# LAMBDA3 RPC contract

This document defines version 1.0 of the service before the dispatcher is
implemented. A client sends a method name and inputs. The server calls the
provided LAMBDA3 tools and returns a result or an error.

## HTTP endpoint

Send every operation to `POST /rpc`. For local development, the planned URL
is `http://127.0.0.1:8000/rpc`.

Use `Content-Type: application/json`. An optional `charset=utf-8` parameter
is accepted. Encode request bodies as UTF-8. Responses with JSON bodies also
use `Content-Type: application/json`.

| HTTP status | Meaning |
| --- | --- |
| `200` | The body contains a JSON-RPC response object or response array. An RPC error also uses this status. |
| `204` | The request contains only valid notifications. The body is empty. |
| `415` | The request has a missing or unsupported Content-Type. No RPC method runs. |
| `405` | The client used an HTTP method other than POST on `/rpc`. |
| `404` | The requested URL does not exist. |

Transport errors (`415`, `405`, and `404`) do not have JSON-RPC response
bodies; their bodies are outside this contract. An empty or malformed JSON
body sent with the correct media type receives HTTP `200` with error
`-32700`. Valid JSON with the wrong request structure receives HTTP `200`
with error `-32600`.

HTTP status describes the HTTP exchange. The JSON-RPC `result` or `error`
describes whether the requested operation succeeded. Clients must check both.

## Requests, responses, and IDs

A request object is called an envelope because it wraps the operation's
name and inputs:

```json
{
  "jsonrpc": "2.0",
  "method": "lambda.interpret",
  "params": {"source": "40 + 2"},
  "id": 1
}
```

- `jsonrpc` must be the string `"2.0"`.
- `method` must be a string. Names are case-sensitive.
- `params` must be an object and is required for all four methods, including
  health. Arrays of positional arguments are not supported.
- `id`, when present, must be a string, number, or `null`. Boolean, object,
  and array IDs are invalid. JSON does not allow NaN or infinity.
- Extra fields on the envelope are ignored. Extra fields inside `params`
  are rejected.

A successful response contains `jsonrpc`, the unchanged `id`, and `result`.
A failed response contains `jsonrpc`, `id`, and `error`. A response never
contains both `result` and `error`.

An omitted ID makes a structurally valid request a **notification**. The
server processes it but sends no response, even if the method is unknown,
parameters are invalid, or the operation fails. A single notification
receives HTTP `204` and an empty body. An explicit `"id": null` is a call
and receives a response with `"id": null`.

A malformed envelope without an ID is not a notification: it receives an
Invalid Request response. For single invalid requests, keep the supplied ID
if it has an allowed type; otherwise use `null`. Invalid batch members always
receive `id: null`. JSON parse errors and empty batches also use `id: null`.
Use distinct IDs for outstanding calls, and match responses by ID rather
than by their order in an array.

## Methods

| Method | Required params | Successful result | Behavior |
| --- | --- | --- | --- |
| `service.health` | `{}` | `{"status":"ok","version":"1.0"}` | Reports service status and API version; does not run LAMBDA3. |
| `lambda.typecheck` | `{"source":"..."}` | `{"type":"sint"}` | Parses and type-checks source, then formats its type. |
| `lambda.interpret` | `{"source":"..."}` | `{"type":"sint","value":"42"}` | Parses, type-checks, evaluates, and formats the result within the deadline. |
| `lambda.compile` | `{"source":"...","target":"python"}` or `{"source":"...","target":"javascript"}` | `{"target":"python","code":"..."}` or the JavaScript equivalent | Parses and type-checks, then returns generated source for the selected target. |

The types and values in this table are examples; they depend on the program.
`source` is text in LAMBDA3 syntax, not Python constructor expressions.
It must be a string with at least one non-whitespace character. Do not trim
or otherwise change accepted source before passing it to LAMBDA3.
`target` is required for compilation and must be exactly `"python"` or
`"javascript"`; there is no default target.

Every source method uses `d0exp_parse_and_typecheck(source)`. Returned types
use `format_type`. Interpretation uses `d0exp_evaluate` and `d0val_format`;
`value` is always a string. Functions appear as `<lam>` or `<fix>`, without
their Python closures or captured environments.

Compilation uses `d0exp_compile` or `d0exp_compile_js`. Return the complete
generated code unchanged as a string, including newlines. JSON escaping
does not change the decoded string. The service never runs generated code.
The provided `LAMBDA3/mylib/` modules remain available for demonstrations
and tests. There is no account system, storage, public deployment, or stream
delivery across calls in this contract.

## Limits

- **Maximum source size: 65,536 bytes (64 KiB), encoded as UTF-8.** Check
  the decoded `source` string's UTF-8 byte length, not the JSON body's size.
  Exactly 65,536 bytes is allowed. A larger source gets `-32602`, with
  `data.parameter: "source"`, `data.limit: 65536`, and `data.unit: "bytes"`.
  This limit applies separately to every source in a batch.
- **Interpretation deadline: 2 seconds per call.** Start the clock when
  starting the interpretation worker. Include worker startup, parsing,
  type-checking, evaluation, and value formatting. If the worker has not
  finished, terminate it and return `-32012`. Use a separate process that
  can be stopped; a thread or a wait timeout alone cannot stop evaluation.
  One timed-out batch member must not stop the other members.

A timeout means the operation exceeded the deadline. It does not prove
that the program would run forever. The interpretation deadline does not
apply to the standalone type-check and compile methods. A runtime exception
that occurs before the deadline is an internal error, not a timeout.

## Validation and errors

Check requests in this order so errors are predictable:

1. Check the HTTP endpoint, HTTP method, and Content-Type.
2. Decode JSON. Invalid JSON gets `-32700`.
3. Check the top-level request or batch and each envelope. An envelope must
   be an object with `jsonrpc: "2.0"`, a string `method`, and an allowed ID
   if present. An invalid envelope gets `-32600`.
4. Look up the method. An unknown name gets `-32601`.
5. Check params for the known method. Missing params, non-object params,
   missing or extra fields, wrong field types, blank or oversized source,
   and unsupported targets get `-32602`.
6. Run LAMBDA3. Map syntax, type, timeout, and unexpected errors as below.

For notifications that pass step 3, suppress any response from steps 4-6.

An error object has an integer `code`, a string `message`, and optional
structured `data`. When data is included, use the category below. Optional
`detail` gives a safe explanation; `parameter` identifies an invalid field.
Syntax errors may include one-based `line` and `column`. Limits use `limit`
and `unit`.

| Code | Message | `data.category` | When it happens / useful data |
| --- | --- | --- | --- |
| `-32700` | `Parse error` | `json_parse` | The HTTP body is not valid JSON. Use a short safe detail. |
| `-32600` | `Invalid Request` | `request` | Invalid envelope, invalid batch member, or empty batch. Detail identifies the broken rule. |
| `-32601` | `Method not found` | `method` | Unknown method name. |
| `-32602` | `Invalid params` | `params` | Invalid inputs. Include a parameter name and safe detail; include the size limit when relevant. |
| `-32603` | `Internal error` | `internal` | Unexpected backend or runtime failure. Return a generic message and no exception details. |
| `-32010` | `LAMBDA syntax error` | `syntax` | `LambdaSyntaxError`. Include a safe parser diagnostic and available line/column. |
| `-32011` | `LAMBDA type error` | `typecheck` | `TypeCheckError`, including unbound variables. Include a safe type-checker diagnostic. |
| `-32012` | `Execution timeout` | `timeout` | Interpretation worker exceeds its deadline. Include `limit: 2` and `unit: "seconds"`. |

A LAMBDA syntax error is different from malformed JSON. The JSON containing
the source may be valid even though the LAMBDA program is not.

Never return tracebacks, filesystem paths, Python object representations,
or captured environments. Use the syntax exception's diagnostic message
and source position without its filename. Sanitize diagnostics before
returning them. Log unexpected failures on the server, and return only the
generic internal error to the client.

## Batches

A batch is a nonempty JSON array. Process each member independently.
Return HTTP `200` and an array containing one response per call and one
Invalid Request error per invalid member. Omit notifications. Even when
only one response remains, return an array. Response order is not guaranteed.

A batch containing only notifications gets HTTP `204` and an empty body,
not an empty JSON array. An empty batch (`[]`) gets HTTP `200` and one
Invalid Request **object**, not an array. A nested array is an invalid
batch member; do not treat it as another batch.

## Complete examples

Each request below is a JSON body sent to `POST /rpc` with
`Content-Type: application/json`. Unless stated otherwise, each response
uses HTTP `200` and `Content-Type: application/json`.

### Health

Request:

```json
{"jsonrpc":"2.0","method":"service.health","params":{},"id":"health-1"}
```

Response:

```json
{"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"health-1"}
```

### Type-checking

Request:

```json
{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"40 + 2"},"id":2}
```

Response:

```json
{"jsonrpc":"2.0","result":{"type":"sint"},"id":2}
```

### Interpretation: factorial

Request:

```json
{
  "jsonrpc": "2.0",
  "method": "lambda.interpret",
  "params": {
    "source": "let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"
  },
  "id": "fact-6"
}
```

Response:

```json
{"jsonrpc":"2.0","result":{"type":"sint","value":"720"},"id":"fact-6"}
```

### Compilation

Request:

```json
{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"40 + 2","target":"python"},"id":"compile-1"}
```

The full response follows. Its long `code` string includes LAMBDA3's runtime
helpers. It is generated by the provided compiler, with nothing omitted.

<details>
<summary>Full Python compilation response</summary>

```json
{
  "jsonrpc": "2.0",
  "result": {
    "target": "python",
    "code": "# The emitted program uses Python values for integers, booleans, lists and\n# tuples. Options need a tagged pair so optn_cons(None) remains distinct from\n# optn_nil (None); the private sentinel is created once per generated program.\ndef _lambda_list_cons(head, tail):\n    if not isinstance(tail, list):\n        raise TypeError(\"list_cons: list tail expected\")\n    return [head] + tail\n\ndef _lambda_list_nilq(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_nilq: list expected\")\n    return len(value) == 0\n\ndef _lambda_list_head(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_head: list expected\")\n    if not value:\n        raise ValueError(\"list_head: nonempty list expected\")\n    return value[0]\n\ndef _lambda_list_tail(value):\n    if not isinstance(value, list):\n        raise TypeError(\"list_tail: list expected\")\n    if not value:\n        raise ValueError(\"list_tail: nonempty list expected\")\n    return value[1:]\n\ndef _lambda_a1sz_index(array, index):\n    if not isinstance(array, list) or not isinstance(index, int) or isinstance(index, bool):\n        raise TypeError(\"A1sz indexing expects an array and sint index\")\n    if not 0 <= index < len(array): raise IndexError(\"A1sz index out of range\")\n    return index\ndef _lambda_a1sz_getat(array, index): return array[_lambda_a1sz_index(array, index)]\ndef _lambda_a1sz_setat(array, index, value):\n    array[_lambda_a1sz_index(array, index)] = value\n    return ()\ndef _lambda_a1sz_make_ncpy(size, value):\n    if not isinstance(size, int) or isinstance(size, bool): raise TypeError(\"A1sz size must be sint\")\n    if size < 0: raise ValueError(\"A1sz size must be nonnegative\")\n    return [value for _ in range(size)]\ndef _lambda_a1sz_make_nfun(size, fn):\n    if not isinstance(size, int) or isinstance(size, bool): raise TypeError(\"A1sz size must be sint\")\n    if size < 0: raise ValueError(\"A1sz size must be nonnegative\")\n    return [fn(i) for i in range(size)]\n\ndef _lambda_optn_cons(value):\n    return (_lambda_some_tag, value)\n\ndef _lambda_optn_nilq(value):\n    return value is None\n\ndef _lambda_optn_get(value):\n    if value is None or not (isinstance(value, tuple) and len(value) == 2 and value[0] is _lambda_some_tag):\n        raise ValueError(\"optn_get: nonempty option expected\")\n    return value[1]\n\nclass _LambdaLazy:\n    def __init__(self, thunk):\n        self.thunk, self.evaluated, self.value = thunk, False, None\n\ndef _lambda_lazy_make(thunk):\n    if not callable(thunk): raise TypeError(\"lazy_make: thunk function expected\")\n    return _LambdaLazy(thunk)\ndef _lambda_lazy_eval(value):\n    if not isinstance(value, _LambdaLazy): raise TypeError(\"lazy_eval: Lazy value expected\")\n    if not value.evaluated:\n        value.value = value.thunk(())\n        value.evaluated = True\n    return value.value\ndef _lambda_stcn_nil(): return {\"cons\": False}\ndef _lambda_stcn_cons(head, tail):\n    if not isinstance(tail, _LambdaLazy): raise TypeError(\"stcn_cons: lazy stream tail expected\")\n    return {\"cons\": True, \"head\": head, \"tail\": tail}\ndef _lambda_stcn_check(value, name):\n    if not isinstance(value, dict) or \"cons\" not in value: raise TypeError(name + \": Stcn value expected\")\ndef _lambda_stcn_nilq(value):\n    _lambda_stcn_check(value, \"stcn_nilq\")\n    return not value[\"cons\"]\ndef _lambda_stcn_consq(value):\n    _lambda_stcn_check(value, \"stcn_consq\")\n    return value[\"cons\"]\ndef _lambda_stcn_head(value):\n    _lambda_stcn_check(value, \"stcn_head\")\n    if not value[\"cons\"]: raise ValueError(\"stcn_head: nonempty stream constructor expected\")\n    return value[\"head\"]\ndef _lambda_stcn_tail(value):\n    _lambda_stcn_check(value, \"stcn_tail\")\n    if not value[\"cons\"]: raise ValueError(\"stcn_tail: nonempty stream constructor expected\")\n    return value[\"tail\"]\n\ndef _lambda_format(value):\n    if isinstance(value, _LambdaLazy): return \"<lazy>\"\n    if isinstance(value, dict) and \"cons\" in value:\n        if not value[\"cons\"]: return \"stcn_nil()\"\n        return \"stcn_cons(\" + _lambda_format(value[\"head\"]) + \", <lazy>)\"\n    if value is None:\n        return \"optn_nil()\"\n    if isinstance(value, tuple) and len(value) == 2 and value[0] is _lambda_some_tag:\n        return \"optn_cons(\" + _lambda_format(value[1]) + \")\"\n    if isinstance(value, bool):\n        return \"true\" if value else \"false\"\n    if isinstance(value, list):\n        return \"[\" + \", \".join(_lambda_format(item) for item in value) + \"]\"\n    if isinstance(value, tuple):\n        body = \", \".join(_lambda_format(item) for item in value)\n        return \"(\" + body + (\",\" if len(value) == 1 else \"\") + \")\"\n    if callable(value):\n        return \"<lam>\"\n    return str(value)\n\ndef _lambda_print(value):\n    print(_lambda_format(value))\n    return ()\n\n_lambda_some_tag = object()\n\ndef _lambda_main():\n    _v1 = 40\n    _v2 = 2\n    _v3 = (_v1 + _v2)\n    return _v3\n\n_lambda_result = _lambda_main()\n"
  },
  "id": "compile-1"
}
```

</details>

For JavaScript, send the same request with `"target":"javascript"`.
The result's `target` is then `"javascript"`, and `code` contains the
unchanged output of `d0exp_compile_js`.

### LAMBDA syntax error

Request:

```json
{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"1 +"},"id":"syntax-1"}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32010,
    "message": "LAMBDA syntax error",
    "data": {
      "category": "syntax",
      "detail": "Expected an expression",
      "line": 1,
      "column": 4
    }
  },
  "id": "syntax-1"
}
```

### Type error: unbound variable

Request:

```json
{"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"x + 1"},"id":"type-1"}
```

Response:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32011,
    "message": "LAMBDA type error",
    "data": {"category":"typecheck","detail":"unbound variable 'x'"}
  },
  "id": "type-1"
}
```

### Batch with calls, a notification, and an invalid member

Request:

```json
[
  {"jsonrpc":"2.0","method":"service.health","params":{},"id":"batch-health"},
  {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"40 + 2"}},
  {"jsonrpc":"2.0","method":"lambda.interpret","params":{"source":"40 + 2"},"id":9},
  17
]
```

Response (one possible order):

```json
[
  {"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"batch-health"},
  {"jsonrpc":"2.0","result":{"type":"sint","value":"42"},"id":9},
  {"jsonrpc":"2.0","error":{"code":-32600,"message":"Invalid Request","data":{"category":"request","detail":"Batch member must be a request object."}},"id":null}
]
```

The type-check notification has no response. The number `17` is invalid,
so it receives an error with `id: null`.

### Notification-only batch

Request:

```json
[
  {"jsonrpc":"2.0","method":"service.health","params":{}},
  {"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"40 + 2"}}
]
```

Response: HTTP `204`, with no body. There is no JSON response envelope.

### Single notification

Request:

```json
{"jsonrpc":"2.0","method":"service.health","params":{}}
```

Response: HTTP `204`, with no body.

### Empty batch

Request:

```json
[]
```

Response:

```json
{"jsonrpc":"2.0","error":{"code":-32600,"message":"Invalid Request","data":{"category":"request","detail":"Batch must not be empty."}},"id":null}
```

## JSON Schema files

- [request.schema.json](request.schema.json) describes a request or a
  nonempty batch. It includes the known methods' parameter rules and a
  separate `$defs.envelope` for the first validation stage.
- [response.schema.json](response.schema.json) describes a response or a
  nonempty response array, including success results and error objects.

Both use JSON Schema Draft 2020-12 and local references, so they do not need
other schema files. They describe valid shapes, not every runtime rule.
The dispatcher still checks UTF-8 byte length, deadlines, method lookup,
ID matching, and the mapping from error codes to categories.

Validate in the stages described above rather than returning Invalid Request
for every schema failure. For example, missing `source` is Invalid params,
not Invalid Request. A batch can fail the overall request schema because
one member is invalid; the server must still process its other members.
An unknown method can pass the schema but must receive Method not found.
Do not try to validate an empty HTTP `204` body against the response schema.
