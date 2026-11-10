AI used: Codex

## Prompt 1

### Prompt:
Complete task 1. Use a JSON schema for the request and response envelopes.

### Output Review and Testing:
Codex created request.schema.json and response.schema.json. The request schema accepts `jsonrpc`, `method`, `params`, and `id`. The source string has a maximum size of 65536. The response schema sends `id`, `result`, `error`, `code`, `message`, and `data`. Valid error codes include the required HTTP response codes in the document.

## Prompt 2

### Prompt:
Complete task 2. Use Flask as the Python web framework.

### Output Review and Testing:
Codex added `app.py`, `dispatcher.py`, `lambda_service.py`, and `rpc_errors.py`. `app.py` is the entry point. It accepts `POST /rpc` and checks that it uses JSON-RPC 2.0. It reads the JSON body and passes it to `dispatcher.py`, which figures out which operation the client requested. `lambda_service.py` contains the four RPC methods. `rpc_errors.py` stores information for an error.

## Prompt 3

### Prompt:
Implement task 3.

### Output Review and Testing:
Codex added `test_rpc.py` using unittest. I reviewed `test_rpc.py` to make sure it included all required tests. Running the file passes all tests.