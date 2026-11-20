"""Stream lifecycle, JSON-RPC contract, and real local HTTP tests."""

from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from itertools import islice
import json
from threading import Thread
import unittest
from unittest.mock import patch
from uuid import UUID

from rpc import Dispatcher
from rpc_errors import RpcError
from server import RpcServer
from solver import Solver, force_cell
from streams import StreamManager


class StreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = Solver()

    def setUp(self):
        self.now = 0
        self.manager = StreamManager(self.solver, clock=lambda: self.now)

    def open(self, size=4):
        return self.manager.open(size)["stream_id"]

    def assert_unknown(self, stream_id):
        with self.assertRaises(RpcError) as caught:
            self.manager.next(stream_id, 1)
        self.assertEqual(caught.exception.code, -32001)

    def test_open_is_lazy_and_next_respects_one_and_32(self):
        with patch("streams.force_cell", wraps=force_cell) as force:
            stream_id = self.open(10)
            self.assertEqual(str(UUID(stream_id)), stream_id)
            force.assert_not_called()
            self.assertFalse(self.manager._streams[stream_id].current.evaluated)
            for limit in (1, 32):
                force.reset_mock()
                result = self.manager.next(stream_id, limit)
                self.assertEqual(len(result["events"]), limit)
                self.assertEqual(force.call_count, limit)
                self.assertFalse(result["done"])
                self.assertFalse(self.manager._streams[stream_id].current.evaluated)

    def test_streams_are_independent_and_close_removes_state(self):
        first, second = self.open(), self.open()
        self.assertNotEqual(first, second)
        a = self.manager.next(first, 1)
        self.manager.next(first, 8)
        self.assertEqual(self.manager.next(second, 1), a)
        self.assertEqual(self.manager.close(first), {"closed": True})
        self.assertNotIn(first, self.manager._streams)
        self.assert_unknown(first)
        with self.assertRaises(RpcError) as caught:
            self.manager.close(first)
        self.assertEqual(caught.exception.code, -32001)
        self.assert_unknown("unknown-id")

    def test_exhaustion_releases_closures_and_repeated_next_is_empty(self):
        stream_id = self.open()
        events = []
        while True:
            result = self.manager.next(stream_id, 32)
            self.assertLessEqual(len(result["events"]), 32)
            events.extend(result["events"])
            if result["done"]:
                break
        self.assertEqual(events[-1], {"event": "done"})
        self.assertEqual(sum(e["event"] == "done" for e in events), 1)
        self.assertEqual(sum(e["event"] == "solution" for e in events), 2)
        self.assertIsNone(self.manager._streams[stream_id].current)
        with patch("streams.force_cell", wraps=force_cell) as force:
            for limit in (1, 32):
                self.assertEqual(self.manager.next(stream_id, limit),
                                 {"events": [], "done": True})
            force.assert_not_called()
        self.assertEqual(self.manager.close(stream_id), {"closed": True})

    def test_expiration_refresh_and_cleanup_on_health(self):
        first, second = self.open(), self.open()
        self.now = 599
        self.manager.next(first, 1)  # Refresh only first.
        self.now = 600
        reply = Dispatcher(self.manager).handle(
            {"jsonrpc": "2.0", "id": 1, "method": "service.health"})
        self.assertIn("result", reply)
        self.assertNotIn(second, self.manager._streams)
        self.assertIn(first, self.manager._streams)
        self.assert_unknown(second)
        self.now = 1199
        self.assert_unknown(first)
        self.assertEqual(self.manager._streams, {})

    def test_completed_record_expires(self):
        stream_id = self.open()
        while not self.manager.next(stream_id, 32)["done"]:
            pass
        self.now = 600
        self.assert_unknown(stream_id)

    def test_invalid_parameters_do_not_allocate_or_advance(self):
        with patch.object(self.solver, "open", wraps=self.solver.open) as open_solver:
            for size in (3, 11, True, "8", 8.5, None):
                with self.subTest(size=size), self.assertRaises(RpcError) as caught:
                    self.manager.open(size)
                self.assertEqual(caught.exception.code, -32602)
            open_solver.assert_not_called()
        stream_id = self.open()
        original = self.manager._streams[stream_id].current
        for limit in (0, 33, True, "1", 1.5, None):
            with self.subTest(limit=limit), self.assertRaises(RpcError) as caught:
                self.manager.next(stream_id, limit)
            self.assertEqual(caught.exception.code, -32602)
        self.assertIs(self.manager._streams[stream_id].current, original)
        self.assertFalse(original.evaluated)

    def test_failed_force_removes_partly_advanced_stream(self):
        stream_id = self.open()
        real_force = force_cell
        calls = 0
        def fail_on_second(stream):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("private interpreter details")
            return real_force(stream)
        with patch("streams.force_cell", side_effect=fail_on_second):
            reply = Dispatcher(self.manager).handle({
                "jsonrpc": "2.0", "id": "failure", "method": "queens.next",
                "params": {"stream_id": stream_id, "limit": 2}})
        self.assertEqual(reply, {"jsonrpc": "2.0", "id": "failure",
                                 "error": {"code": -32603, "message": "Internal error"}})
        self.assert_unknown(stream_id)

    def test_concurrent_requests_consume_separate_contiguous_batches(self):
        stream_id = self.open()
        expected = list(islice(self.solver.events(4), 64))
        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs = [executor.submit(self.manager.next, stream_id, 32) for _ in range(2)]
            actual = [json.dumps(job.result()["events"], sort_keys=True) for job in jobs]
        batches = [json.dumps(expected[:32], sort_keys=True),
                   json.dumps(expected[32:], sort_keys=True)]
        self.assertCountEqual(actual, batches)


class RpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = Solver()

    def setUp(self):
        self.manager = StreamManager(self.solver)
        self.rpc = Dispatcher(self.manager)

    def call(self, method, params=None, request_id=1):
        request = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            request["params"] = params
        return self.rpc.handle(request)

    def test_health_and_request_ids(self):
        for request_id in (None, 0, 4.5, "request-1"):
            reply = self.call("service.health", {}, request_id)
            self.assertEqual(reply, {"jsonrpc": "2.0", "id": request_id,
                                     "result": {"status": "ok", "version": "1.0"}})
        self.assertIn("result", self.call("service.health"))

    def test_invalid_envelopes_and_batches(self):
        for request in (None, 1, "hello", [], [{}], {},
                        {"jsonrpc": "1.0", "method": "service.health", "id": 1},
                        {"jsonrpc": "2.0", "method": 1},
                        {"jsonrpc": "2.0", "method": "service.health", "id": True},
                        {"jsonrpc": "2.0", "method": "service.health", "id": []}):
            with self.subTest(request=request):
                reply = self.rpc.handle(request)
                self.assertEqual(reply["error"]["code"], -32600)
                self.assertIsNone(reply["id"])

    def test_malformed_json(self):
        for body in (b"", b"{", b"\xff", b'{"id":NaN}', b'{"id":Infinity}',
                     b'{"id":1e9999}'):
            with self.subTest(body=body):
                reply = self.rpc.handle_json(body)
                self.assertEqual(reply["error"]["code"], -32700)
                self.assertIsNone(reply["id"])

    def test_unknown_method_and_stream_errors_preserve_id(self):
        self.assertEqual(self.call("eval", {"source": "1"}, "a")["error"]["code"], -32601)
        for method, params in (("queens.next", {"stream_id": "missing", "limit": 1}),
                               ("queens.close", {"stream_id": "missing"})):
            reply = self.call(method, params, "b")
            self.assertEqual(reply["id"], "b")
            self.assertEqual(reply["error"]["code"], -32001)

    def test_exact_parameter_shapes(self):
        cases = [
            ("service.health", []), ("service.health", {"extra": 1}),
            ("queens.open", {}), ("queens.open", {"size": 8, "source": "1"}),
            ("queens.open", {"size": True}), ("queens.open", {"size": 11}),
            ("queens.next", {"stream_id": "a"}),
            ("queens.next", {"stream_id": "a", "limit": 33}),
            ("queens.next", {"stream_id": "a", "limit": False}),
            ("queens.close", {"stream_id": ""}),
            ("queens.close", {"stream_id": 5}),
            ("queens.close", {"stream_id": "a", "extra": 1}),
        ]
        with patch.object(self.solver, "open", wraps=self.solver.open) as open_solver:
            for method, params in cases:
                with self.subTest(method=method, params=params):
                    self.assertEqual(self.call(method, params)["error"]["code"], -32602)
            open_solver.assert_not_called()
        reply = self.rpc.handle_json(
            b'{"jsonrpc":"2.0","id":7,"method":"queens.open","params":null}')
        self.assertEqual(reply["error"]["code"], -32602)

    def test_notifications_execute_and_suppress_success_and_errors(self):
        stream_id = self.manager.open(4)["stream_id"]
        notification = {"jsonrpc": "2.0", "method": "queens.next",
                        "params": {"stream_id": stream_id, "limit": 1}}
        self.assertIsNone(self.rpc.handle(notification))
        self.assertEqual(self.manager.next(stream_id, 1)["events"][0]["event"], "place")
        self.assertIsNone(self.rpc.handle({"jsonrpc": "2.0", "method": "queens.close",
                                           "params": {"stream_id": stream_id}}))
        self.assertNotIn(stream_id, self.manager._streams)
        for method, params in (("unknown", {}), ("queens.open", {"size": False}),
                               ("queens.next", {"stream_id": "missing", "limit": 1})):
            self.assertIsNone(self.rpc.handle({"jsonrpc": "2.0", "method": method,
                                                "params": params}))


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manager = StreamManager()
        cls.server = RpcServer(("127.0.0.1", 0), Dispatcher(cls.manager))
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=5)

    def request(self, body, *, path="/rpc", content_type="application/json", method="POST"):
        connection = HTTPConnection("127.0.0.1", self.server.server_port, timeout=30)
        try:
            connection.request(method, path, body=body, headers={"Content-Type": content_type})
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def call(self, method, params, request_id=1):
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        status, content_type, body = self.request(json.dumps(request))
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/json")
        reply = json.loads(body)
        self.assertEqual(reply["id"], request_id)
        return reply

    def test_health_over_http(self):
        self.assertEqual(self.call("service.health", {})["result"],
                         {"status": "ok", "version": "1.0"})

    def test_http_errors_notifications_and_transport_rules(self):
        for body, code in ((b"{", -32700), (b"[]", -32600),
                           (b'{"jsonrpc":"2.0","id":1,"method":"unknown"}', -32601),
                           (b'{"jsonrpc":"2.0","id":1,"method":"queens.open","params":{}}', -32602)):
            status, content_type, data = self.request(body)
            self.assertEqual(status, 200)
            self.assertEqual(content_type, "application/json")
            self.assertEqual(json.loads(data)["error"]["code"], code)
        for method in ("service.health", "unknown", "queens.open"):
            status, _, data = self.request(json.dumps(
                {"jsonrpc": "2.0", "method": method, "params": {}}))
            self.assertEqual((status, data), (204, b""))
        self.assertEqual(self.request(b"{}", content_type="text/plain")[0], 415)
        self.assertEqual(self.request(b"{}", path="/other")[0], 404)
        self.assertEqual(self.request(None, method="GET")[0], 405)
        self.assertEqual(self.request(b"{}", content_type="application/json; charset=utf-8")[0], 200)

    def test_http_close_and_unknown_id(self):
        stream_id = self.call("queens.open", {"size": 4})["result"]["stream_id"]
        self.assertEqual(self.call("queens.close", {"stream_id": stream_id})["result"],
                         {"closed": True})
        self.assertEqual(self.call("queens.next", {"stream_id": stream_id, "limit": 1})
                         ["error"]["code"], -32001)

    def test_http_flow_all_92_solutions_and_final_done(self):
        stream_id = self.call("queens.open", {"size": 8}, "open")["result"]["stream_id"]
        solutions = []
        done_events = 0
        request_id = 0
        while True:
            # Exercise both limit boundaries in the same real HTTP search.
            limit = 1 if request_id == 0 else 32
            reply = self.call("queens.next", {"stream_id": stream_id, "limit": limit}, request_id)
            self.assertIn("result", reply)
            result = reply["result"]
            self.assertLessEqual(len(result["events"]), limit)
            self.assertTrue(result["events"])
            for event in result["events"]:
                if event["event"] == "solution":
                    board = tuple(event["board"])
                    self.assertEqual(len(board), 8)
                    self.assertTrue(all(c != old and abs(c - old) != row - r
                                        for row, c in enumerate(board)
                                        for r, old in enumerate(board[:row])))
                    solutions.append(board)
                elif event["event"] == "done":
                    done_events += 1
            if result["done"]:
                self.assertEqual(result["events"][-1], {"event": "done"})
                break
            self.assertNotIn({"event": "done"}, result["events"])
            request_id += 1
        self.assertEqual(len(solutions), 92)
        self.assertEqual(len(set(solutions)), 92)
        self.assertEqual(solutions, sorted(solutions))
        self.assertEqual(done_events, 1)
        self.assertIsNone(self.manager._streams[stream_id].current)
        for _ in range(2):
            self.assertEqual(self.call("queens.next", {"stream_id": stream_id, "limit": 32})
                             ["result"], {"events": [], "done": True})
        self.call("queens.close", {"stream_id": stream_id})


if __name__ == "__main__":
    unittest.main()
