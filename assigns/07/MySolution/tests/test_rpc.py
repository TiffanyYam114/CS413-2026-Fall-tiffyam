"""Run from assigns/07: python -B -m unittest discover -s MySolution/tests -t . -v"""

import json
import multiprocessing
from pathlib import Path
import re
import time
import unittest
from unittest.mock import Mock, patch

from jsonschema import Draft202012Validator

from MySolution.app import create_app
from MySolution import lambda_service


SOLUTION = Path(__file__).resolve().parents[1]
SOURCE_METHODS = ("lambda.typecheck", "lambda.interpret", "lambda.compile")
FACTORIAL = """let fact : sint -> sint =
  fix fact(n: sint): sint =>
    if n <= 1 then 1 else n * fact(n - 1)
in fact(6) end"""
SLOW_PROGRAM = """let fib : sint -> sint =
  fix fib(n: sint): sint =>
    if n <= 1 then n else fib(n - 1) + fib(n - 2)
in fib(40) end"""


def request(method="service.health", params=None, request_id="request-1"):
    return {
        "jsonrpc": "2.0", "method": method,
        "params": {} if params is None else params, "id": request_id,
    }


def source_params(method, source):
    params = {"source": source}
    if method == "lambda.compile":
        params["target"] = "python"
    return params


class RpcHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        request_schema = json.loads((SOLUTION / "request.schema.json").read_text())
        response_schema = json.loads((SOLUTION / "response.schema.json").read_text())
        Draft202012Validator.check_schema(request_schema)
        Draft202012Validator.check_schema(response_schema)
        cls.request_validator = Draft202012Validator(request_schema)
        cls.response_validator = Draft202012Validator(response_schema)

    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()

    def post(self, body):
        # json.dumps also supports a top-level null, unlike json=None in some
        # test clients. Invalid inputs deliberately bypass the request schema.
        return self.client.post(
            "/rpc", data=json.dumps(body), content_type="application/json",
        )

    def json_body(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        body = response.get_json()
        self.response_validator.validate(body)
        return body

    def assert_result(self, response, expected, request_id="request-1"):
        body = self.json_body(response)
        self.assertEqual(body, {"jsonrpc": "2.0", "result": expected, "id": request_id})

    def assert_error(self, response, code, category, request_id="request-1"):
        body = self.json_body(response)
        self.assertEqual(body["jsonrpc"], "2.0")
        self.assertEqual(body["id"], request_id)
        self.assertNotIn("result", body)
        self.assertEqual(body["error"]["code"], code)
        self.assertEqual(body["error"]["data"]["category"], category)
        return body["error"]

    def assert_empty_notification(self, response):
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b"")

    def test_health_and_request_ids(self):
        for request_id in ["health-1", 0, 42, 1.5, None]:
            with self.subTest(request_id=request_id):
                self.assert_result(
                    self.post(request(request_id=request_id)),
                    {"status": "ok", "version": "1.0"}, request_id,
                )

    def test_typecheck_formatted_types(self):
        for source, expected in [
            ("40 + 2", "sint"),
            ("true", "bool"),
            ("(1, true)", "(sint, bool)"),
            ("list_cons(1, list_nil())", "List[sint]"),
            ("lam (x: sint) => x + 1", "sint -> sint"),
        ]:
            with self.subTest(source=source):
                self.assert_result(
                    self.post(request("lambda.typecheck", {"source": source})),
                    {"type": expected},
                )

    def test_interpret_arithmetic(self):
        self.assert_result(
            self.post(request("lambda.interpret", {"source": "6 * 7"})),
            {"type": "sint", "value": "42"},
        )

    def test_interpret_factorial(self):
        self.assert_result(
            self.post(request("lambda.interpret", {"source": FACTORIAL})),
            {"type": "sint", "value": "720"},
        )

    def test_interpret_tuple(self):
        self.assert_result(
            self.post(request("lambda.interpret", {"source": "(42, true)"})),
            {"type": "(sint, bool)", "value": "(42, true)"},
        )

    def test_interpret_collection(self):
        self.assert_result(
            self.post(request("lambda.interpret", {
                "source": "list_cons(1, list_cons(2, list_nil()))",
            })),
            {"type": "List[sint]", "value": "[1, 2]"},
        )

    def test_provided_list_library(self):
        declarations = (SOLUTION.parent / "LAMBDA3/mylib/list.lam").read_text()
        source = "let\n" + declarations + "\nin list_length(list_range(1, 5)) end"
        self.assert_result(
            self.post(request("lambda.interpret", {"source": source})),
            {"type": "sint", "value": "4"},
        )

    def test_compile_both_targets_returns_unchanged_code(self):
        expression, _ = lambda_service.lambda3.d0exp_parse_and_typecheck(FACTORIAL)
        for target, compiler in [
            ("python", lambda_service.lambda3.d0exp_compile),
            ("javascript", lambda_service.lambda3.d0exp_compile_js),
        ]:
            with self.subTest(target=target):
                body = self.json_body(self.post(request("lambda.compile", {
                    "source": FACTORIAL, "target": target,
                })))
                self.assertEqual(body["id"], "request-1")
                self.assertEqual(body["result"]["target"], target)
                code = body["result"]["code"]
                self.assertIsInstance(code, str)
                self.assertTrue(code.strip())
                self.assertEqual(code, compiler(expression))

    def test_compile_does_not_execute_generated_code(self):
        for target in ["python", "javascript"]:
            with self.subTest(target=target):
                # Evaluation would divide by zero; compilation must succeed.
                body = self.json_body(self.post(request("lambda.compile", {
                    "source": "1 / 0", "target": target,
                })))
                self.assertEqual(body["result"]["target"], target)
                self.assertTrue(body["result"]["code"].strip())

    def test_syntax_errors(self):
        for method in SOURCE_METHODS:
            with self.subTest(method=method):
                error = self.assert_error(self.post(request(
                    method, source_params(method, "1 +"), "syntax-1",
                )), -32010, "syntax", "syntax-1")
                self.assertEqual(error["message"], "LAMBDA syntax error")
                self.assertEqual(error["data"]["detail"], "Expected an expression")
                self.assertEqual(error["data"]["line"], 1)
                self.assertEqual(error["data"]["column"], 4)
                self.assertNotIn("<lambda>", json.dumps(error))

    def test_type_errors(self):
        for method in SOURCE_METHODS:
            with self.subTest(method=method):
                error = self.assert_error(self.post(request(
                    method, source_params(method, "1 + true"), "type-1",
                )), -32011, "typecheck", "type-1")
                self.assertEqual(error["message"], "LAMBDA type error")
                self.assertIn("expected", error["data"]["detail"])

    def test_unbound_variable_rejected(self):
        for method in SOURCE_METHODS:
            with self.subTest(method=method):
                error = self.assert_error(self.post(request(
                    method, source_params(method, "x + 1"),
                )), -32011, "typecheck")
                self.assertEqual(error["data"]["detail"], "unbound variable 'x'")

    def test_malformed_json(self):
        for raw in ["", "{", '{"id": 1,}', "NaN", "Infinity", b"\xff"]:
            with self.subTest(raw=raw):
                self.assert_error(self.client.post(
                    "/rpc", data=raw, content_type="application/json",
                ), -32700, "json_parse", None)

    def test_invalid_envelopes(self):
        for body in [
            None, 17, "hello", {},
            {"jsonrpc": "2.0", "params": {}},
            {"jsonrpc": "2.0", "method": 42},
            {"jsonrpc": "2.0", "method": "service.health", "id": True},
            {"jsonrpc": "2.0", "method": "service.health", "id": []},
            {"jsonrpc": "2.0", "method": "service.health", "id": {}},
        ]:
            with self.subTest(body=body):
                self.assert_error(self.post(body), -32600, "request", None)

    def test_invalid_envelope_preserves_usable_id(self):
        self.assert_error(self.post({
            "jsonrpc": "1.0", "method": "service.health", "id": "bad-version",
        }), -32600, "request", "bad-version")

    def test_unknown_method_and_case_sensitive_names(self):
        for method in ["unknown", "Service.health", "lambda.TYPECHECK"]:
            with self.subTest(method=method):
                self.assert_error(self.post(request(method)), -32601, "method")

    def test_missing_or_nonobject_params(self):
        for method in ("service.health", *SOURCE_METHODS):
            for params in ["missing", None, [], "text", 42, True]:
                with self.subTest(method=method, params=params):
                    body = request(method)
                    if params == "missing":
                        del body["params"]
                    else:
                        body["params"] = params
                    self.assert_error(self.post(body), -32602, "params")

    def test_invalid_source_parameters(self):
        for method in SOURCE_METHODS:
            for source in ["", " \n\t", None, 42, True, [], {}]:
                with self.subTest(method=method, source=source):
                    self.assert_error(self.post(request(
                        method, source_params(method, source),
                    )), -32602, "params")
            with self.subTest(method=method, source="missing"):
                params = source_params(method, "1")
                del params["source"]
                self.assert_error(self.post(request(method, params)), -32602, "params")

    def test_extra_parameters_rejected(self):
        for method in ("service.health", *SOURCE_METHODS):
            with self.subTest(method=method):
                params = {} if method == "service.health" else source_params(method, "1")
                params["extra"] = "unexpected"
                self.assert_error(self.post(request(method, params)), -32602, "params")

    def test_invalid_compile_target(self):
        for params in [
            {"source": "1"},
            *({"source": "1", "target": target} for target in [None, "Python", "ruby", [], 42]),
        ]:
            with self.subTest(params=params):
                self.assert_error(self.post(request("lambda.compile", params)), -32602, "params")

    def test_oversized_source_rejected_in_bytes(self):
        for source in ["1" * 65_537, "#" + "é" * 32_768 + "\n1"]:
            for method in SOURCE_METHODS:
                with self.subTest(method=method, characters=len(source)):
                    error = self.assert_error(self.post(request(
                        method, source_params(method, source),
                    )), -32602, "params")
                    self.assertEqual(error["data"]["parameter"], "source")
                    self.assertEqual(error["data"]["limit"], 65_536)
                    self.assertEqual(error["data"]["unit"], "bytes")

    def test_source_at_size_limit_is_accepted(self):
        source = "#" + "a" * (65_536 - 3) + "\n1"
        self.assertEqual(len(source.encode("utf-8")), 65_536)
        self.assert_result(
            self.post(request("lambda.typecheck", {"source": source})),
            {"type": "sint"},
        )

    def test_function_results_hide_closure_internals(self):
        for source, value in [
            ("let secret : sint = 7 in lam (x: sint) => x + secret end", "<lam>"),
            ("fix identity(n: sint): sint => n", "<fix>"),
        ]:
            with self.subTest(value=value):
                self.assert_result(
                    self.post(request("lambda.interpret", {"source": source})),
                    {"type": "sint -> sint", "value": value},
                )

    def test_backend_failure_is_logged_without_leaking_details(self):
        with patch.object(
            lambda_service.lambda3, "d0exp_parse_and_typecheck",
            side_effect=RuntimeError("private C:/secret/backend.py traceback"),
        ):
            with self.assertLogs("MySolution.dispatcher", level="ERROR") as logs:
                error = self.assert_error(self.post(request(
                    "lambda.typecheck", {"source": "1"}, "failure-1",
                )), -32603, "internal", "failure-1")
        self.assertEqual(error, {
            "code": -32603, "message": "Internal error", "data": {"category": "internal"},
        })
        self.assertIn("RuntimeError", "\n".join(logs.output))

    def test_timeout_stops_worker_and_batch_continues(self):
        before = {child.pid for child in multiprocessing.active_children()}
        started = time.monotonic()
        body = self.json_body(self.post([
            request("lambda.interpret", {"source": SLOW_PROGRAM}, "slow"),
            request(request_id="after-timeout"),
        ]))
        elapsed = time.monotonic() - started
        by_id = {item["id"]: item for item in body}
        self.assertEqual(set(by_id), {"slow", "after-timeout"})
        self.assertEqual(by_id["slow"]["error"], {
            "code": -32012, "message": "Execution timeout",
            "data": {"category": "timeout", "limit": 2, "unit": "seconds"},
        })
        self.assertEqual(by_id["after-timeout"]["result"], {"status": "ok", "version": "1.0"})
        # Allow scheduling and cleanup time without requiring exact timing.
        self.assertLess(elapsed, 8, "The worker did not stop near its deadline")
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, before)
        self.assert_result(
            self.post(request("lambda.interpret", {"source": "40 + 2"})),
            {"type": "sint", "value": "42"},
        )

    def test_batch_matches_ids_and_omits_notifications(self):
        notification = request("lambda.typecheck", {"source": "1"})
        del notification["id"]
        body = self.json_body(self.post([
            request("lambda.interpret", {"source": "40 + 2"}, 7),
            notification,
            request(request_id="health"),
            request("lambda.typecheck", {"source": "true"}, None),
        ]))
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 3)
        by_id = {item["id"]: item["result"] for item in body}
        self.assertEqual(by_id, {
            7: {"type": "sint", "value": "42"},
            "health": {"status": "ok", "version": "1.0"},
            None: {"type": "bool"},
        })

    def test_invalid_batch_members_have_null_ids(self):
        invalid = [
            17, None, [], {},
            {"jsonrpc": "1.0", "method": "service.health", "id": 5},
            {"jsonrpc": "2.0", "method": "service.health", "id": True},
        ]
        body = self.json_body(self.post([*invalid, request(request_id="valid")]))
        self.assertEqual(len(body), len(invalid) + 1)
        errors = [item for item in body if "error" in item]
        self.assertEqual(len(errors), len(invalid))
        for error in errors:
            self.assertIsNone(error["id"])
            self.assertEqual(error["error"]["code"], -32600)
        self.assertEqual(next(item for item in body if item["id"] == "valid")["result"], {
            "status": "ok", "version": "1.0",
        })

    def test_batch_method_error_keeps_id(self):
        body = self.json_body(self.post([request("unknown", request_id="missing-method")]))
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], "missing-method")
        self.assertEqual(body[0]["error"]["code"], -32601)

    def test_batch_with_one_reply_still_returns_array(self):
        notification = request()
        del notification["id"]
        body = self.json_body(self.post([notification, request(request_id="only-call")]))
        self.assertIsInstance(body, list)
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["id"], "only-call")

    def test_empty_batch_returns_one_error_object(self):
        self.assert_error(self.post([]), -32600, "request", None)

    def test_single_notification_has_no_body(self):
        body = request("lambda.typecheck", {"source": "40 + 2"})
        del body["id"]
        self.assert_empty_notification(self.post(body))

    def test_notification_only_batch_has_no_body(self):
        bodies = [request(), request("lambda.typecheck", {"source": "1"})]
        for body in bodies:
            del body["id"]
        self.assert_empty_notification(self.post(bodies))

    def test_notifications_suppress_method_and_parameter_errors(self):
        bodies = [
            {"jsonrpc": "2.0", "method": "unknown"},
            {"jsonrpc": "2.0", "method": "lambda.interpret", "params": {}},
        ]
        for body in bodies:
            with self.subTest(body=body):
                self.assert_empty_notification(self.post(body))
        self.assert_empty_notification(self.post(bodies))

    def test_notification_reaches_dispatch_handler(self):
        # This double checks the dispatch boundary, not a language result.
        dispatcher = self.app.extensions["rpc_dispatcher"]
        handler = Mock(wraps=dispatcher.methods["service.health"])
        dispatcher.methods["service.health"] = handler
        self.assert_empty_notification(self.post({
            "jsonrpc": "2.0", "method": "service.health", "params": {},
        }))
        handler.assert_called_once_with({})

    def test_wrong_media_type_is_http_transport_error(self):
        for media_type in [None, "text/plain", "application/json; charset=latin-1"]:
            with self.subTest(media_type=media_type):
                response = self.client.post("/rpc", data="{}", content_type=media_type)
                self.assertEqual(response.status_code, 415)
                self.assertNotEqual(response.mimetype, "application/json")

    def test_utf8_content_type_parameter_is_accepted(self):
        self.assert_result(self.client.post(
            "/rpc", data=json.dumps(request()),
            content_type="application/json; charset=utf-8",
        ), {"status": "ok", "version": "1.0"})

    def test_wrong_http_method_and_url(self):
        for method in ["GET", "PUT", "DELETE", "OPTIONS"]:
            with self.subTest(method=method):
                response = self.client.open("/rpc", method=method)
                self.assertEqual(response.status_code, 405)
                self.assertNotEqual(response.mimetype, "application/json")
        self.assertEqual(self.client.get("/missing").status_code, 404)

    def test_documented_examples_match_schemas(self):
        # Examples include intentionally invalid batch members and []. Check
        # valid envelopes individually instead of requiring invalid input to pass.
        text = (SOLUTION / "RPC.md").read_text(encoding="utf-8")
        examples = re.findall(r"```json\n(.*?)\n```", text, re.S)
        self.assertTrue(examples)
        for example in examples:
            body = json.loads(example)
            members = body if isinstance(body, list) else [body]
            for member in members:
                if not isinstance(member, dict):
                    continue
                validator = self.request_validator if "method" in member else self.response_validator
                with self.subTest(example=member.get("id")):
                    validator.validate(member)


if __name__ == "__main__":
    unittest.main()
