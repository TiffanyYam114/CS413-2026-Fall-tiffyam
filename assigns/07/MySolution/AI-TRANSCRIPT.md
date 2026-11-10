AI used: Codex

## Prompt 1

### Prompt:
Complete task 1. Use a JSON schema for the request and response envelopes.

### Output Review and Testing:
Codex created request.schema.json and response.schema.json. The request schema accepts `jsonrpc`, `method`, `params`, and `id`. The source string has a maximum size of 65536. The response schema sends `id`, `result`, `error`, `code`, `message`, and `data`. Valid error codes include the required HTTP response codes in the document.

