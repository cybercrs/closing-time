# Closing Time — native browser app

The final student-facing app uses HTML/CSS/JavaScript with no Python interpreter, Streamlit, Pyodide, WebAssembly, runtime package, external asset request, npm runtime dependency, shared storage or new service. Source is isolated in `native/` on `native/html-js`; publication adds only `/js/` to the existing `stlite-browser` branch. Main, the Python/Streamlit implementation, the published stlite root and Pages settings remain unchanged.

## Original lesson and calculations

All twenty reached pages, twenty-one first-pass checkpoints, timing questions, six transaction classifications, four paired account challenges, three statement connections, four integrity judgments, statements, completed accounting equations and final reporting-chain debrief remain. The original renderers export sixty unanswered/wrong/correct variants. The original blue/gold styling and clock tab icon are retained; the icon is a self-contained SVG data asset. No Receivables-specific teaching changes are applied.

An independent native model recalculates adjusted account balances, statement totals, accounting equations, comparison rows and every answer evaluation. Incorrect responses require revision before ordinary Continue actions unlock new pages. Simple/account practice counts every failed recheck; statement practice counts only changed answers, preserving already-correct first-pass flags. Account effects and omissions form one original checkpoint. Final mastery appears inline after the last correct integrity response; it does not add a separate page.

## Review and compatible saving

Subtle boxed Back/Forward controls have accessible native names, keyboard focus and 44px targets. Back renders earned feedback as static content, with no editing, checks, revisions, scoring, reset or new reveals. Earlier integrity pages never switch to the final debrief just because the case is complete. Read-only balance tables retain inspection, expansion and CSV download. Forward stops at the actual current page, including after a correct answer; ordinary validated Continue controls earn the next page. Engine guards enforce the same limits independently of the UI.

Original compressed version-4 `progress` links remain compatible for ordinary saved work in both directions. To use an old Python/stlite bookmark, retain its query parameters and change only the path to `/closing-time/js/`. Seeds retain all 63 integer bits through parsing, hashing and serialization. Account-effect/omission orders reproduce Python SHA-256 seeding, MT19937 shuffle and its unchanged-order rotation exactly. Recognition/classification/statement/integrity choices retain their original, unshuffled order.

Answers, current drafts, first-pass flags, attempts, viewed page and earned position survive refresh/bookmarks. Additional query values and fragments remain. No identity, free text, localStorage, sessionStorage or central score store is introduced. Independent sessions share no storage. Start over returns to a fresh briefing and leaves older copied bookmarks intact.

The original validator caps saved attempts at 99, although live repeated practice can exceed that limit. Native practice preserves the full original scoring history and upgrades only an overflow snapshot to native version 5. Native v5 links refresh and resume in this JavaScript app; the old Python/stlite app cannot restore v5. Ordinary links remain original v4, and reset starts v4 again. No counter is truncated or silently reset.

The account comparison retains all original rows, column sorting, keyboard-accessible expansion and CSV download. Narrow tables scroll within a labelled region. The reviewed CSV uses LF line endings for repository readability; the actual download uses standard CRLF and its full content is tested.

## Build and verification

```bash
/workspace/.cloud-setup/venvs/main/bin/python native/export.py
node --test native/tests/*.test.mjs
/workspace/.cloud-setup/venvs/main/bin/python -m unittest discover -s tests -v
/workspace/.cloud-setup/venvs/main/bin/python native/build.py
/workspace/.cloud-setup/venvs/main/bin/python native/tests/browser.py
```

The build copies seven native assets and a hash manifest. `--site-output PATH` writes only `PATH/js/`. Python and Node are development tools; learners download neither. Serve over HTTP(S); `file://` is unsupported. Current ES-module browsers with Web Crypto, BigInt, structured cloning and Compression Streams are required. Chromium is tested; other browsers and physical devices remain unmeasured.

Screenshots, original/native snapshots, calculation/shuffle parity, browser results, final metadata QA and source-protection evidence are in `review/` and `VALIDATION.md`. Publication checks exact source/static refs, every unchanged non-js static blob and successful Pages deployment. The known hosted proxy denial is respected without an alternate route. Local measurements do not promise hosted/network speed or classroom capacity.
