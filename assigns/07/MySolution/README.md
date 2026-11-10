# LAMBDA3 JSON-RPC service

This service lets a client type-check, interpret, or compile LAMBDA3 source
over HTTP. It uses the provided `LAMBDA3/lambda3.py` implementation.

All operations use **`POST http://127.0.0.1:8000/rpc`**.

## Requirements and setup

Use Python 3.12 or later. The project uses Flask 3.1.3. Tests also use
jsonschema 4.26.0 and Python's built-in `unittest` runner. 

Keep `MySolution/` beside the provided `LAMBDA3/` directory. Run all commands
below from the assignment directory, `assigns/07`.

Install the server and test dependencies:

```powershell
python -m pip install -r MySolution/requirements-test.txt
```

If you only want to run the server, install `MySolution/requirements.txt`
instead.

## Start the server

```powershell
python -m MySolution.app
```

Leave this terminal open. The server listens on `127.0.0.1:8000`, with debug
mode off. Press Ctrl+C to stop it.

Opening the URL in a browser sends a GET request. This API needs a POST
request with a JSON body; it does not have a webpage. Use the examples below
in a second terminal.

## Run the tests

```powershell
python -B -m unittest discover -s MySolution/tests -t . -v
```

The tests use Flask's test client, so the server does not need to be running.
The `-B` option avoids creating Python bytecode caches. See
`TESTING.md` for test names, results, and the architecture diagram.

## Send requests with curl

These examples use **Windows PowerShell and `curl.exe`**. JSON is piped to
curl so PowerShell does not change the quotation marks inside the request.
The server must be running for these commands.

Each request includes an `id`. The response repeats that ID so the client
can match it to the request.

### Check service health

```powershell
'{"jsonrpc":"2.0","method":"service.health","params":{},"id":"health-1"}' |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

Expected response (field order may differ):

```json
{"jsonrpc":"2.0","result":{"status":"ok","version":"1.0"},"id":"health-1"}
```

### Type-check a program

```powershell
'{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"40 + 2"},"id":"type-1"}' |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

Expected response:

```json
{"jsonrpc":"2.0","result":{"type":"sint"},"id":"type-1"}
```

### Interpret factorial

This computes factorial 6, which is 720.

```powershell
$body = @'
{
  "jsonrpc": "2.0",
  "method": "lambda.interpret",
  "params": {
    "source": "let fact : sint -> sint = fix fact(n: sint): sint => if n <= 1 then 1 else n * fact(n - 1) in fact(6) end"
  },
  "id": "fact-6"
}
'@
$body |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

Expected response:

```json
{"jsonrpc":"2.0","result":{"type":"sint","value":"720"},"id":"fact-6"}
```

The value is a formatted string. Functions use `<lam>` or `<fix>` rather
than exposing Python closure objects.

### Compile to Python

```powershell
'{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"40 + 2","target":"python"},"id":"compile-python"}' |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

The response has `id: "compile-python"` and a `result` with `target: "python"`
and `code`. The `code` field contains the complete generated Python source,
including runtime helpers.

### Compile to JavaScript

```powershell
'{"jsonrpc":"2.0","method":"lambda.compile","params":{"source":"40 + 2","target":"javascript"},"id":"compile-javascript"}' |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

The response has `id: "compile-javascript"` and a `result` with
`target: "javascript"` and the complete generated source in `code`.

**The service returns generated code but never runs it.** Every source
method parses and type-checks the program first.

### Try an unbound variable

The variable `x` has no definition, so this request fails type-checking.

```powershell
'{"jsonrpc":"2.0","method":"lambda.typecheck","params":{"source":"x + 1"},"id":"unbound-1"}' |
  curl.exe -sS -X POST http://127.0.0.1:8000/rpc -H "Content-Type: application/json" --data-binary "@-"
```

Expected response:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32011,
    "message": "LAMBDA type error",
    "data": {"category":"typecheck","detail":"unbound variable 'x'"}
  },
  "id": "unbound-1"
}
```

## Limits and errors

- Source must be a nonblank string, at most **65,536 UTF-8 bytes** per call.
- Interpretation has a **two-second deadline**, including worker startup,
  parsing, type-checking, evaluation, and formatting. The server stops the
  worker if it takes too long. A timeout does not prove the program would
  run forever.
- RPC responses use **HTTP 200**, even when they contain an `error`.
  Unsupported media types use HTTP 415 instead.
- A request without an `id` is a notification. It is processed without a
  JSON response; a single notification uses HTTP 204 and an empty body.
- A batch is an array of requests. Match responses by ID, not array order.
  Notifications are left out of the response array.

The complete method rules, error codes, batch examples, and limits are in
`RPC.md`.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Flask endpoint, HTTP checks, and JSON decoding. |
| `dispatcher.py` | Request envelopes, method lookup, IDs, batches, and notifications. |
| `lambda_service.py` | Parameter checks, calls to LAMBDA3, and the interpretation worker. |
| `rpc_errors.py` | Shared RPC error objects. |
| `__init__.py` | Marks `MySolution` as a Python package. |
| `requirements.txt` | Server dependency. |
| `requirements-test.txt` | Server and test dependencies. |
| `request.schema.json`, `response.schema.json` | Describe valid request and response shapes; tests use them for validation. |
| `tests/test_rpc.py` | Automated HTTP tests. |
| `RPC.md` | Full RPC contract. |
| `TESTING.md` | Test commands, requirement mapping, results, and architecture. |

The server checks requests in Python rather than loading the schema files
at runtime. The provided `LAMBDA3/mylib/` modules are available for examples
and tests. This service is intended for local development and testing.
