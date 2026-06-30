# Plan: E2E test cases for sheets_to_banana (issue #13)

## Context

All 130 existing tests are unit tests; each isolates one pipeline module
(`parse` / `mapping` / `encode` / `fetch`), and all network is mocked
(`test_fetch.py` patches `requests.get`). Two near-E2E tests exist
(`test_short_corte_full_pattern`, `test_long_corte_full_pattern` in
`test_parse.py`) but they start from an inline CSV string and skip both
`fetch_csv` and `main()`.

Issue #13 wants true end-to-end coverage: **give the tool a real Google Sheets
link, run the real pipeline, assert the BananaDrum URL(s) are correct** — so a
regression anywhere from fetch → parse → keywords → mapping → trim → encode →
stdout is caught.

## Decisions (from interview)

- **Input:** ONE real, public, **view-only** Google Sheet (anyone-with-link can
  *view*). Read credential-free via the existing `fetch.py` export path.
- **Why view-only (not writable):** writing to Sheets requires OAuth2 / a
  service account — "anyone can edit" does NOT grant anonymous API writes.
  Making the sheet view-only eliminates the threat (vandalism) AND its
  mitigation (the check-and-overwrite script), so there is **no service
  account, no CI secret, no new dependency, no drift-check, no overwrite logic.**
- **Entry point under test:** `main()` from `sheets_to_banana.__main__`, invoked
  with a patched `sys.argv`; capture printed BananaDrum URL(s) from stdout and
  assert exact match.
- **Expected URLs:** generate from current code against the live sheet, user
  verifies each in bananadrum.net once, then **freeze** as golden constants.
- **Canonical sheet content source of truth:** built from the same
  `make_csv` / `instrument_row` / `section_label` / `break_header` helpers the
  unit tests use (extracted to a shared module so it's literally the same code).
- **Coverage:** broad — one sheet exercising many features: multiple breaks,
  several instruments, keywords (levada / virada / corte), 6/8 polyrhythm, and
  the surdo split.
- **CI placement:** runs in the existing `test_suite.yml` pytest job alongside
  unit tests (no separate job/marker).

## Implementation

### 1. Extract shared CSV helpers — `tests/csv_helpers.py` (new)
Move `make_csv`, `instrument_row`, `section_label`, `break_header`,
`empty_row` out of `test_parse.py` into `tests/csv_helpers.py`. Update
`test_parse.py` to `from tests.csv_helpers import ...` (mechanical; behavior
unchanged — the suite must still pass). This makes the E2E canonical content
*reuse* the unit helpers rather than duplicate them.
- `tests/__init__.py` already exists, so `from tests.csv_helpers import …`
  resolves under the existing `pythonpath = ["."]`.

### 2. Canonical sheet definition + materializer — `tests/test_e2e.py` (new)
- A module-level function `canonical_csv()` that builds the broad multi-break
  sheet content using the shared helpers. This is the in-repo record of exactly
  what the live sheet must contain.
- A `if __name__ == '__main__': print(canonical_csv())` block so the content can
  be regenerated and pasted into the sheet (`python tests/test_e2e.py`).
  *ponytail: no Sheets-API writer — view-only means the sheet is populated by
  hand/paste, rarely.*

### 3. The E2E test — in `tests/test_e2e.py`
- `LIVE_SHEET_URL` constant = the real view-only share link (filled in once the
  sheet exists — see Prerequisite).
- `EXPECTED_URLS` constant = frozen list of BananaDrum URLs (one per break, in
  sheet order), captured + user-verified during step 5.
- Test body:
  1. Pre-flight connectivity: `requests.get(export_url, timeout=10)`; on
     `requests.ConnectionError` / `requests.Timeout` → `pytest.skip("Google
     Sheets unreachable")`. (HTTP errors like a deleted/private sheet are NOT
     skipped — they surface as failures.)
  2. `monkeypatch.setattr(sys, 'argv', ['sheets_to_banana', LIVE_SHEET_URL])`.
  3. `from sheets_to_banana.__main__ import main; main()`.
  4. `out = capsys.readouterr().out` → assert
     `out.strip().splitlines() == EXPECTED_URLS`.
- `main()` prints all breaks (one URL per line) when `--break` is omitted; order
  is deterministic, so exact list equality is the assertion. Logging goes to
  stderr, so stdout is clean URLs only.
- *ponytail check:* this single live test is the runnable check for the whole
  E2E path; no extra scaffolding.

### 4. CI — `.github/workflows/test_suite.yml`
No change needed: it already runs `pip install .` + `pytest tests/ -v`, which
picks up `test_e2e.py`. The test makes a real network call in that job, as
chosen.

## Prerequisite handoff (blocks completion)

Implementation cannot finish without a one-time manual step that only the user
can do (no Google credentials available to me):

1. I produce `canonical_csv()` and run `python tests/test_e2e.py` to print the
   CSV.
2. **User** creates a Google Sheet, pastes/imports that content, shares it
   **"anyone with the link — Viewer"**, and gives me the URL.
3. I set `LIVE_SHEET_URL`, run `python -m sheets_to_banana <url>`, capture the
   emitted URL(s).
4. **User** opens each URL in bananadrum.net to confirm it plays the intended
   pattern.
5. I freeze the verified URLs into `EXPECTED_URLS`.

## Critical files

| File | Change |
|---|---|
| `sheets_to_banana/tests/csv_helpers.py` | NEW — shared CSV builder helpers (extracted from `test_parse.py`) |
| `sheets_to_banana/tests/test_parse.py` | EDIT — import helpers from `csv_helpers` (mechanical) |
| `sheets_to_banana/tests/test_e2e.py` | NEW — canonical content + materializer + live E2E test |
| `sheets_to_banana/src/__main__.py` | reused as-is (`main()` is the entry point) |
| `sheets_to_banana/src/fetch.py` | reused as-is (credential-free read path) |

## Verification

- `pytest sheets_to_banana/tests/ -v` — full suite green, including
  `test_e2e.py` (which performs the live fetch + asserts frozen URLs).
- `pytest sheets_to_banana/tests/test_e2e.py -v` — E2E in isolation.
- Disconnect network → E2E reports **skipped** (not failed), proving the
  connectivity guard.
- Manually corrupt one `EXPECTED_URLS` entry → E2E **fails**, proving the
  assertion bites.
- `python tests/test_e2e.py` prints the canonical CSV (sheet repopulation path).

## Deliberately out of scope

- Sheets-API write / service-account / CI secret / `google-api-python-client`
  (eliminated by the view-only decision).
- Runtime drift/tamper check (impossible to drift a view-only sheet).
- Per-feature separate sheets/tabs (one broad sheet chosen instead).
