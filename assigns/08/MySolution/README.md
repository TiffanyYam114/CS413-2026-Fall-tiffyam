## Requirements and commands

Use Python 3.12 or later. Run these commands from the assignment's
`assigns/08/` directory.


Run the solver tests:

```text
python -m unittest discover -s MySolution -p test_solver.py -v
```

Run the RPC and real HTTP tests:

```text
python -m unittest discover -s MySolution -p test_rpc.py -v
```

Run all tests:

```text
python -m unittest discover -s MySolution -p "test_*.py" -v
```

The client tests need Node.js 18 or later, with no npm packages. Node is only
needed for testing; running the app needs Python and a modern browser.
Run only the client checks with:

```text
python -m unittest discover -s MySolution -p test_client.py -v
```

This command generates a small-board trace using the real LAMBDA3 solver and
runs 20 JavaScript tests for playback, rendering, and transport.



Print the first 10 events without searching the rest of the tree:

```text
python MySolution/solver.py --size 8 --limit 10
```

Print every solution and the final solution count:

```text
python MySolution/solver.py --size 8
```

Sizes 4 through 10 are supported. Without `--limit`, larger boards can take
longer because the command deliberately consumes the whole search.

## Run the RPC service

```text
python MySolution/server.py
```

Open **http://127.0.0.1:8000/** in your browser. The RPC endpoint is
`http://127.0.0.1:8000/rpc`. Stop the server with Ctrl+C.
Use `python MySolution/server.py --port 8001` if port 8000 is already in use.
The server binds to the local computer only. Open the root URL for the page;
visiting the RPC URL directly sends GET and receives HTTP 405. Open the page
through this server rather than double-clicking `web/index.html`.


## Try the RPC methods

Leave the server running and open a second PowerShell terminal. Define this
small helper, which sends a JSON-RPC call and returns the parsed response:

```powershell
function Invoke-QueensRpc($method, $parameters) {
    $requestBody = @{
        jsonrpc = "2.0"
        id = 1
        method = $method
        params = $parameters
    } | ConvertTo-Json -Depth 10
    Invoke-RestMethod -Uri http://127.0.0.1:8000/rpc -Method Post `
        -ContentType application/json -Body $requestBody
}

Invoke-QueensRpc "service.health" @{}
$opened = Invoke-QueensRpc "queens.open" @{ size = 8 }
$streamId = $opened.result.stream_id
Invoke-QueensRpc "queens.next" @{ stream_id = $streamId; limit = 1 } |
    ConvertTo-Json -Depth 10
Invoke-QueensRpc "queens.close" @{ stream_id = $streamId }
```

Health returns `{"status":"ok","version":"1.0"}` inside `result`. Open
returns a random `stream_id` and the size, without searching. The first next
call returns `{"event":"try","column":0,"row":0,"board":[]}` inside
`result.events`, with `done: false`. Close returns `{"closed":true}` inside
`result`. See `DESIGN.md` for complete JSON request and response examples.

| Method | Required parameter object |
| --- | --- |
| `service.health` | `{}`; `params` can also be omitted |
| `queens.open` | `{"size":8}`; integer sizes 4 through 10 |
| `queens.next` | `{"stream_id":"...","limit":1}`; integer limits 1 through 32 |
| `queens.close` | `{"stream_id":"..."}` |

Extra parameter fields are rejected. Booleans do not count as integers.
Only these fixed methods are exposed; requests cannot supply source code.
Calls preserve the request ID. A notification omits `id`, executes normally,
and receives HTTP 204 with no body, including when its operation fails.
Use a call for `queens.open` so you receive the new ID.

## Stream lifetime and errors

Each next call returns at most the requested number of events. It never
forces the tail beyond that batch. The response containing the final `done`
event has `done: true`. Later next calls return `{"events":[],"done":true}`.

Streams expire after 600 seconds without a successful next call. New streams
start their timer at creation. Expired entries are removed before the next
valid RPC envelope is dispatched, or during a stream operation. A successful
close removes the entry immediately. A server restart invalidates all IDs.

Exhausted streams release their lazy search state immediately. A small
completion record remains until expiration or close, allowing repeated next
calls to report completion. All state is in memory. One lock protects stream
operations, so concurrent requests cannot consume overlapping batches.

| Error code | Meaning |
| --- | --- |
| `-32700` | Invalid JSON, including non-finite numbers |
| `-32600` | Invalid request envelope; batches are not supported |
| `-32601` | Unknown method |
| `-32602` | Invalid parameter object, size, limit, or ID type |
| `-32603` | Internal error; details are kept out of the response |
| `-32001` | Unknown, closed, or expired stream ID |

JSON-RPC results and errors use HTTP 200 and `application/json`. Parse errors
and invalid envelopes use `id: null`. Operation errors preserve the call ID.
A stream that fails while producing a batch is removed; the client must open
a fresh stream. No partial batch is returned on failure.

HTTP transport errors are separate: an unknown path returns 404, GET on `/rpc`
returns 405, and a content type other than `application/json` returns 415.
The service requires a nonnegative Content-Length, does not support chunked
request bodies, and accepts bodies up to 1 MiB (larger bodies return 413).
Bad request framing returns 400. The service is for local use and does not
include authentication, persistent storage, public hosting, or batch RPC.

## Service files

`streams.py` stores stream positions, applies limits, and handles cleanup.
`rpc.py` validates JSON-RPC envelopes and dispatches the four fixed methods.
`rpc_errors.py` defines public application errors and parameter checks.
`server.py` handles HTTP only. `test_rpc.py` exercises stream state, RPC, and
real HTTP requests using the actual LAMBDA3 solver.

The server serves only a fixed list of browser assets, not arbitrary local
files. `web/rpc-client.mjs` handles transport, `web/controller.mjs` handles
playback and stream state, `web/view.mjs` renders board snapshots, and
`web/app.mjs` connects the controls. `web/index.html` and `web/styles.css`
provide the page and visual states.

## How the solver works

`queens.lam` contains all search logic. `search` passes success and failure
functions to its recursive calls. The safety checker also calls a continuation
instead of returning a Boolean. A solution includes a saved continuation that
can resume the remaining search. See `DESIGN.md` for the search pseudocode.

The solver searches rows from top to bottom and columns from left to right.
Its internal board puts the newest queen first. Event snapshots reverse that
list into row order.

LAMBDA3 events are tuples `(kind, column, row, board)`. Kinds are `0` for
`try`, `1` for `place`, `2` for `reject`, `3` for `backtrack`, `4` for
`solution`, and `5` for `done`. The last two kinds use `-1` as unused
coordinates. `done` also uses an empty board. The Python converter omits these
unused fields when producing event dictionaries.

`solver.py` loads and type-checks the fixed source with the supplied interpreter.
It provides `Solver.open(size)`, `force_cell(stream)`, `event_to_dict(value)`,
and an optional `Solver.events(size)` iterator. Python handles loading and value
conversion; the actual search runs in LAMBDA3. Opening does not search, and
each force leaves the returned tail suspended. Consumers should discard old
cells once they advance to avoid retaining old stream values.

The LAMBDA3 entry point assumes a valid size. The Python interface checks that
it is an integer from 4 through 10 before opening a stream.

The collision helper also rejects row distance zero, allowing the same-row
safety rule to be tested directly. Normal search visits a new row each time
and always starts its safety walk at distance one.

## Reference code

The supplied `LAMBDA3/mytest/eight_queens.lam` and
`LAMBDA3/mytest/eight_queens_stream.lam` informed the collision comparisons and
the use of list and lazy-stream primitives. Their comparisons were adapted to
store columns by row. Their direct-style search and stream-append search were
not copied: this solver uses CPS and emits each individual search event.

The supplied interpreter and standard-library test examples informed the Python
loading, type-checking, and evaluation calls. No changes were made to LAMBDA3.