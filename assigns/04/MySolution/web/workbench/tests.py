"""F2/F3 state and Django boundary checks; no database or browser required."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from .source import MAX_SOURCE_BYTES, SourceConflict, SourceError, SourceModel


class SourceModelTests(unittest.TestCase):
    def setUp(self):
        self.model = SourceModel()

    def test_initial_typing_apply_and_discard_without_browser(self):
        self.model.edit('D0Eint(42)')
        self.assertTrue(self.model.snapshot()["dirty"])
        self.model.apply('D0Eint(42)')
        self.assertEqual(self.model.snapshot()["revision"], 1)
        self.assertEqual(self.model.require_applied_source(), ('D0Eint(42)', 1))
        self.model.edit('D0Eint(43)')
        self.model.discard()
        self.assertEqual(self.model.snapshot()["draft"], 'D0Eint(42)')
        self.assertEqual(self.model.snapshot()["revision"], 1)

    def test_manual_blank_editor_keeps_previous_applied_source(self):
        self.model.load("old.lambda", 'D0Eint(1)')
        self.model.manual()
        state = self.model.snapshot()
        self.assertEqual(state["draft"], "")
        self.assertEqual(state["source"], 'D0Eint(1)')
        self.assertTrue(state["dirty"])
        with self.assertRaises(SourceError):
            self.model.apply("")
        self.model.discard()
        self.assertEqual(self.model.snapshot()["draft_name"], "old.lambda")

    def test_dirty_state_blocks_source_replacement_and_tools(self):
        self.model.load("old", 'D0Eint(1)')
        self.model.edit('D0Eint(2)')
        for operation in [self.model.manual, self.model.require_applied_source,
                          lambda: self.model.load("new", 'D0Eint(3)')]:
            with self.assertRaises(SourceConflict):
                operation()
        self.assertEqual(self.model.snapshot()["draft"], 'D0Eint(2)')
        self.model.apply('D0Eint(2)')
        self.assertEqual(self.model.snapshot()["revision"], 2)

    def test_rejected_edits_preserve_source_revision_and_text(self):
        self.model.load("old", 'D0Eint(1)')
        for invalid in ["", " \n\t", "x" * (MAX_SOURCE_BYTES + 1), "é" * (MAX_SOURCE_BYTES // 2 + 1)]:
            with self.subTest(length=len(invalid)):
                with self.assertRaises(SourceError):
                    self.model.apply(invalid)
                state = self.model.snapshot()
                self.assertEqual(state["source"], 'D0Eint(1)')
                self.assertEqual(state["source_name"], "old")
                self.assertEqual(state["revision"], 1)
                self.assertEqual(state["draft"], invalid)
                self.assertTrue(state["dirty"])
        self.model.apply('D0Eint(42)')
        self.assertEqual(self.model.snapshot()["revision"], 2)

    def test_utf8_byte_limit_inclusive_and_stale_version_rejected(self):
        self.model.apply("é" * (MAX_SOURCE_BYTES // 2))
        stale = self.model.snapshot()["version"]
        self.model.edit("changed", stale)
        with self.assertRaises(SourceConflict):
            self.model.discard(stale)
        self.assertEqual(self.model.snapshot()["draft"], "changed")

    def test_editing_back_to_applied_text_is_clean(self):
        self.model.load("old", 'D0Eint(1)')
        self.model.edit('D0Eint(2)')
        self.model.edit('D0Eint(1)')
        self.assertFalse(self.model.snapshot()["dirty"])
        self.model.require_applied_source()


@override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"])
class SourceViewTests(SimpleTestCase):
    def setUp(self):
        self.model = SourceModel()
        self.model_patch = patch("workbench.views.source_model", self.model)
        self.model_patch.start()
        self.addCleanup(self.model_patch.stop)

    def post(self, command, **values):
        return self.client.post("/api/source/", data=json.dumps({
            "command": command, "version": self.model.snapshot()["version"], **values,
        }), content_type="application/json")

    def upload(self, contents, name="uploaded.lambda"):
        return self.client.post("/api/source/", {
            "file": SimpleUploadedFile(name, contents, content_type="text/plain"),
            "version": self.model.snapshot()["version"],
        })

    def test_page_has_edit_controls_csrf_and_literal_initial_source(self):
        self.model.apply('D0Evar("</script><img src=x onerror=alert(1)>")')
        page = self.client.get("/")
        self.assertContains(page, "Apply changes")
        self.assertContains(page, "Discard changes")
        self.assertContains(page, "csrfmiddlewaretoken")
        self.assertContains(page, "\\u003C/script\\u003E")
        self.assertNotContains(page, "<img src=x onerror=alert(1)>")

    def test_manual_entry_apply_replacement_edit_and_discard(self):
        self.assertEqual(self.post("edit", source='D0Eint(42)').status_code, 200)
        self.assertEqual(self.post("apply", source='D0Eint(42)').json()["state"]["revision"], 1)
        self.post("edit", source='D0Eint(43)')
        self.assertEqual(self.post("discard").json()["state"]["draft"], 'D0Eint(42)')
        self.assertEqual(self.post("example", example="factorial").json()["state"]["revision"], 2)
        self.post("manual")
        self.assertEqual(self.model.snapshot()["draft"], "")
        self.post("apply", source='D0Eint(7)')
        self.assertEqual(self.model.snapshot()["source_name"], "Manual input")

    def test_dirty_requests_cannot_bypass_disabled_controls(self):
        self.post("example", example="factorial")
        self.post("edit", source='D0Evar("draft")')
        for command, values in [("manual", {}), ("example", {"example": "fibonacci"})]:
            self.assertEqual(self.post(command, **values).status_code, 409)
        self.assertEqual(self.upload(b'D0Eint(3)').status_code, 409)
        for op in ("lint", "interpret", "typecheck", "compile", "execute"):
            response = self.client.post("/api/action/", json.dumps({
                "operation": op, "version": self.model.snapshot()["version"],
            }), content_type="application/json")
            self.assertEqual(response.status_code, 409)
        self.assertEqual(self.model.snapshot()["draft"], 'D0Evar("draft")')

    def test_blank_and_oversized_edits_are_retained_for_correction(self):
        self.post("apply", source='D0Eint(42)')
        for invalid in ["", "  \n", "x" * 65537, "é" * 32769]:
            response = self.post("apply", source=invalid)
            self.assertEqual(response.status_code, 400)
            state = response.json()["state"]
            self.assertEqual(state["source"], 'D0Eint(42)')
            self.assertEqual(state["revision"], 1)
            self.assertEqual(state["draft"], invalid)
        self.assertEqual(self.post("apply", source='D0Eint(43)').json()["state"]["revision"], 2)

    def test_rejected_uploads_keep_applied_source_and_editable_preview(self):
        self.post("apply", source='D0Eint(42)')
        for invalid in [b"", b" \n", b"D0Evar('\xff')", b"x" * 65537]:
            response = self.upload(invalid, "rejected.lambda")
            self.assertEqual(response.status_code, 400)
            state = response.json()["state"]
            self.assertEqual(state["source"], 'D0Eint(42)')
            self.assertEqual(state["revision"], 1)
            self.assertTrue(state["dirty"])
            self.assertEqual(state["draft"], invalid.decode("utf-8", errors="replace"))
            self.post("discard")

    def test_invalid_utf8_cannot_be_applied_unchanged_then_correction_succeeds(self):
        self.post("apply", source='D0Eint(42)')
        rejected = self.upload(b"D0Evar('\xff')").json()["state"]["draft"]
        self.assertEqual(self.post("apply", source=rejected).status_code, 400)
        self.assertEqual(self.post("apply", source='D0Evar("fixed")').status_code, 200)
        self.assertEqual(self.model.snapshot()["revision"], 2)

    def test_uploaded_copy_changes_without_writing_a_local_file(self):
        original = b'D0Eint(7)'
        with TemporaryDirectory() as directory:
            local_file = Path(directory) / "uploaded.lambda"
            local_file.write_bytes(original)
            self.assertEqual(self.upload(local_file.read_bytes(), local_file.name).status_code, 200)
            self.post("apply", source='D0Eint(8)')
            self.assertEqual(self.model.snapshot()["source"], 'D0Eint(8)')
            self.assertEqual(local_file.read_bytes(), original)
            self.assertEqual(self.model.snapshot()["source_name"], "uploaded.lambda")

    def test_transport_limit_preserves_applied_state(self):
        self.post("apply", source='D0Eint(42)')
        response = self.post("edit", source="x" * (2 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["state"]["source"], 'D0Eint(42)')
        self.assertEqual(response.json()["state"]["revision"], 1)

    def test_csrf_protection_and_current_state_on_reload(self):
        protected = Client(enforce_csrf_checks=True)
        protected.get("/")
        payload = {"command": "apply", "source": 'D0Eint(42)', "version": 0}
        self.assertEqual(protected.post("/api/source/", json.dumps(payload), content_type="application/json").status_code, 403)
        accepted = protected.post("/api/source/", json.dumps(payload), content_type="application/json",
                                  HTTP_X_CSRFTOKEN=protected.cookies["csrftoken"].value)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(protected.get("/api/source/").json()["state"]["source"], 'D0Eint(42)')

    def test_malformed_request_does_not_mutate_state(self):
        self.assertEqual(self.post("unknown").status_code, 400)
        self.assertEqual(self.post("edit", source=42).status_code, 400)
        self.assertEqual(self.post("edit", source="x", version=True).status_code, 400)
        self.assertEqual(self.client.post("/api/source/", "not json", content_type="application/json").status_code, 400)
        self.assertEqual(self.model.snapshot()["revision"], 0)
