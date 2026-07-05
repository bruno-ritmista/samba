# Make sheets_to_banana ready for a wider audience

## Context

`sheets_to_banana` is about to be shared with a larger group of samba
musicians/arrangers. Today it has two usage paths — a Google Colab notebook
(no install) and a local CLI (Python/git/pip) — but almost no onboarding
material: no prerequisites list, no FAQ/troubleshooting, generic error
messages that don't tell the user what actually went wrong, and a couple of
typos/broken links in the README. Users will use the tool **independently,
with no peer support**, so anything that isn't self-explanatory in the docs
or the tool's own output becomes a dead end for them.

Decisions from the interview that shape this plan:
- **Colab is the primary path**, CLI is secondary/advanced (for tech-savvy users).
- Audience splits cleanly: non-technical users → Colab only; tech-savvy users → Colab + CLI. No cross-user support.
- Fix **both** the code's error messages *and* write an FAQ — not one or the other.
- FAQ lives as **`FAQ.md` on GitHub**; the Colab notebook links to it (not duplicated inline).
- **Text-only** instructions — no screenshots/GIFs.
- Scope is **end-user docs only** — `doc/design-plan.md`, `doc/deployment-plan.md`, `CONTRIBUTING.md` are untouched.
- A template Google Sheet already exists: `https://docs.google.com/spreadsheets/d/1NL_UpLsLf1YSnPphxxP7Mdu-IdTzckSYDjZsCih0LCw/edit?usp=sharing` — link it in the docs.
- **English only** — no translation, matching the existing repo.
- For sheet formatting, tell users to **copy the template and only edit notes/instruments inside it** — no separate "notation format" explainer in the FAQ (avoids duplicating rules the template already encodes).
- No dedicated support channel — the FAQ documents known limitations instead of pointing to a contact/issue queue.

Aside (not part of this task): the `banana-to-pdf` worktree has its own, older/stale
`sheets_to_banana/README.md` on a different branch — unrelated to this work, flagging only for awareness.

## Root cause dug up during review

`fetch_csv` in [fetch.py](../src/fetch.py) has two real weaknesses, not just wording problems:

1. **No timeout** on `requests.get()` — a flaky connection hangs the tool indefinitely instead of failing with a message.
2. **Private/unshared sheets don't raise an HTTP error at all.** Google redirects to a sign-in page and returns **200 OK with an HTML body**, so `raise_for_status()` never fires. The HTML then gets fed to `csv.reader` in [parse.py](../src/parse.py), which produces the unrelated, confusing `"No breaks found in sheet."` — for what is actually the single most common mistake (forgetting to set sharing to "Anyone with the link").

Both the CLI ([__main__.py](../src/__main__.py)) and the Colab notebook ([sheets_to_banana.ipynb](../deployment/sheets_to_banana.ipynb)) currently swallow the real exception and print a static, generic string — so fixing `fetch_csv` alone isn't enough; both call sites need to surface the message it now raises instead of discarding it.

## Changes

### 1. `src/fetch.py` — raise clear, specific errors (root-cause fix, single place)
- Add `timeout=15` to the `requests.get()` call. Catch `requests.exceptions.Timeout` / `ConnectionError` and re-raise as a plain exception with message: `"Could not reach Google Sheets — check your internet connection and try again."`
- After `raise_for_status()`, inspect `response.headers.get("Content-Type", "")`. If it doesn't look like CSV (Google serves `text/html` for the sign-in-redirect case), raise with message: `"This sheet doesn't look public. In Google Sheets: File → Share → General access → 'Anyone with the link'."`
- Extend the existing "Not a valid Google Sheets URL" `ValueError` message with a one-line hint to copy the full link from the browser address bar.
- No new exception classes — plain built-in exceptions with a fully-formed, user-facing message string are enough; callers just display `str(e)`.

### 2. `src/__main__.py` — stop re-wrapping the message
- Change `logger.error("Failed to fetch sheet: %s", e)` to `logger.error("%s", e)` — the message from `fetch_csv` is now self-descriptive, no need to double-prefix.

### 3. `deployment/sheets_to_banana.ipynb` — surface the real message
- Change `except Exception: print("❌ Could not read your Google Sheet. ...")` in the `_run()` cell to `except Exception as e: print(f"❌ {e}")`.
- Add a short markdown line near the top pointing to the FAQ: `❓ Something not working? See the [FAQ](https://github.com/bruno-ritmista/samba/blob/main/sheets_to_banana/FAQ.md).`

### 4. `tests/test_fetch.py` — extend existing patterns (no new framework)
- Update `_make_mock_response` to include a `headers` dict (default `{"Content-Type": "text/csv"}`).
- Update the two `assert_called_once_with(...)` calls to include `timeout=15`.
- Add cases: HTML content-type → clear "not public" message; `requests.exceptions.Timeout` → clear "check your internet connection" message.

### 5. `README.md` — restructure for the two audiences + fix rot
- Fix typos: `percursion` → `percussion`, `Collab` → `Colab` (×2), broken link `https://www.bannadrum.net` → `https://bananadrum.net`.
- Add a **Prerequisites** section before Usage, split by path:
  - Colab: a Google account, a modern browser (Chrome/Firefox/Safari/Edge), and a Google Sheet in the expected notation format, already shared as "Anyone with the link" — link the template sheet as a starting point.
  - CLI (labelled "Advanced / for developers"): Python ≥3.11, git, pip.
- Keep Colab listed first (already is) and label the CLI section as the advanced/secondary path.
- Add a link to `FAQ.md` near the top.

### 6. `FAQ.md` — new file, symptom → cause → fix
Sections, all text-only:
- Prerequisites recap (mirrors README, one line each).
- Link to the template sheet.
- Common errors and what they mean: invalid link, sheet not public (200/HTML case), network/timeout, no breaks found, break number out of range, no recognised instruments, tempo not a number.
- Known limitations: Colab is desktop-only (not mobile-friendly), needs a live internet connection, Colab sessions time out after ~12 hours regardless of the keep-alive, the `branch_name` field is for testing only and should stay blank.
- No dedicated support channel — states that this FAQ is the primary self-service resource.

## Verification
- `pytest sheets_to_banana/tests/ -v` — full suite, including the new/updated `test_fetch.py` cases.
- Run the CLI against the template sheet URL end-to-end to confirm the README's example still works and the template is correctly formatted for the tool.
- Manually trigger each new error path once (bad link, a sheet you own but haven't shared, disconnect network) to confirm the printed messages match the FAQ wording.
- Re-read the diffed README/FAQ for tone consistency with the "independent, non-technical user" audience.
- Rely on the existing `validate_usage_instructions.yml` CI workflow (Mode C already executes the notebook via `nbconvert`) to catch any notebook breakage from the `_run()` edit — no new CI workflow needed.
