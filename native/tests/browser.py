"""Full local native Chromium QA at the actual project-prefixed /js/ path."""
from __future__ import annotations

import json
import re
import statistics
import sys
import threading
import time
import traceback
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from closing_time.progress import decode_snapshot, encode_state, score_summary, activity_defaults
from closing_time import case_data as case, engine  # noqa: E402

NATIVE = ROOT / "native"
RESULTS = NATIVE / "test-results"
PREFIX = "/closing-time/js/"
RESULTS.mkdir(exist_ok=True)
ORACLE = json.loads((NATIVE / "tests/python-oracles.json").read_text())
LEGACY = json.loads((NATIVE / "tests/legacy-links.json").read_text())
checks, requests, external, errors, console_errors = [], [], [], [], []


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        requests.append(path)
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        elif path.startswith(PREFIX):
            self.path = path[len(PREFIX) - 1:]
            super().do_GET()
        else:
            self.send_error(404)


def passed(name):
    checks.append({"name": name, "status": "passed"})
    print("PASSED:", name, flush=True)


def main():
    import base64
    import csv
    import hashlib
    import random
    import zlib
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(NATIVE / "dist")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = "http://127.0.0.1:" + str(server.server_port)
    url = origin + PREFIX
    result = {"url": url, "conditions": "Actual native Chromium at /closing-time/js/; external requests blocked."}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="/usr/bin/chromium", headless=True,
            proxy={"server": "http://127.0.0.1:9", "bypass": "127.0.0.1,localhost"})
        def attach(context):
            def route(route):
                if route.request.url.startswith(origin):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()
            context.route("**/*", route)
            def events(page):
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            context.on("page", events)
        context = browser.new_context(viewport={"width": 1280, "height": 960}, accept_downloads=True)
        attach(context)
        page = context.new_page()
        def loaded(view=None):
            page.wait_for_function("document.documentElement.dataset.ready==='true'&&document.documentElement.dataset.saving==='false'")
            if view is not None:
                page.wait_for_function("v=>document.documentElement.dataset.view===String(v)", arg=view)
            expect(page).to_have_title("Closing Time")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            assert not re.search(r"\b(?:pilot|preview|test(?:ing)?\s+(?:app|version|site))\b", page.locator("body").inner_text(), re.I)
        def go(address=url, view=None):
            page.goto(address, wait_until="networkidle")
            loaded(view)
        def raw():
            token = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["progress"][0]
            return json.loads(zlib.decompress(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))))
        def state():
            value = decode_snapshot(urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["progress"][0])
            assert value is not None
            return value
        def button(label):
            page.get_by_role("button", name=label, exact=True).click()
            loaded()
        def radio(key, value):
            page.locator("input[name=" + json.dumps(key) + "][value=" + json.dumps(value) + "]").check()
            loaded()
        def shot(name):
            page.screenshot(path=str(RESULTS / (name + ".png")), full_page=True)
        def simple(items, prefix, label, wrong=False):
            for index, item in enumerate(items):
                options = case.CLASSIFICATION_OPTIONS if prefix == "classification" else item.options
                correct = item.classification if prefix == "classification" else item.correct
                if wrong and index == 0:
                    radio("widget_" + prefix + "_" + item.id, next(value for value in options if value != correct))
                    button(label)
                    expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
                    expect(page.get_by_role("button", name="Continue", exact=True)).to_have_count(0)
                    revised = "Check revised judgment" if prefix == "integrity" else "Check revised answer"
                    if prefix == "recognition":
                        button(revised)
                        assert state()["ct_attempts"]["recognition:" + item.id] == 2
                    radio("widget_" + prefix + "_" + item.id, correct)
                    button(revised)
                else:
                    radio("widget_" + prefix + "_" + item.id, correct)
                    button(label)
                if prefix == "integrity" and index == len(items) - 1:
                    expect(page.locator("#lesson")).to_contain_text("Close complete.")
                else:
                    button("Continue")
        def account_stage(wrong=False):
            seed = state()["ct_shuffle_seed"]
            for index, item in enumerate(case.ACCOUNT_CHALLENGES):
                for field in ("effect", "omission"):
                    options = list(getattr(item, field + "_options"))
                    digest = hashlib.sha256(f"{seed}:account-{field}:{item.id}".encode()).digest()
                    rng = random.Random(int.from_bytes(digest[:8], "big"))
                    expected_order = options.copy()
                    rng.shuffle(expected_order)
                    if expected_order == options:
                        expected_order = expected_order[1:] + expected_order[:1]
                    key = "widget_" + field + "_" + item.id
                    assert page.locator("input[name=" + json.dumps(key) + "]").evaluate_all("nodes=>nodes.map(node=>node.value)") == expected_order
                if wrong and index == 0:
                    radio("widget_effect_" + item.id, next(value for value in item.effect_options if value != item.correct_effect))
                    radio("widget_omission_" + item.id, item.correct_omission)
                    button("Check the account ripple")
                    expect(page.locator("#lesson")).to_contain_text("Account directions - Review")
                    expect(page.locator("#lesson")).to_contain_text("Omission effect - Correct")
                    radio("widget_effect_" + item.id, item.correct_effect)
                    button("Check revised account analysis")
                else:
                    radio("widget_effect_" + item.id, item.correct_effect)
                    radio("widget_omission_" + item.id, item.correct_omission)
                    button("Check the account ripple")
                button("Continue")
        def statement_stage(wrong=False):
            for index, item in enumerate(case.STATEMENT_QUESTIONS):
                value = next(value for value in item.options if value != item.correct) if wrong and index == 0 else item.correct
                radio("widget_statement_" + item.id, value)
            button("Check the statement connections")
            if wrong:
                before = state()["ct_attempts"].copy()
                button("Check revised reasoning")
                assert state()["ct_attempts"] == before
                item = case.STATEMENT_QUESTIONS[0]
                radio("widget_statement_" + item.id, item.correct)
                revised_url = page.url
                page.reload()
                loaded(15)
                expect(page.locator("input[name=" + json.dumps("widget_statement_" + item.id) + "][value=" + json.dumps(item.correct) + "]")).to_be_checked()
                assert page.url == revised_url
                button("Check revised reasoning")
                for item in case.STATEMENT_QUESTIONS[1:]:
                    assert state()["ct_attempts"]["statement:" + item.id] == 1
            expect(page.locator("#lesson")).to_contain_text("Completed statements")
            button("Continue to the integrity review")
        try:
            go(view=0)
            expect(page.get_by_role("button", name="Back", exact=True)).to_be_disabled()
            expect(page.get_by_role("button", name="Forward", exact=True)).to_be_disabled()
            assert page.locator(".hero").evaluate("el=>getComputedStyle(el).backgroundImage") != "none"
            shot("brief-desktop")
            button("Begin the close")
            loaded(1)
            button("Check the reporting period")
            expect(page.get_by_role("alert")).to_contain_text("Choose a response")
            first = case.RECOGNITION_QUESTIONS[0]
            radio("widget_recognition_" + first.id, first.correct)
            expect(page.get_by_role("alert")).to_have_count(0)
            draft_url = page.url
            before = state()
            button("Back")
            loaded(0)
            assert state() == before
            expect(page.locator("#lesson input,#lesson button")).to_have_count(0)
            expect(page.locator("#reset")).to_be_disabled()
            button("Forward")
            loaded(1)
            page.reload()
            loaded(1)
            assert page.url == draft_url and state() == before
            expect(page.locator('input[name="widget_recognition_' + first.id + '"][value=' + json.dumps(first.correct) + "]")).to_be_checked()
            passed("Original styling/title, required answer, draft review/refresh, readonly briefing and current-step Forward stop")

            simple(case.RECOGNITION_QUESTIONS, "recognition", "Check the reporting period", True)
            loaded(5)
            simple(case.ADJUSTMENT_ITEMS, "classification", "Identify the transaction", True)
            loaded(11)
            account_stage(True)
            loaded(15)
            with page.expect_download() as download_info:
                page.get_by_role("button", name="Download table as CSV", exact=True).click()
            download = download_info.value
            assert download.suggested_filename == "closing-time-account-comparison.csv"
            download.save_as(str(RESULTS / "account-comparison.csv"))
            with (RESULTS / "account-comparison.csv").open() as file:
                rows = list(csv.DictReader(file))
            expected_rows = [{"Account": row["Account"], "Unadjusted balance": row["Unadjusted"], "Adjusted balance": row["Adjusted"]} for row in engine.balance_rows()]
            assert rows == expected_rows
            page.get_by_role("button", name="Expand table", exact=True).click()
            expect(page.get_by_role("dialog")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.get_by_role("dialog")).to_have_count(0)
            expect(page.get_by_role("button", name="Expand table", exact=True)).to_be_focused()
            statement_stage(True)
            loaded(16)
            simple(case.INTEGRITY_SCENARIOS, "integrity", "Evaluate the proposal", True)
            loaded(19)
            expected = {"correct": 16, "attempted": 21, "total": 21, "revisions": 6}
            assert score_summary(state()) == expected
            expect(page.locator("#lesson")).to_contain_text("First-pass decisions: 16 of 21 | Practice revisions used: 6 | Final mastery: complete")
            completed_url = page.url
            result["completion_bookmark"] = completed_url
            shot("completed-desktop")
            passed("Full twenty-page close: wrong/repeated timing, classification, mixed account feedback, statement revisions and integrity mastery")
            passed("Original balance comparison CSV, keyboard table expansion, exact account permutations and first-pass/revision totals")

            before = state()
            allowed = {"Account", "Unadjusted balance", "Adjusted balance", "Expand table", "Download table as CSV"}
            for view in range(18, -1, -1):
                button("Back")
                loaded(view)
                assert state() == before
                expect(page.locator("#lesson input,#lesson select,#lesson textarea")).to_have_count(0)
                expect(page.locator("#reset")).to_be_disabled()
                assert set(page.locator("#lesson button").all_text_contents()).issubset(allowed)
                if view >= 16:
                    expect(page.locator("#lesson")).not_to_contain_text("Close complete.")
                if view == 15:
                    shot("review-statements-desktop")
            forward = page.get_by_role("button", name="Forward", exact=True)
            forward.focus()
            page.keyboard.press("Tab")
            page.keyboard.press("Shift+Tab")
            expect(forward).to_be_focused()
            assert forward.evaluate("el=>el.matches(':focus-visible')&&getComputedStyle(el).outlineWidth==='2px'")
            page.keyboard.press("Enter")
            loaded(1)
            for view in range(2, 20):
                button("Forward")
                loaded(view)
                assert state() == before
            expect(forward).to_be_disabled()
            review_url = completed_url.replace("view=19", "view=3")
            go(review_url, 3)
            page.reload()
            loaded(3)
            assert state() == before
            go(completed_url.replace("view=19", "view=999"), 19)
            assert state() == before
            passed("Every older page strictly readonly; no premature integrity debrief; keyboard/focus, repeated review, bookmarks and future rejection")

            for width in (900, 390):
                page.set_viewport_size({"width": width, "height": 844})
                go(completed_url, 19)
                shot("completed-" + str(width))
                for label in ("Back", "Forward"):
                    box = page.get_by_role("button", name=label, exact=True).bounding_box()
                    assert box["width"] >= 44 and box["height"] >= 44 and box["x"] + box["width"] <= width
                go(completed_url.replace("view=19", "view=15"), 15)
                if width == 390:
                    assert page.locator(".table-wrap").evaluate("el=>el.scrollWidth>el.clientWidth")
                shot("statement-review-" + str(width))
            page.set_viewport_size({"width": 1280, "height": 960})
            go(completed_url, 19)
            page.locator("#reset").click()
            loaded(0)
            assert state()["ct_attempts"] == {}
            independent = browser.new_context()
            attach(independent)
            other = independent.new_page()
            other.goto(url, wait_until="networkidle")
            other.wait_for_function("document.documentElement.dataset.ready==='true'")
            assert other.locator("html").get_attribute("data-reached") == "0"
            go(completed_url, 19)
            assert other.locator("html").get_attribute("data-reached") == "0"
            independent.close()
            passed("1280/900/390px layouts, 44px arrows, table scrolling, reset and independent contexts with old bookmarks retained")

            for fixture in LEGACY:
                position = fixture["position"]
                view = next(index for index, item in enumerate(LEGACY) if item["position"] == position)
                address = url + "?progress=" + fixture["token"] + "&view=" + str(view) + "&tag=a%20b&tag=c%2Fd#saved"
                go(address, view)
                assert raw() == json.loads(fixture["wire"])
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
                assert query["tag"] == ["a b", "c/d"] and urllib.parse.urlsplit(page.url).fragment == "saved"
            max_seed = next(entry for entry in ORACLE["snapshots"] if entry["position"] == {"stage": 3, "index": 0} and entry["status"] == "unanswered")
            go(url + "?progress=" + max_seed["token"], 11)
            assert state()["ct_shuffle_seed"] == 2**63 - 1
            item = case.ACCOUNT_CHALLENGES[0]
            for field in ("effect", "omission"):
                options = list(getattr(item, field + "_options"))
                rng = random.Random(int.from_bytes(hashlib.sha256(f"{2**63 - 1}:account-{field}:{item.id}".encode()).digest()[:8], "big"))
                expected_order = options.copy()
                rng.shuffle(expected_order)
                if expected_order == options:
                    expected_order = expected_order[1:] + expected_order[:1]
                assert page.locator("input[name=" + json.dumps("widget_" + field + "_" + item.id) + "]").evaluate_all("nodes=>nodes.map(node=>node.value)") == expected_order
            go(url + "?progress=bad!&view=999", 0)
            expect(page.locator("#lesson")).to_contain_text("This saved link could not be restored")
            passed("All twenty legacy page bookmarks, exact 63-bit seeds, original/native tokens, extra query values and malformed links")

            go(view=0)
            button("Begin the close")
            simple(case.RECOGNITION_QUESTIONS, "recognition", "Check the reporting period")
            simple(case.ADJUSTMENT_ITEMS, "classification", "Identify the transaction")
            account_stage()
            statement_stage()
            simple(case.INTEGRITY_SCENARIOS, "integrity", "Evaluate the proposal")
            loaded(19)
            assert score_summary(state()) == {"correct": 21, "attempted": 21, "total": 21, "revisions": 0}
            page.locator("#lesson").get_by_role("button", name="Start over", exact=True).click()
            loaded(0)
            passed("Second complete perfect close: 21/21 first pass, no revisions and final inline reset")

            boundary = activity_defaults()
            boundary.update(ct_stage=1, ct_shuffle_seed=42)
            item = case.RECOGNITION_QUESTIONS[0]
            wrong = next(value for value in item.options if value != item.correct)
            boundary["ct_recognition_responses"][item.id] = wrong
            boundary["ct_drafts"]["recognition"][item.id] = wrong
            boundary["ct_attempts"]["recognition:" + item.id] = 99
            boundary["ct_first_pass"]["recognition:" + item.id] = False
            go(url + "?progress=" + encode_state(boundary), 1)
            assert raw()["v"] == 4
            button("Check revised answer")
            assert raw()["v"] == 5 and raw()["at"]["recognition:" + item.id] == 100
            overflow_url = page.url
            page.reload()
            loaded(1)
            assert page.url == overflow_url and raw()["at"]["recognition:" + item.id] == 100
            assert raw()["fp"]["recognition:" + item.id] is False
            page.locator("#reset").click()
            loaded(0)
            assert raw()["v"] == 4
            passed("99-to-100 practice overflow, native-v5 recovery with full history, and reset to ordinary v4")
            timings = []
            for _ in range(5):
                cold = browser.new_context()
                attach(cold)
                fresh = cold.new_page()
                session = cold.new_cdp_session(fresh)
                session.send("Network.enable")
                session.send("Network.setCacheDisabled", {"cacheDisabled": True})
                fresh.goto(url, wait_until="networkidle")
                fresh.wait_for_function("document.documentElement.dataset.ready==='true'")
                timings.append(fresh.evaluate("performance.getEntriesByName('closing-ready')[0].startTime"))
                cold.close()
            result["cold_initialization_ms"] = {"samples": timings, "median": statistics.median(timings),
                "conditions": "Five cache-disabled fresh Chromium contexts on local loopback; not hosted loading or capacity measurements."}
            assert external == errors == console_errors == []
            assert not any(path.endswith((".py", ".whl", ".wasm")) or "/vendor/" in path or "/_stcore/" in path for path in requests)
            passed("Five local cold initializations with no external requests, runtime/package loads, server traffic or browser errors")
        except Exception:
            checks.append({"name": "Browser walkthrough", "status": "failed", "error": traceback.format_exc()})
            page.screenshot(path=str(RESULTS / "failure.png"), full_page=True)
            result["body_on_failure"] = page.locator("body").inner_text()
        browser.close()
    server.shutdown()
    result.update(checks=checks,requests=sorted(set(requests)),external_requests=external,page_errors=errors,console_errors=console_errors,
        saved_link_compatibility="Ordinary native/legacy v4 links interoperate. Only attempt-count overflow above 99 upgrades to native-only v5; old apps cannot restore v5.")
    (RESULTS / "browser-results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k not in ("completion_bookmark","body_on_failure")},indent=2),flush=True)
    return int(any(check["status"] == "failed" for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
