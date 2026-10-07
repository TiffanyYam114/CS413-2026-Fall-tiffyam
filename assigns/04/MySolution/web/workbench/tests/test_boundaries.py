"""Part 4 architecture checks; runnable with plain unittest, without Django."""
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from .. import lambda1 as L
from ..backend import perform
from ..controller import SourceController
from ..reader import SCHEMAS, read_expression
from ..source import SourceConflict, SourceModel
from ..tools import Artifact, BackendReply, GeneratedCode, Outcome


def completed(model):
    deadline = time.monotonic() + 2
    while model.snapshot()["busy"] is not None:
        if time.monotonic() >= deadline:
            raise AssertionError("Injected backend did not complete")
        time.sleep(0.005)
    return model.snapshot()


class ModelBoundaryTests(unittest.TestCase):
    def test_model_works_when_framework_view_and_language_imports_are_forbidden(self):
        # A fresh interpreter catches dependencies hidden by Django's test setup.
        script = '''
import sys
class DenyDependencies:
    def find_spec(self, fullname, path=None, target=None):
        forbidden = ("django", "workbench.views", "workbench.controller",
                     "workbench.backend", "workbench.reader", "workbench.lambda1")
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Model imported forbidden dependency: " + fullname)
sys.meta_path.insert(0, DenyDependencies())
from workbench.source import SourceModel, SourceError, SourceConflict
from workbench.tools import Outcome, Result
model = SourceModel()
model.edit("D0Eint(42)")
model.apply("D0Eint(42)")
revision, source, artifact, job = model.begin_operation("lint")
assert (revision, source, artifact) == (1, "D0Eint(42)", None)
try:
    model.edit("D0Eint(43)")
except SourceConflict:
    pass
else:
    raise AssertionError("Busy model accepted an edit")
assert model.finish_operation(Result("lint", revision, Outcome.SUCCESS, "closed"), job_id=job)
try:
    model.apply(" ")
except SourceError:
    pass
else:
    raise AssertionError("Blank source accepted")
state = model.snapshot()
assert state["source"] == "D0Eint(42)" and state["revision"] == 1
assert state["draft"] == " " and state["results"][0]["text"] == "closed"
model.discard()
assert not model.snapshot()["dirty"]
assert not any(name == "django" or name.startswith("django.") for name in sys.modules)
print("independent model passed")
'''
        result = subprocess.run([sys.executable, "-I", "-c",
                                 "import sys; sys.path.insert(0, "
                                 + repr(str(Path(__file__).resolve().parents[2])) + ");\n" + script],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("independent model passed", result.stdout)


class BindingBoundaryTests(unittest.TestCase):
    def test_constructor_matrix_covers_the_entire_reader_allowlist(self):
        cases = {
            "D0Eint": ("D0Eint(1)", set()),
            "D0Ebtf": ("D0Ebtf(True)", set()),
            "D0Evar": ('D0Evar("x")', {"x"}),
            "D0Eop1": ('D0Eop1("+1", D0Evar("x"))', {"x"}),
            "D0Eop2": ('D0Eop2("+", D0Evar("x"), D0Evar("x"))', {"x"}),
            "D0Elam": ('D0Elam("x", D0Epair(D0Evar("x"), D0Evar("y")))', {"y"}),
            "D0Efix": ('D0Efix("f", "x", D0Epair(D0Eapp(D0Evar("f"), D0Evar("x")), D0Evar("z")))', {"z"}),
            "D0Eapp": ('D0Eapp(D0Evar("f"), D0Evar("x"))', {"f", "x"}),
            "D0Eif0": ('D0Eif0(D0Evar("c"), D0Evar("x"), D0Evar("y"))', {"c", "x", "y"}),
            "D0Elet": ('D0Elet("x", D0Evar("x"), D0Evar("x"))', {"x"}),
            "D0Epair": ('D0Epair(D0Evar("x"), D0Evar("x"))', {"x"}),
            "D0Epfst": ('D0Epfst(D0Evar("p"))', {"p"}),
            "D0Epsnd": ('D0Epsnd(D0Evar("p"))', {"p"}),
        }
        self.assertEqual(set(cases), set(SCHEMAS), "Add coverage when a constructor is added")
        for constructor, (source, expected) in cases.items():
            with self.subTest(constructor=constructor):
                names = L.d0exp_fvset(read_expression(source))
                self.assertIsInstance(names, frozenset)
                self.assertEqual(names, frozenset(expected))

    def test_nested_shadowing_and_recursive_binding_do_not_escape_their_scope(self):
        cases = [
            ('D0Elam("x", D0Elet("x", D0Evar("x"), D0Evar("x")))', set()),
            ('D0Elet("x", D0Evar("y"), D0Elam("y", D0Epair(D0Evar("x"), D0Evar("y"))))', {"y"}),
            ('D0Elam("x", D0Elam("x", D0Epair(D0Evar("x"), D0Evar("z"))))', {"z"}),
            ('D0Epair(D0Elam("x", D0Evar("x")), D0Evar("x"))', {"x"}),
            ('D0Epair(D0Efix("f", "x", D0Eapp(D0Evar("f"), D0Evar("x"))), D0Evar("f"))', {"f"}),
            ('D0Elam("z", D0Efix("f", "x", D0Epair(D0Eapp(D0Evar("f"), D0Evar("x")), D0Evar("z"))))', set()),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                reply = perform("lint", source)
                self.assertIsInstance(reply.free_variables, frozenset)
                self.assertEqual(reply.free_variables, frozenset(expected))
                self.assertEqual(reply.outcome, Outcome.LANGUAGE_ERROR if expected else Outcome.SUCCESS)


class ControllerBoundaryTests(unittest.TestCase):
    def test_injected_backend_bypasses_default_adapter_reader_and_evaluator(self):
        class Backend:
            def lint(self, source):
                self.source = source
                return BackendReply(Outcome.SUCCESS, "replacement lint", frozenset())

        model, backend = SourceModel(), Backend()
        # The model accepts text; constructor validation belongs to the backend.
        model.apply("text understood by a replacement backend")
        with patch("workbench.controller.LambdaBackend", side_effect=AssertionError("Default adapter constructed")), \
             patch("workbench.backend.read_expression", side_effect=AssertionError("Reader used by controller")), \
             patch.object(L, "d0exp_evaluate", side_effect=AssertionError("Evaluator used by controller")):
            SourceController(model, backend).action("lint")
            state = completed(model)
        self.assertEqual(backend.source, state["source"])
        self.assertEqual(state["results"][-1]["text"], "replacement lint")
        self.assertEqual(state["results"][-1]["outcome"], "success")

    def test_future_execute_consumes_exact_compiler_artifact_without_recompiling(self):
        # Test-only extension contract; the production Compile remains a placeholder.
        class FutureBackend:
            def __init__(self):
                self.calls = []

            def compile(self, source):
                self.calls.append(("compile", source))
                return BackendReply(Outcome.SUCCESS, "compiled", generated_code=GeneratedCode("future", "code"))

            def execute(self, artifact):
                self.calls.append(("execute", artifact))
                return BackendReply(Outcome.SUCCESS, "executed artifact")

        model, backend = SourceModel(), FutureBackend()
        model.apply("D0Eint(42)")
        controller = SourceController(model, backend)
        controller.action("compile")
        self.assertTrue(completed(model)["artifact_available"])
        artifact = model.artifact
        self.assertEqual(artifact, Artifact(1, "future", "code"))
        controller.action("execute")
        self.assertEqual(completed(model)["results"][-1]["text"], "executed artifact")
        self.assertEqual(backend.calls, [("compile", "D0Eint(42)"), ("execute", artifact)])
        self.assertIs(backend.calls[-1][1], artifact)
        model.apply("D0Eint(43)")
        with self.assertRaises(SourceConflict):
            controller.action("execute")
        self.assertEqual(len(backend.calls), 2)
