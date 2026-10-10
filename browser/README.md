# Closing Time: browser version

This isolated version executes Python in each learner's browser. It has no Python server, login, database, or central score store. Keep the complete static directory together and serve it over HTTP(S); opening index.html as a local file is unsupported.

The source branch is `rollout/stlite-browser-navigation`; the separate static publishing branch is `stlite-browser`. The live Community Cloud entrypoint, dependencies, theme and server settings remain unchanged on main. Do not merge the migration into main as part of this rollout.

## Build and test

From this repository root in the saved Accounting Teaching Apps environment:

```bash
/workspace/.cloud-setup/venvs/main/bin/python -m unittest discover -s tests -v
/workspace/.cloud-setup/venvs/main/bin/python -m browser.build
/workspace/.cloud-setup/venvs/main/bin/python -m browser.test_browser
```

The optional cached build flags are `--runtime-archive /tmp/assigned-runtime-cache/runtime.tgz --asset-cache /tmp/assigned-runtime-cache`. All inputs are hash-checked even when cached. Playwright and `/usr/bin/chromium` are local development tools only. Build output is `browser/dist`; fresh evidence is `browser/test-results`. Reviewed evidence is retained in `browser/validation`.

The build reuses Dock to Dollar source commit `8a0f25a2bff6f9f1eacbc8ab132ababc94974c87`: stlite 1.8.1, its patched Streamlit 1.57.0, Pyodide 0.29.3 and locally packaged, hash-verified wheels/assets. Server Streamlit 1.60.0 is never installed into stlite. The declaration extraction fails if it cannot uniquely locate the original initialization driver. Root packages are placed ahead of the browser entrypoint directory to prevent module-name collisions. A dedicated worker per browser page isolates sessions.

## Progress and review

The compact boxed Back/Forward arrows have native accessible labels, visible keyboard focus and 44px touch targets. Back only changes the viewed page. A private state copy renders earlier work as static text, with no answer controls, submit actions, hint/reveal actions or reset controls. Forward visits reached pages and stops at the actual current page. Existing activity controls earn new pages.

Each recognition, classification, account, and integrity decision has its own review page; the statement questions stay together. The original blue/gold lesson styling is retained. The native sidebar opener stays visible with a 44px target, so Start over remains accessible after the original toolbar CSS is applied. The original final integrity response opens the debrief on the final page. Earlier integrity review cannot switch to the completed-case renderer or change first-pass scores.

Browser fields outside forms transmit draft changes on change while retaining explicit submission. Widget values are retained before rendering on each rerun, without relying on newer Streamlit persist_state APIs. Canonical URL snapshots retain the original validation and scoring rules; the separate `view` parameter is clamped to reached pages. Refresh and bookmarks reconstruct progress and review position. URL progress remains a learner-controlled recovery mechanism, not an authenticated grade record.

## Loading recovery

Startup is local to each browser. A visible loading notice offers **Retry loading** after 60 seconds or a loading error. Retrying reloads the current address and retains its complete progress and view parameters; it never clears or reconstructs saved work. Local startup times varied during concurrent headless tests, so the final Wasm checks run serially. No speculative runtime timer or vendor patch is retained.

## GitHub Pages activation

GitHub reported `has_pages: false` before rollout. The available connected tools cannot configure Pages. In this repository: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: stlite-browser → Folder: / (root) → Save**. Verify the subsequent Pages build/deployment before sharing its URL. The static branch contains `.nojekyll` and preserves subdirectory asset paths. Do not replace an existing Pages site if one appears meanwhile.

The cloud proxy restriction on cybercrs.github.io remains respected. Hosted browser testing is not claimed. Local walkthroughs establish functionality, not classroom capacity; no concurrency claim is made for 40–45 or 80–135 students. Initial visits download about 57 MB of runtime files; local transfer timings are not public-site performance estimates.
