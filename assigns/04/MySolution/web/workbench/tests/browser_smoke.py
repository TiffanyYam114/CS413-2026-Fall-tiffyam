"""Exercise the Django page in a real browser, using an isolated local server."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from socketserver import ThreadingMixIn
from threading import Thread
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parent


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="chrome", help="chrome, msedge, or chromium (requires Playwright browser installation)")
    args = parser.parse_args()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.contrib.staticfiles.handlers import StaticFilesHandler
    from django.core.wsgi import get_wsgi_application
    from playwright.sync_api import expect, sync_playwright
    from workbench import views
    from workbench.backend import LambdaBackend
    from workbench.examples import EXAMPLES
    from workbench.source import SourceModel
    from workbench.tools import BackendReply, Outcome

    views.source_model = SourceModel()
    views.language_backend = LambdaBackend()
    server = make_server("127.0.0.1", 0, StaticFilesHandler(get_wsgi_application()),
                         server_class=ThreadedServer, handler_class=QuietHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    artifacts = ROOT / "test-artifacts"
    artifacts.mkdir(exist_ok=True)
    records = []
    browser_version = None

    def record(identifier, observed):
        records.append({"check": identifier, "observed": observed, "outcome": "passed"})
        print(f"PASS {identifier}: {observed}", flush=True)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel=args.channel, headless=True)
            browser_version = browser.version
            print(f"Browser: {browser_version}", flush=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            exceptions = []
            page.on("pageerror", lambda error: exceptions.append(str(error)))
            page.goto(url)
            editor = page.locator("#source-editor")
            menu = page.locator("#source-menu")
            status = page.locator("#source-status")
            results = page.locator("#tool-results")
            error = page.locator("#source-error")

            def ready():
                expect(editor).to_be_enabled(timeout=15000)
                expect(page.locator('[data-operation="lint"]')).to_be_enabled(timeout=15000)
                expect(page.locator("main")).to_have_attribute("aria-busy", "false")

            def state():
                return page.request.get(url + "/api/source/").json()["state"]

            def apply(source):
                editor.fill(source)
                page.get_by_role("button", name="Apply changes", exact=True).click()
                ready()
                assert state()["source"] == source

            def action(label, outcome, text):
                count = results.locator(".tool-result").count()
                page.get_by_role("button", name=label, exact=True).click()
                expect(results.locator(".tool-result")).to_have_count(count + 1, timeout=15000)
                ready()
                expect(results.locator(".tool-result").last.locator("h3")).to_contain_text(outcome)
                expect(results.locator(".tool-result").last.locator("pre")).to_contain_text(text)

            def upload(path_or_payload):
                with page.expect_file_chooser() as chooser:
                    menu.select_option("file")
                chooser.value.set_files(path_or_payload)

            expect(editor).to_be_enabled()
            assert page.locator("[data-operation]").all_text_contents() == ["Lint", "Interpret", "Type-check", "Compile", "Execute"]
            for button in page.locator("[data-operation]").all():
                expect(button).to_be_disabled()
            apply('D0Eop2("+", D0Eint(20), D0Eint(22))')
            action("Interpret", "success", "D0Vint(arg1=42)")
            record("B1", "Initial typing without upload applies revision 1; action order is correct; real arithmetic returns 42.")

            menu.select_option("manual")
            expect(editor).to_have_value("")
            apply('D0Evar("x")')
            action("Lint", "language error", "Undeclared variables: 'x'")
            editor.fill('D0Eint(42)')
            expect(menu).to_be_disabled()
            for button in page.locator("[data-operation]").all():
                expect(button).to_be_disabled()
            page.get_by_role("button", name="Discard changes", exact=True).click()
            expect(editor).to_have_value('D0Evar("x")')
            apply('D0Eint(42)')
            expect(results.locator(".tool-result")).to_have_count(0)
            action("Lint", "success", "No free variables")
            record("B2", "Manual input is blank; dirty edits block source/tools; Discard restores text; closed Lint succeeds and accepted edits clear output.")

            for example, expected in (("factorial", 120), ("fibonacci", 55)):
                previous_revision = state()["revision"]
                menu.select_option(example)
                expect(page.locator("#source-name")).to_contain_text(example.title())
                ready()
                assert state()["revision"] == previous_revision + 1
                expect(results.locator(".tool-result")).to_have_count(0)
                action("Interpret", "success", f"D0Vint(arg1={expected})")
            record("B3", "Factorial and Fibonacci selections increment revision, clear output, and evaluate to 120 and 55.")

            local_file = artifacts / "upload.lambda"
            original = 'D0Eint(7)\n'
            local_file.write_text(original, encoding="utf-8")
            previous_revision = state()["revision"]
            upload(str(local_file))
            expect(page.locator("#source-name")).to_contain_text("upload.lambda")
            ready()
            assert state()["revision"] == previous_revision + 1
            expect(results.locator(".tool-result")).to_have_count(0)
            apply('D0Eint(8)')
            assert local_file.read_text(encoding="utf-8") == original
            action("Interpret", "success", "D0Vint(arg1=8)")
            before = state()
            editor.fill(" \n")
            page.get_by_role("button", name="Apply changes", exact=True).click()
            expect(error).to_contain_text("cannot be empty")
            expect(editor).to_have_value(" \n")
            after = state()
            for field in ("source", "source_name", "revision", "results", "artifact_available"):
                assert before[field] == after[field]
            editor.fill("x" * 65537)
            page.get_by_role("button", name="Apply changes", exact=True).click()
            expect(error).to_contain_text("65536-byte")
            expect(editor).to_have_value("x" * 65537)
            page.get_by_role("button", name="Discard changes", exact=True).click()
            ready()
            record("B4", "Choose File increments revision; applied edits preserve the original file; rejected blank/oversized edits retain previous results and revision.")

            before = state()
            upload({"name": "invalid.lambda", "mimeType": "text/plain", "buffer": b"D0Evar('\xff')"})
            expect(error).to_contain_text("not valid UTF-8")
            assert "\ufffd" in editor.input_value()
            for field in ("source", "source_name", "revision", "results"):
                assert state()[field] == before[field]
            page.get_by_role("button", name="Discard changes", exact=True).click()
            ready()
            record("B5", "Invalid UTF-8 upload is rejected with an editable preview; applied source and results survive and Discard recovers.")

            apply('D0Eop2("/", D0Eint(1), D0Eint(0))')
            action("Lint", "success", "No free variables")
            action("Interpret", "runtime error", "ZeroDivisionError")
            apply('D0Eint("bad")')
            action("Interpret", "input error", "expects int")
            apply('D0Eint(42)')
            action("Type-check", "not implemented", "Type checking is not yet implemented")
            action("Compile", "not implemented", "Compilation is not yet implemented")
            expect(page.get_by_role("button", name="Execute", exact=True)).to_be_disabled()
            expect(page.locator("#execute-help")).to_contain_text("generated code")
            record("B6", "Lint/runtime differences and input diagnostics are visible; placeholders have not-implemented outcomes; Execute stays disabled.")

            html = '<img src=x onerror="window.__injected=1">'
            source = f"D0Evar({html!r})"
            apply(source)
            action("Lint", "language error", html)
            expect(editor).to_have_value(source)
            assert results.locator("img").count() == 0
            assert page.evaluate("window.__injected") is None

            class LiteralBackend(LambdaBackend):
                def interpret(self, source):
                    return BackendReply(Outcome.SUCCESS, html + '\nsecond line\n<script>window.__injected=1</script>')

            # Inject output only to exercise rendering; other evaluation checks use lambda1.
            views.language_backend = LiteralBackend()
            action("Interpret", "success", "second line")
            output = results.locator(".tool-result").last.locator("pre")
            assert output.text_content() == html + '\nsecond line\n<script>window.__injected=1</script>'
            assert output.evaluate("node => getComputedStyle(node).whiteSpace") == "pre-wrap"
            assert results.locator("img, script").count() == 0
            assert page.evaluate("window.__injected") is None
            assert "Revision " + str(state()["revision"]) in results.locator(".tool-result").last.locator("h3").inner_text()
            page.screenshot(path=str(artifacts / "literal-output.png"), full_page=True)
            views.language_backend = LambdaBackend()
            record("B7", "HTML-like source/output stays literal, multiline output keeps line breaks, and action/revision/outcome metadata is shown.")

            slow = EXAMPLES["fibonacci"][1].replace("D0Eint(10)\n)", "D0Eint(35)\n)")
            apply(slow)
            page.get_by_role("button", name="Interpret", exact=True).click()
            expect(status).to_contain_text("Busy: Interpret", timeout=2000)
            for control in (editor, menu, page.locator("#source-file"), page.locator("#source-apply"), page.locator("#source-discard")):
                expect(control).to_be_disabled()
            for button in page.locator("[data-operation]").all():
                expect(button).to_be_disabled()
            expect(page.locator("main")).to_have_attribute("aria-busy", "true")
            current = state()
            assert current["busy"] == "interpret"
            conflict = page.request.post(url + "/api/source/", data=json.dumps({
                "command": "edit", "source": "conflicting edit", "version": current["version"],
            }), headers={"Content-Type": "application/json", "X-CSRFToken": page.locator('[name="csrfmiddlewaretoken"]').input_value()})
            assert conflict.status == 409
            assert page.evaluate("new Promise(resolve => setTimeout(() => resolve('responsive'), 25))") == "responsive"
            page.screenshot(path=str(artifacts / "busy.png"), full_page=True)
            ready()
            expect(results.locator(".tool-result").last).to_contain_text("backend failure")
            expect(results.locator(".tool-result").last).to_contain_text("worker limit")
            expect(editor).to_have_value(slow)
            record("B8", "Real interpreter timeout shows busy text, disables conflicting controls, rejects direct edits, keeps the page responsive, preserves source, and restores controls.")

            class FailOnceBackend(LambdaBackend):
                def __init__(self):
                    super().__init__()
                    self.fail = True

                def interpret(self, source):
                    if self.fail:
                        self.fail = False
                        raise OSError("Injected backend failure")
                    return super().interpret(source)

            views.language_backend = FailOnceBackend()
            apply('D0Eint(42)')
            before = state()
            action("Interpret", "backend failure", "Injected backend failure")
            action("Interpret", "success", "D0Vint(arg1=42)")
            assert state()["source"] == before["source"]
            assert state()["revision"] == before["revision"]
            views.language_backend = LambdaBackend()
            record("B9", "Injected backend failure preserves source/revision and restores controls; retry of unchanged source uses real evaluation and succeeds.")

            def lose_response(route):
                route.fetch()  # The server accepts the action, but its response is lost.
                route.abort("failed")

            count = results.locator(".tool-result").count()
            page.route("**/api/action/", lose_response)
            page.get_by_role("button", name="Interpret", exact=True).click()
            expect(status).to_contain_text("Checking server state", timeout=3000)
            ready()
            page.unroute("**/api/action/", lose_response)
            expect(results.locator(".tool-result")).to_have_count(count + 1)
            expect(results.locator(".tool-result").last).to_contain_text("D0Vint(arg1=42)")
            expect(error).to_be_hidden()
            record("B10", "A lost POST response triggers state reconciliation; the completed result appears and controls recover without submitting a duplicate action.")

            page.reload()
            ready()
            expect(editor).to_have_value('D0Eint(42)')
            expect(results.locator(".tool-result")).to_have_count(count + 1)
            editor.focus()
            page.keyboard.press("Tab")
            assert page.locator(":focus").get_attribute("data-operation") == "lint"
            page.keyboard.press("Enter")
            expect(results.locator(".tool-result")).to_have_count(count + 2, timeout=10000)
            ready()
            assert not exceptions, exceptions
            record("B11", "Reload restores current source/results; keyboard activation works; no uncaught JavaScript errors occurred.")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        (artifacts / "browser-results.json").write_text(json.dumps({
            "time_utc": datetime.now(timezone.utc).isoformat(), "browser_version": browser_version,
            "checks": records,
        }, indent=2), encoding="utf-8")
    print(f"Browser smoke: {len(records)}/11 checks passed", flush=True)


if __name__ == "__main__":
    main()
