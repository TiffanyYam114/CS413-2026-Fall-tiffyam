"""Real language integration and replaceable-controller tests for F4–F7."""
import json
from threading import Event
import time
import unittest
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from . import lambda1 as L
from .backend import LambdaBackend, perform
from .controller import SourceController
from .examples import EXAMPLES
from .reader import InputError, read_expression
from .source import SourceConflict, SourceModel
from .tools import Artifact, BackendReply, Outcome


def wait_idle(model, timeout=5):
    deadline = time.monotonic() + timeout
    while model.snapshot()["busy"]:
        if time.monotonic() >= deadline:
            raise AssertionError("Tool action did not leave busy state")
        time.sleep(0.005)
    return model.snapshot()


class LanguageTests(unittest.TestCase):
    def test_free_variables_for_every_constructor_and_scoping(self):
        x, y, z = L.D0Evar("x"), L.D0Evar("y"), L.D0Evar("z")
        cases = [
            (L.D0Eint(1), set()), (L.D0Ebtf(True), set()), (x, {"x"}),
            (L.D0Eop1("+1", x), {"x"}), (L.D0Eop2("+", x, y), {"x", "y"}),
            (L.D0Elam("x", L.D0Epair(x, y)), {"y"}),
            (L.D0Efix("x", "y", L.D0Epair(L.D0Eapp(x, y), z)), {"z"}),
            (L.D0Eapp(x, y), {"x", "y"}), (L.D0Eif0(x, y, z), {"x", "y", "z"}),
            (L.D0Elet("x", x, L.D0Epair(x, z)), {"x", "z"}),
            (L.D0Epair(x, x), {"x"}), (L.D0Epfst(x), {"x"}), (L.D0Epsnd(y), {"y"}),
            (L.D0Elam("x", L.D0Elam("y", L.D0Epair(x, y))), set()),
            (L.D0Elam("unused", L.D0Eint(1)), set()),
        ]
        for expression, expected in cases:
            with self.subTest(expression=expression):
                names = L.d0exp_fvset(expression)
                self.assertIsInstance(names, frozenset)
                self.assertEqual(names, frozenset(expected))

    def test_lint_checks_all_branches_sorts_names_and_never_evaluates(self):
        with patch.object(L, "d0exp_evaluate", side_effect=AssertionError("Lint must not evaluate")):
            reply = perform("lint", 'D0Eop2("/", D0Eint(1), D0Eint(0))')
        self.assertEqual(reply.outcome, Outcome.SUCCESS)
        self.assertEqual(reply.free_variables, frozenset())
        reply = LambdaBackend().lint('D0Eif0(D0Ebtf(True), D0Evar("z"), D0Evar("a"))')
        self.assertEqual(reply.outcome, Outcome.LANGUAGE_ERROR)
        self.assertEqual(reply.free_variables, frozenset({"z", "a"}))
        self.assertEqual(reply.text, "Undeclared variables: 'a', 'z'")

    def test_restricted_reader_multiline_comments_and_argument_validation(self):
        expression = read_expression('# comment\nD0Eop2(name="+",\narg1=D0Eint(-2), arg2=D0Eint(44))')
        self.assertEqual(L.d0exp_evaluate(expression), L.D0Vint(42))
        for source in ['__import__("os").system("echo unsafe")', 'D0Eint(True)',
                       'D0Epair(D0Eint(1), 2)', 'D0Eint(1 + 2)', 'D0Eint(*[1])',
                       'D0Eint()', 'D0Eint(1, arg1=2)', 'D0E000()', 'D0Vint(1)',
                       'D0Evar(1)', 'D0Eint(1); D0Eint(2)']:
            with self.subTest(source=source):
                with self.assertRaises(InputError):
                    read_expression(source)

    def test_real_arithmetic_factorial_fibonacci_and_base_cases(self):
        backend = LambdaBackend()
        reply = backend.interpret('D0Eop2("+", D0Eint(20), D0Eint(22))')
        self.assertEqual(reply.outcome, Outcome.SUCCESS)
        self.assertEqual(reply.text, "D0Vint(arg1=42)")
        for example, default, values in [("factorial", 5, [(0, 1), (1, 1), (5, 120)]),
                                         ("fibonacci", 10, [(0, 0), (1, 1), (10, 55)])]:
            sample = EXAMPLES[example][1]
            for argument, expected in values:
                with self.subTest(example=example, argument=argument):
                    source = sample.replace(f"D0Eint({default})\n)", f"D0Eint({argument})\n)")
                    reply = backend.interpret(source)
                    self.assertEqual(reply.outcome, Outcome.SUCCESS)
                    self.assertEqual(reply.text, f"D0Vint(arg1={expected})")

    def test_input_errors_and_runtime_failures_including_pair_sentinels(self):
        backend = LambdaBackend()
        for invalid in ['D0Eint("bad")', 'D0Eint(', 'D0Eint(False)']:
            self.assertEqual(backend.interpret(invalid).outcome, Outcome.INPUT_ERROR)
        for failure in ['D0Eop2("/", D0Eint(1), D0Eint(0))', 'D0Evar("x")',
                        'D0Epair(D0Eint(1), D0Epair(D0Eint(2), D0Evar("x")))',
                        'D0Eapp(D0Eint(1), D0Eint(2))', 'D0Epfst(D0Eint(1))']:
            with self.subTest(source=failure):
                self.assertEqual(backend.interpret(failure).outcome, Outcome.RUNTIME_ERROR)

    def test_placeholders_do_not_claim_success_or_create_generated_code(self):
        backend = LambdaBackend()
        for operation in (backend.typecheck, backend.compile):
            reply = operation("D0Eint(42)")
            self.assertEqual(reply.outcome, Outcome.NOT_IMPLEMENTED)
            self.assertIn("not yet implemented", reply.text)
            self.assertIsNone(reply.generated_code)
        self.assertEqual(backend.execute(Artifact(1, "future", "code")).outcome, Outcome.NOT_IMPLEMENTED)

    def test_actual_worker_timeout_cleanup_and_successful_retry(self):
        backend = LambdaBackend(timeout=0.000001)
        reply = backend.interpret("D0Eint(42)")
        self.assertEqual(reply.outcome, Outcome.BACKEND_FAILURE)
        self.assertIn("worker limit", reply.text)
        backend.timeout = 3
        self.assertEqual(backend.interpret("D0Eint(42)").text, "D0Vint(arg1=42)")


class RecordingBackend:
    def __init__(self):
        self.calls = []
        self.gate = None
        self.fail = False

    def reply(self, operation, source):
        self.calls.append((operation, source))
        if self.gate is not None and not self.gate.wait(2):
            raise TimeoutError("Injected worker deadline")
        if self.fail:
            self.fail = False
            raise OSError("Injected backend failure")
        outcome = Outcome.NOT_IMPLEMENTED if operation in {"typecheck", "compile"} else Outcome.SUCCESS
        return BackendReply(outcome, f"{operation} reply")

    def lint(self, source): return self.reply("lint", source)
    def interpret(self, source): return self.reply("interpret", source)
    def typecheck(self, source): return self.reply("typecheck", source)
    def compile(self, source): return self.reply("compile", source)
    def execute(self, artifact): return self.reply("execute", artifact)


class ToolControllerTests(unittest.TestCase):
    def test_dispatch_through_replaced_backend_without_view_changes(self):
        model, backend = SourceModel(), RecordingBackend()
        model.apply("D0Eint(42)")
        controller = SourceController(model, backend)
        for operation in ("lint", "interpret", "typecheck", "compile"):
            controller.action(operation)
            result = wait_idle(model)["results"][-1]
            self.assertEqual(result["operation"], operation)
            self.assertEqual(result["revision"], 1)
            self.assertEqual(result["outcome"], "not_implemented" if operation in {"typecheck", "compile"} else "success")
        self.assertEqual(backend.calls, [(op, "D0Eint(42)") for op in ("lint", "interpret", "typecheck", "compile")])
        self.assertFalse(model.snapshot()["artifact_available"])
        with self.assertRaises(SourceConflict):
            controller.action("execute")
        self.assertEqual(len(backend.calls), 4)

    def test_busy_conflicts_backend_failure_preserves_source_and_retry_succeeds(self):
        model, backend = SourceModel(), RecordingBackend()
        model.apply("D0Eint(42)")
        backend.gate = Event()
        backend.fail = True
        controller = SourceController(model, backend)
        controller.action("interpret")
        self.assertEqual(model.snapshot()["busy"], "interpret")
        try:
            for operation in [lambda: model.edit("other"), model.discard, model.manual,
                              lambda: model.load("other", "D0Eint(1)"),
                              lambda: controller.action("lint")]:
                with self.assertRaises(SourceConflict):
                    operation()
        finally:
            backend.gate.set()
        result = wait_idle(model)["results"][-1]
        self.assertEqual(result["outcome"], "backend_failure")
        self.assertEqual(model.snapshot()["source"], "D0Eint(42)")
        controller.action("interpret")
        self.assertEqual(wait_idle(model)["results"][-1]["outcome"], "success")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ToolViewTests(SimpleTestCase):
    def setUp(self):
        self.model = SourceModel()
        self.backend = LambdaBackend()
        for name, value in [("source_model", self.model), ("language_backend", self.backend)]:
            override = patch(f"workbench.views.{name}", value)
            override.start()
            self.addCleanup(override.stop)

    def action(self, operation):
        response = self.client.post("/api/action/", json.dumps({
            "operation": operation, "version": self.model.snapshot()["version"],
        }), content_type="application/json")
        return response

    def result(self, operation):
        self.assertEqual(self.action(operation).status_code, 202)
        return wait_idle(self.model)["results"][-1]

    def test_button_order_no_source_dirty_source_and_execute_guards(self):
        page = self.client.get("/").content.decode()
        labels = ["lint", "interpret", "typecheck", "compile", "execute"]
        positions = [page.index(f'data-operation="{op}"') for op in labels]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Type-check</button>", page)
        for op in labels:
            self.assertEqual(self.action(op).status_code, 409)
        self.model.apply("D0Eint(42)")
        self.assertEqual(self.action("execute").status_code, 409)
        self.model.edit("D0Eint(43)")
        for op in labels:
            self.assertEqual(self.action(op).status_code, 409)

    def test_real_lint_and_interpret_results_have_operation_revision_and_outcome(self):
        self.model.apply('D0Evar("x")')
        result = self.result("lint")
        self.assertEqual(result["operation"], "lint")
        self.assertEqual(result["revision"], 1)
        self.assertEqual(result["outcome"], "language_error")
        self.assertEqual(result["free_variables"], ["x"])
        self.model.apply('D0Eop2("/", D0Eint(1), D0Eint(0))')
        self.assertEqual(self.model.snapshot()["results"], [])
        self.assertEqual(self.result("lint")["outcome"], "success")
        result = self.result("interpret")
        self.assertEqual(result["outcome"], "runtime_error")
        self.assertIn("ZeroDivisionError", result["text"])
        self.model.apply('D0Eint("bad")')
        self.assertEqual(self.result("interpret")["outcome"], "input_error")
        self.model.apply('D0Eint(42)')
        self.assertEqual(self.result("interpret")["text"], "D0Vint(arg1=42)")
        self.assertEqual(self.client.get("/api/source/").json()["state"]["results"][-1]["revision"], 4)

    def test_placeholder_messages_and_unavailable_execute(self):
        self.model.apply("D0Eint(42)")
        for operation in ("typecheck", "compile"):
            result = self.result(operation)
            self.assertEqual(result["outcome"], "not_implemented")
            self.assertIn("not yet implemented", result["text"])
            self.assertFalse(self.model.snapshot()["artifact_available"])
        self.assertEqual(self.action("execute").status_code, 409)
        self.assertIn("generated code", self.model.snapshot()["execute_reason"])

    def test_http_dispatch_uses_replacement_backend_without_view_changes(self):
        backend = RecordingBackend()
        self.model.apply("D0Eint(42)")
        with patch("workbench.views.language_backend", backend):
            for operation in ("lint", "interpret", "typecheck", "compile"):
                with self.subTest(operation=operation):
                    result = self.result(operation)
                    self.assertEqual(result["text"], f"{operation} reply")
                    self.assertEqual(result["revision"], 1)
                    self.assertEqual(result["outcome"], "not_implemented"
                                     if operation in {"typecheck", "compile"} else "success")
            self.assertEqual(self.action("execute").status_code, 409)
        self.assertEqual(backend.calls, [(op, "D0Eint(42)")
                                       for op in ("lint", "interpret", "typecheck", "compile")])
        self.assertFalse(self.model.snapshot()["artifact_available"])

    def test_real_timeout_preserves_source_and_releases_controls_for_retry(self):
        self.model.apply("D0Eint(42)")
        self.backend.timeout = 0.000001
        self.assertEqual(self.result("interpret")["outcome"], "backend_failure")
        self.assertEqual(self.model.snapshot()["source"], "D0Eint(42)")
        self.assertIsNone(self.model.snapshot()["busy"])
        self.backend.timeout = 3
        self.assertEqual(self.result("interpret")["outcome"], "success")
