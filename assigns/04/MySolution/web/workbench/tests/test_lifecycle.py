"""Revision, result, artifact, and recovery regressions for F8–F10."""
import json
from threading import Event
import unittest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from ..controller import SourceController
from ..source import SourceConflict, SourceError, SourceModel
from .test_tools import RecordingBackend, wait_idle
from ..tools import Artifact, BackendReply, Outcome, Result


class LifecycleModelTests(unittest.TestCase):
    def setUp(self):
        self.model = SourceModel()
        self.model.apply("D0Eint(42)")

    def compiled(self):
        revision, _, _, job = self.model.begin_operation("compile")
        self.model.finish_operation(Result("compile", revision, Outcome.SUCCESS, "compiled"),
                                    Artifact(revision, "future-format", "generated contents"), job)

    def test_each_accepted_source_change_creates_revision_and_clears_results_and_artifact(self):
        controller = SourceController(self.model)
        for replace in [lambda: controller.upload("uploaded.lambda", b"D0Eint(42)"),
                        lambda: controller.command("example", example="factorial"),
                        lambda: controller.command("example", example="fibonacci"),
                        lambda: controller.command("apply", source="D0Eint(43)")]:
            with self.subTest(replacement=replace):
                self.compiled()
                before = self.model.snapshot()
                self.assertTrue(before["artifact_available"])
                self.assertTrue(before["results"])
                replace()
                after = self.model.snapshot()
                self.assertEqual(after["revision"], before["revision"] + 1)
                self.assertFalse(after["artifact_available"])
                self.assertEqual(after["results"], [])

    def test_rejections_and_discard_preserve_applied_results_and_artifact(self):
        self.compiled()
        before = self.model.snapshot()
        controller = SourceController(self.model)
        for reject in [lambda: controller.command("apply", source=" \n"),
                       lambda: controller.command("apply", source="x" * 65537),
                       lambda: controller.upload("bad.lambda", b"D0Eint(\xff)"),
                       lambda: controller.upload("big.lambda", b"x" * 65537)]:
            with self.assertRaises(SourceError):
                reject()
            after = self.model.snapshot()
            for field in ("source", "source_name", "revision", "results", "artifact_available"):
                self.assertEqual(after[field], before[field])
            self.assertTrue(after["dirty"])
            self.model.discard()
            self.assertEqual(self.model.snapshot()["draft"], before["source"])

    def test_failed_recompilation_invalidates_old_artifact(self):
        self.compiled()
        revision, _, artifact, job = self.model.begin_operation("compile")
        self.assertIsNone(artifact)
        self.model.finish_operation(Result("compile", revision, Outcome.BACKEND_FAILURE, "compiler failed"), job_id=job)
        self.assertFalse(self.model.snapshot()["artifact_available"])
        with self.assertRaises(SourceConflict):
            self.model.begin_operation("execute")

    def test_windows_uploads_match_textarea_and_raw_input_byte_limit_is_enforced(self):
        controller = SourceController(self.model)
        controller.upload("windows.lambda", b"# comment\r\nD0Eint(42)\r\n")
        self.assertEqual(self.model.snapshot()["source"], "# comment\nD0Eint(42)\n")
        self.model.edit("# comment\nD0Eint(42)\n")
        self.assertFalse(self.model.snapshot()["dirty"])
        self.model.require_applied_source()
        before = self.model.snapshot()
        with self.assertRaises(SourceError):
            self.model.apply("\r\n" * 32768 + "x")
        self.assertEqual(self.model.snapshot()["revision"], before["revision"])
        self.assertEqual(self.model.snapshot()["source"], before["source"])

    def test_watchdog_releases_busy_state_and_late_completion_cannot_overwrite_retry(self):
        release, started, ignored = Event(), Event(), Event()

        class SlowBackend(RecordingBackend):
            def interpret(self, source):
                self.calls.append(("interpret", source))
                if len(self.calls) == 1:
                    started.set()
                    release.wait(3)
                    return BackendReply(Outcome.SUCCESS, "old late result")
                return BackendReply(Outcome.SUCCESS, "successful retry")

        controller = SourceController(self.model, SlowBackend(), timeout=0.1)
        real_finish = self.model.finish_operation

        def finish(result, artifact=None, job_id=None):
            accepted = real_finish(result, artifact, job_id)
            if result.text == "old late result":
                self.assertFalse(accepted)
                ignored.set()
            return accepted

        with patch.object(self.model, "finish_operation", side_effect=finish):
            try:
                controller.action("interpret")
                self.assertTrue(started.wait(1))
                failed = wait_idle(self.model)
                self.assertIn("action limit", failed["results"][-1]["text"])
                self.assertEqual(failed["results"][-1]["outcome"], "backend_failure")
                self.assertEqual(failed["source"], "D0Eint(42)")
                controller.action("interpret")
                retried = wait_idle(self.model)
                self.assertEqual(retried["results"][-1]["text"], "successful retry")
                release.set()
                self.assertTrue(ignored.wait(1))
                self.assertEqual(self.model.snapshot()["results"], retried["results"])
            finally:
                release.set()

    def test_backend_exit_and_invalid_reply_restore_controls(self):
        class ExitingBackend(RecordingBackend):
            def interpret(self, source):
                raise SystemExit("backend stopped")

        class InvalidBackend(RecordingBackend):
            def interpret(self, source):
                return BackendReply(Outcome.SUCCESS, "invalid names", ["x"])

        for backend in (ExitingBackend(), InvalidBackend()):
            controller = SourceController(self.model, backend)
            controller.action("interpret")
            state = wait_idle(self.model)
            self.assertEqual(state["results"][-1]["outcome"], "backend_failure")
            self.assertIsNone(state["busy"])
            self.assertEqual(state["source"], "D0Eint(42)")
            controller.backend = RecordingBackend()
            controller.action("interpret")
            self.assertEqual(wait_idle(self.model)["results"][-1]["outcome"], "success")


@override_settings(ALLOWED_HOSTS=["testserver"])
class LifecycleViewTests(SimpleTestCase):
    def setUp(self):
        self.model, self.backend = SourceModel(), RecordingBackend()
        for name, value in (("source_model", self.model), ("language_backend", self.backend)):
            override = patch(f"workbench.views.{name}", value)
            override.start()
            self.addCleanup(override.stop)
        self.model.apply("D0Eint(42)")

    def post(self, command, **values):
        return self.client.post("/api/source/", json.dumps({
            "command": command, "version": self.model.snapshot()["version"], **values,
        }), content_type="application/json")

    def action(self):
        return self.client.post("/api/action/", json.dumps({
            "operation": "interpret", "version": self.model.snapshot()["version"],
        }), content_type="application/json")

    def test_revision_result_metadata_literal_text_and_new_source_clears_output(self):
        text = '<img src=x onerror="alert(1)">\nsecond line\n</script>'
        self.backend.interpret = lambda source: BackendReply(Outcome.SUCCESS, text)
        self.assertEqual(self.action().status_code, 202)
        state = wait_idle(self.model)
        result = state["results"][-1]
        self.assertEqual(result, {"operation": "interpret", "revision": 1,
                                 "outcome": "success", "text": text, "free_variables": None})
        page = self.client.get("/")
        self.assertContains(page, "\\u003Cimg")
        self.assertNotContains(page, text)
        self.assertEqual(self.client.get("/api/source/").json()["state"]["results"][-1]["text"], text)
        self.assertEqual(self.post("apply", source="D0Eint(43)").json()["state"]["results"], [])

    def test_busy_requests_are_rejected_get_remains_responsive_and_retry_works(self):
        self.backend.gate = Event()
        self.backend.fail = True
        try:
            self.assertEqual(self.action().status_code, 202)
            self.assertEqual(self.client.get("/api/source/").json()["state"]["busy"], "interpret")
            for command, values in (("edit", {"source": "new"}), ("apply", {"source": "new"}),
                                    ("discard", {}), ("manual", {}), ("example", {"example": "factorial"})):
                self.assertEqual(self.post(command, **values).status_code, 409)
            upload = self.client.post("/api/source/", {"file": SimpleUploadedFile("new.lambda", b"D0Eint(3)"),
                                                      "version": self.model.snapshot()["version"]})
            self.assertEqual(upload.status_code, 409)
            self.assertEqual(self.action().status_code, 409)
        finally:
            self.backend.gate.set()
        failed = wait_idle(self.model)
        self.assertEqual(failed["results"][-1]["outcome"], "backend_failure")
        self.assertEqual(failed["source"], "D0Eint(42)")
        self.assertEqual(self.action().status_code, 202)
        self.assertEqual(wait_idle(self.model)["results"][-1]["outcome"], "success")

    def test_state_responses_are_not_cached_and_restart_has_new_state_id(self):
        response = self.client.get("/api/source/")
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertNotEqual(response.json()["state"]["state_id"], SourceModel().snapshot()["state_id"])
