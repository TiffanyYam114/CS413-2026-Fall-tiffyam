"""Process-local lazy stream positions, protected for concurrent requests."""

from dataclasses import dataclass
from threading import RLock
from time import monotonic
from uuid import uuid4

from rpc_errors import RpcError, integer_in_range, valid_stream_id
from solver import Solver, force_cell, event_to_dict


@dataclass
class StreamState:
    current: object
    size: int
    last_access: float
    done: bool = False


class StreamManager:
    def __init__(self, solver=None, *, clock=monotonic, lifetime=600):
        self.solver = solver if solver is not None else Solver()
        self.clock = clock
        self.lifetime = lifetime
        self._streams = {}
        self._lock = RLock()

    def cleanup(self):
        with self._lock:
            now = self.clock()
            expired = [key for key, state in self._streams.items()
                       if now - state.last_access >= self.lifetime]
            for key in expired:
                del self._streams[key]

    def _find(self, stream_id):
        self.cleanup()
        if stream_id not in self._streams:
            raise RpcError(-32001, "Unknown, closed, or expired stream ID")
        return self._streams[stream_id]

    def open(self, size):
        integer_in_range(size, "size", 4, 10)
        with self._lock:
            self.cleanup()
            current = self.solver.open(size)  # Does not force a cell.
            stream_id = str(uuid4())
            self._streams[stream_id] = StreamState(current, size, self.clock())
            return {"stream_id": stream_id, "size": size}

    def next(self, stream_id, limit):
        valid_stream_id(stream_id)
        integer_in_range(limit, "limit", 1, 32)
        with self._lock:
            state = self._find(stream_id)
            events = []
            try:
                for _ in range(limit):
                    if state.done:
                        break
                    cell = force_cell(state.current)
                    if not cell.is_cons:
                        # The fixed solver must end with a done event.
                        raise RuntimeError("Solver ended without done")
                    event = event_to_dict(cell.head)
                    events.append(event)
                    if event["event"] == "done":
                        state.done = True
                        state.current = None  # Release all search closures.
                        break
                    state.current = cell.tail  # Save, but never force ahead.
            except Exception:
                # No later request may reuse a partly advanced failed stream.
                del self._streams[stream_id]
                raise
            state.last_access = self.clock()
            return {"events": events, "done": state.done}

    def close(self, stream_id):
        valid_stream_id(stream_id)
        with self._lock:
            self._find(stream_id)
            del self._streams[stream_id]
            return {"closed": True}
