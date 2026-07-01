# Implementation Plan — Issue #18: `banana_to_pdf`

## Context

**Why:** Percussionists want to read their samba notation offline (e.g. at rehearsal). Today a rhythm lives only as an interactive [BananaDrum](https://bananadrum.net) share URL. Issue #18 asks for a new tool, `banana_to_pdf`, that takes such a URL and produces a printable A4 PDF grid.

**Critical constraint (from user):** The URL is typically created by a user **manually typing notes in the BananaDrum web GUI** — it is *not* assumed to come from `sheets_to_banana`. It shares the same URL format, but the decoder must be built from BananaDrum's **authoritative** instrument/style schema, not from inverting `sheets_to_banana/src/mapping.py` (which only maps the subset of styles that tool emits, and is missing two instruments — `'a'` 4-Bell Agogo and `'4'` Whippy Repinique — and several hit styles).

**Outcome:** A new self-contained tool `banana_to_pdf/` mirroring `sheets_to_banana/`'s layout, usable two ways:
- **Tech-savvy:** `python -m banana_to_pdf <bananadrum_url> [-o out.pdf]`
- **Non-tech:** a Google Colab notebook that takes the URL and offers the PDF for download.

## Increment plan & status

Increments mirror the pipeline stages (confirmed with user 2026-07-01, one increment per stage, same pattern as `sheets_to_banana/doc/PLAN.md`).

| # | Increment | Scope | Status |
|---|---|---|---|
| 1 | Repo setup + `decode.py` | Worktree/branch (`banana_to_pdf` at `C:/Users/bruno/git/samba/banana-to-pdf`), README row, `decode_url()` + `RawTrack`/`DecodedArrangement`, `test_decode.py` (round-trip vs. `sheets_to_banana`'s verified anchor URLs + real-world BananaDrum URLs) | **Done** |
| 2 | `mapping.py` | Authoritative `INSTRUMENTS`/`GLYPHS` tables, surdo merge, drop-empty-rows, `map_tracks()` | **Done** |
| 3 | `render.py` | fpdf2 A4 grid renderer, 4-bar systems, pagination, title hyperlink, Unicode font | **Done** |
| 4 | `__main__.py` + packaging | CLI (`decode_url` → `map_tracks` → `render_pdf`), `requirements.txt`, `doc/requirements-dev.txt`, `pyproject.toml` console-script entry | **Done** |
| 5 | Colab notebook | `deployment/banana_to_pdf.ipynb` mirroring `sheets_to_banana.ipynb` | **Done** |

**Increment 1 implementation notes (for continuing in another session):**
- `src/decode.py` — `decode_url()`, `_decode_url_number()`, `_decode_notes()`, dataclasses `RawTrack`/`DecodedArrangement`. `_B64` and `_INSTRUMENT_BASE` defined locally (not imported from `sheets_to_banana`, per "Reuse / reference" below).
- `tests/test_decode.py` — 11 tests passing, including the two anchors from `sheets_to_banana/tests/test_encode.py` (`test_low_surdo_beat_2_and_4`, `test_encode_url_with_polyrhythm_verified`) decoded in reverse.
- Manually smoke-tested against two real bananadrum.net URLs (20-bar and 15-bar breaks with mixed polyrhythm/non-polyrhythm tracks) — title/tempo/n_bars parsed correctly, non-polyrhythm tracks padded to the right length, polyrhythm tracks correctly detected and skipped with a warning.
- `pyproject.toml` created for `pip install -e .` (needed for `banana_to_pdf.*` imports to resolve in tests); `requirements.txt` / `doc/requirements-dev.txt` deferred to Increment 4 since no new dependency is needed until `render.py` (fpdf2).
- Next step for Increment 2: read `INSTRUMENTS`/`GLYPHS` design already spec'd under "New tool structure" → `src/mapping.py` below; no new open decisions expected, should be a straight implementation.

**Increment 2 implementation notes (for continuing in another session):**
- `src/mapping.py` — `INSTRUMENTS` (id → name/base/style-labels), `GLYPHS` (id, style_index) → Unicode glyph per the plan's starting proposal, `map_tracks()`, dataclass `Row(label, cells)`.
- Surdo merge: Low (`'9'`) + Mid (`'8'`) → one `"Surdo 1a/2a"` row; both-hit → `◉`; High Surdo (`'7'`) stays separate. Per-track accent/muted *is* distinguishable (accent=`○` open ring, muted=`●` filled, matching the real BananaDrum icon — fixed 2026-07-01, was backwards in the first draft). Remaining open point is narrower than originally stated: only the both-hit merged cell collapses accent/muted info from the two drums into one glyph (`◉` regardless of which of the 4 accent/muted combos occurred).
- Display order implemented as an explicit `_DISPLAY_ORDER` key list (`7, surdo_merged, 5, 3, 4, 6, 2, 1, 0, a`) — Repinique/Whippy and Agogô/4-Bell grouped adjacently since the plan's category list didn't specify sub-order.
- All-rest rows dropped after merge; unmapped (id, style) glyph lookups fall back to `●` and warn once (module-level `_warned` set, same pattern as `sheets_to_banana/src/mapping.py`).
- `tests/test_mapping.py` — 5 tests passing (glyph lookup, surdo merge incl. both-hit, empty-row drop, display order, fallback+warn).
- Next step for Increment 3: `src/render.py` per the fpdf2 spec below; no new open decisions expected.

**Increment 3 implementation notes (for continuing in another session):**
- `assets/DejaVuSans.ttf` bundled by copying it out of a transiently-installed `matplotlib` wheel (matplotlib itself was uninstalled right after; it is not a project dependency). Reuses an already-published, permissively-licensed font instead of hand-fetching a URL.
- One glyph changed from Increment 2's draft: Repinique "hand" (`('3', 6)`) was `'✋'` (U+270B), which DejaVu Sans does **not** cover (confirmed via `fontTools` cmap check) — swapped to `'✱'` (U+2731, heavy asterisk), which it does cover. Every other glyph in `GLYPHS` was checked against the bundled font's cmap and is covered.
- `src/render.py` — `render_pdf(rows, n_bars, title, url, out_path)` plus a testable `_build_pdf(...) -> FPDF` seam (returns before `.output()`, so tests can assert `len(pdf.pages)` without parsing a written file or adding a PDF-reading dependency).
- Systems are drawn whole-or-on-a-new-page (`pdf.set_auto_page_break(False)`, manual space check before each system) so a system never splits across a page break, matching the plan's "paginate between systems" intent rather than fpdf2's default per-cell auto page break.
- Cell width is derived (`(page_width - margins - label_width) / 64`), not hardcoded to the plan's ~2.6mm starting guess — `_LABEL_WIDTH_MM` (34mm, sized for "Repinique (Whippy)") is the tunable knob instead.
- `tests/test_render.py` — 3 tests: non-empty file written, small arrangement fits one page, a 200-bar arrangement forces ≥2 pages.
- `fpdf2` was `pip install`ed into the dev environment for this increment but **not yet** added to `requirements.txt` — that formalization is Increment 4 per the plan, along with wiring `assets/DejaVuSans.ttf` into package data (it currently resolves via a path relative to `src/`, which works for editable installs but needs an explicit package-data entry once this is a real wheel/sdist install, e.g. via Colab).
- Next step for Increment 4: `src/__main__.py` CLI + `requirements.txt` (`fpdf2>=2.7`) + `doc/requirements-dev.txt` (`pytest>=8.0.0`) + package-data wiring for the font, per the plan below.

**Post-Increment-3 revision (2026-07-01, user reviewed a real render against a WebGUI screenshot):**
- **Glyph table replaced.** The real GUI reuses one shared glyph vocabulary across instruments for equivalent hit *kinds*, rather than a bespoke set per instrument: `X`=strong/center accent, `x`=light/edge/ghost, `○`=open, `●`=filled/muted/bass, `⁂`=rimshot, `/`=buzz, `✱`=slap, `↓ v ^ ↑`=Agogô low-low/low/high/high-high (2-bell Agogô reuses 4-Bell's middle two, `v`/`^`). Repinique's "rim" (`◠`) is the one style with no cross-instrument match. Read off the screenshot at low confidence on a few cells — flagged as still tunable, same as before.
- **Surdos un-merged.** High/Mid/Low Surdo (`'7'`/`'8'`/`'9'`) are now three separate rows (matching the WebGUI), not merged into one "Surdo 1a/2a" row — a both-hit combined glyph made Low vs Mid indistinguishable, which defeated the point of printing them. `_merge_surdo` and `_SURDO_BOTH_GLYPH` removed from `mapping.py`.
- **Display order now matches the WebGUI exactly**, top to bottom: Agogô, 4-Bell Agogô, Chocalho, Tamborim, Repinique, Repinique (Whippy), Caixa, Timbau, High Surdo, Mid Surdo, Low Surdo — replacing the earlier "Surdos first" guess.
- `tests/test_mapping.py` updated to match (glyph assertions, no-merge assertion, new order assertion).

**Increment 4 implementation notes (for continuing in another session):**
- `src/__main__.py` — `main()`: argparse (`url` positional, `-o/--output`), pipeline `decode_url` → `map_tracks` → `render_pdf`, `_default_output_path(title)` slugifies the title (regex, mirrors `sheets_to_banana`'s use of `re` for title cleanup) falling back to `arrangement.pdf` when title is empty. Errors from `decode_url` (bad/malformed URL) are caught and logged rather than crashing with a traceback, same pattern as `sheets_to_banana/src/__main__.py`'s `fetch_csv` try/except.
- **Font packaging fixed**, not just wired: `assets/DejaVuSans.ttf` moved to `src/assets/DejaVuSans.ttf` (sibling of `render.py`) and `pyproject.toml` gained `[tool.setuptools.package-data]` (`banana_to_pdf = ["assets/*.ttf"]`). The old path (`Path(__file__).parent.parent / 'assets'`) only worked for editable installs; verified the fix against a real (non-editable) `pip install .` into a throwaway venv — `python -m banana_to_pdf <url>` rendered a non-empty PDF.
- `pyproject.toml` also gained `dependencies = ["fpdf2>=2.7"]` and `[project.scripts] banana_to_pdf = "banana_to_pdf.__main__:main"` — verified the installed console-script (`banana_to_pdf <url> -o out.pdf`) also renders correctly.
- Only `python -m banana_to_pdf` (installed) and the `banana_to_pdf` console-script are supported — unlike `sheets_to_banana`, there is **no** top-level direct-run trick file (`banana_to_pdf/__main__.py` importing `src/` without install), since the plan's own usage docs only ever specify `python -m banana_to_pdf ...`, and no CI validate-usage workflow exists yet for this tool to require it.
- `tests/test_main.py` — 3 tests: default-filename derivation (with and without title), one end-to-end smoke test reusing `test_decode.py`'s verified anchor URL, asserting a real PDF gets written and its path printed.
- Full suite: 22/22 passing (`pytest tests/ -v`).
- Next step for Increment 5: `deployment/banana_to_pdf.ipynb` per the plan below — copy `sheets_to_banana.ipynb`'s pattern, `uv pip install ... git+...#subdirectory=banana_to_pdf`, call `decode_url`/`map_tracks`/`render_pdf` directly, `google.colab.files.download(path)`.

**Increment 5 implementation notes:**
- `deployment/banana_to_pdf.ipynb` — one markdown cell + one form-mode code cell, mirroring `sheets_to_banana.ipynb`'s structure (branch-aware `uv pip install`, keepalive thread, friendly ⚠️-prefixed warning logging, ✅/❌ messages). Simpler than the sheets version: single `bananadrum_url` param (no break-selection/tempo fields, since those aren't inputs to this pipeline) plus the same advanced `branch_name` field.
- Reuses `_default_output_path` from `__main__.py` (imported, not duplicated) for the download filename.
- Pipeline cell: `decode_url` → `map_tracks` → `render_pdf` → `google.colab.files.download(out_path)`; `decode_url` failure and empty-`rows` are both caught and reported with a friendly ❌, matching `__main__.py`'s error handling.
- Verified the exact pipeline calls used in the notebook cell (not the notebook itself, which needs Colab) against a real decode: rendered a non-empty PDF from the anchor URL in `test_decode.py`.
- All 5 increments now complete per the plan.

## Decisions locked with the user

| Topic | Decision |
|---|---|
| Note glyphs | **Unicode symbols** (not ASCII, not embedded icon images) that resemble BananaDrum icons, reusing one glyph per hit-kind across instruments (see revision note above). |
| Glyph table | I provide a sensible default dict; user tunes after seeing a real PDF. Revised once already against a WebGUI screenshot (2026-07-01); still tunable. |
| Polyrhythm (6/8) | **Out of scope for iteration 1.** Detect a `-<suffix>` on a track segment, warn, skip that track. Open point for future. |
| Layout | **4 bars per "system"** (64 step-cells wide), systems stacked down the page; ~9 systems ≈ 36 bars for a typical (few-instrument) break. |
| Overflow | **Paginate automatically** — spill onto page 2, 3… based on available vertical space. |
| Instrument order | Matches the WebGUI top-to-bottom order exactly (see revision note above). |
| Surdos | **Not merged** — High/Mid/Low Surdo stay three separate rows, matching the WebGUI (reversed from the original "merge Low+Mid" decision once a combined glyph proved to hide which drum was hit). |
| Empty instruments | Omitted from the PDF (all-rest tracks skipped). |
| Unknown styles | Skip (fallback to rest/blank) + warn; never crash. Open point for future. |
| PDF library | **fpdf2** (pure-Python, tiny, Colab-friendly, native table + hyperlink + Unicode-font support). |
| Structure | Mirror `sheets_to_banana/` exactly. |

## Repo setup (do first)

Per project workflow, **create a dedicated worktree** — do not edit in `main`:
- Branch `banana_to_pdf`, worktree at `C:/Users/bruno/git/samba/banana-to-pdf`.
- Add a row to root `README.md` table: `banana_to_pdf | BananaDrum URL → printable PDF | Done | banana_to_pdf`.

## Authoritative schema (source of truth)

From BananaDrum `packages/bananadrum-webapp/src/bateria-instruments.ts` (repo `github.com/mooseling/BananaDrum`). **The implementer should confirm against that file** (clone the repo if the local copy at `c:\Users\bruno\git\BananaDrum` is absent). Instrument id → (name, style-count, `base = styles+1`):

| id | name | styles (in order) | base |
|---|---|---|---|
| `0` | Agogo | low, high | 3 |
| `a` | 4-Bell Agogo | low-low, low, high, high-high | 5 |
| `1` | Chocalho | accent, ghost | 3 |
| `2` | Tamborim | accent, ghost | 3 |
| `3` | Repinique | center, edge, rimshot, rim, buzz, hand, slap | 8 |
| `4` | Repinique (Whippy) | accent, ghost | 3 |
| `5` | Caixa | accent, ghost, buzz, rimshot | 5 |
| `6` | Timbau | open, slap, bass | 4 |
| `7` | High Surdo | accent, muted | 3 |
| `8` | Mid Surdo | accent, muted | 3 |
| `9` | Low Surdo | accent, muted | 3 |

Style index `0` = rest; `1..n` = the styles above in order. `base` values match `sheets_to_banana`'s `_INSTRUMENT_BASE` for the 9 shared instruments — good cross-check.

## URL / composition format (from `encode.py` + BananaDrum `deserialisers.ts`)

```
https://bananadrum.net/?t=<url-encoded title>&a2=<composition>
        (t= optional)                          |
composition = 4-4 . <tempo> . <n_bars> . 1-4 . 16 . <track1> . <track2> ...
              timesig  tempo   length    pulse  stepRes
track = <instrument_id><base64 notes>[ - <base64 polyrhythm> ]
```
- Base-64 alphabet (verbatim from `encode.py`): `0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ~_`
- Total steps per track = `n_bars * 16` (stepResolution 16).
- Notes are digits of a base-N integer, **first step = MSB**.

## New tool structure (`banana_to_pdf/`)

Mirror `sheets_to_banana/`. Pipeline runs left→right:

```
BananaDrum URL
  → decode.py   decode_url()    parse query, split composition, base-64→style indices per track
  → mapping.py  map_tracks()    instrument id→name, (id,style)→Unicode glyph; merge surdos; drop empties
  → render.py   render_pdf()    fpdf2: A4 grid, 4-bar systems, paginate, title hyperlink
  → __main__.py CLI
```

### `src/decode.py`
Exact inverse of `encode.py`:
- `decode_url(url) -> DecodedArrangement` with fields `title: str`, `tempo: int`, `n_bars: int`, `tracks: list[RawTrack]`.
- `RawTrack(instrument_id: str, styles: list[str])` — per-step style-index strings, length `n_bars*16`.
- Base-64 decode: `for ch in s: n = n*64 + _B64.index(ch)`. Then recover digits: `divmod(n, base)` repeatedly, **prepend**, **pad leading `'0'`** to `n_bars*16`.
- Parse query with `urllib.parse` (`urlparse` + `parse_qs`); `unquote` the `t=` param. Handle `t=` absent (→ `title=""`).
- If a track segment contains `'-'`: it carries a polyrhythm → log a warning and **skip that track** (iteration-1 limitation; the pre-`-` integer encodes *spliced* notes and would misalign if naively expanded).
- Reuse the `_B64` constant and per-instrument `base` table (define locally — keep the tool self-contained, do **not** import across sibling packages).

### `src/mapping.py`
- `INSTRUMENTS: dict[id -> (display_name, base, [style_labels])]` — the authoritative table above.
- `GLYPHS: dict[(instrument_id, style_index_int) -> str]` — proposed default Unicode map (user-tunable, one editable dict). Starting proposal (mark each `# tunable`):
  - Agogo `0`: 1→`▽` 2→`△`;  4-Bell `a`: 1→`▼` 2→`▽` 3→`△` 4→`▲`
  - Chocalho `1`, Tamborim `2`, Whippy `4`: 1→`●` 2→`○`
  - Repinique `3`: 1→`●` 2→`◐` 3→`╱` 4→`▏` 5→`~` 6→`✋` 7→`◆`
  - Caixa `5`: 1→`●` 2→`○` 3→`~` 4→`╱`
  - Timbau `6`: 1→`◯` 2→`◆` 3→`●`
  - High/Mid/Low Surdo `7/8/9`: 1→`●` 2→`◌` (muted)
  - Fallback for any unmapped style: `●` (or blank) + warn once.
- `map_tracks(decoded) -> list[Row]` where `Row(label: str, cells: list[str])`, one glyph or `''`(rest) per step:
  - **Merge surdos:** combine id `'9'` (Low) and `'8'` (Mid) into a single `"Surdo 1a/2a"` row — per step: low-only→low glyph, mid-only→mid glyph, both→`◉` (tunable), rest→blank. Muted variants → damped glyph (tunable, open point).
  - **Drop all-rest rows** (issue requirement).
  - Order rows by BananaDrum `displayOrder` (Surdos, Caixa, Repinique, Timbau, Tamborim, Chocalho, Agogo).

### `src/render.py` — fpdf2
- `render_pdf(rows, n_bars, title, url, out_path)`.
- A4 portrait (`FPDF(orientation='P', format='A4')`), margins ~10 mm.
- **Title** at top: `title or "Untitled"`, as a hyperlink to `url` (`pdf.cell(..., link=url)`).
- **System = 4 bars = 64 step-cells** + a left label column. Draw a header row of bar numbers; beat gridlines every 4 cells, heavier bar separators every 16.
- Stack systems down the page; when the next system won't fit vertically, `pdf.add_page()` (**automatic pagination**).
- Cell/font sizes are layout **calibration knobs** — start ~2.6 mm cell width, ~4.5 mm row height, small font; tune against a real render. `# ponytail: tune cell geometry against a printed A4 proof`.
- Register a Unicode TTF font (fpdf2's core fonts are Latin-1 only) so glyphs render — bundle e.g. DejaVuSans (`pdf.add_font(...); pdf.set_font('DejaVu', size=...)`). List the `.ttf` in the package data / notebook install.

### `src/__main__.py`
- argparse mirroring `sheets_to_banana`: positional `url`; `-o/--output` (default derived from title or `arrangement.pdf`).
- Pipeline: `decode_url` → `map_tracks` → `render_pdf`; `logging.basicConfig(level=INFO, stream=sys.stderr)`; print the saved path.

### Packaging
- `requirements.txt`: `fpdf2>=2.7`. `doc/requirements-dev.txt`: `pytest>=8.0.0`.
- `pyproject.toml`/`setup.cfg` mirroring `sheets_to_banana` (console-script entry + package data for the bundled font).

### `deployment/banana_to_pdf.ipynb`
Copy the `sheets_to_banana.ipynb` pattern: one form-mode cell with `#@param` inputs `bananadrum_url` (string) and optional `branch_name`; `uv pip install ... git+https://github.com/bruno-ritmista/samba.git@{branch}#subdirectory=banana_to_pdf`; call the pipeline directly (import `decode_url`, `map_tracks`, `render_pdf`); write the PDF then `google.colab.files.download(path)`; friendly ✅/❌/⚠️ messages.

## Files to create

| File | Role |
|---|---|
| `banana_to_pdf/src/__init__.py` / `__main__.py` | package + CLI |
| `banana_to_pdf/src/decode.py` | URL → per-track style indices (inverse of `encode.py`) |
| `banana_to_pdf/src/mapping.py` | authoritative id/style tables + Unicode `GLYPHS` + surdo merge |
| `banana_to_pdf/src/render.py` | fpdf2 A4 grid renderer |
| `banana_to_pdf/tests/test_decode.py` / `test_render.py` | pytest |
| `banana_to_pdf/requirements.txt`, `doc/requirements-dev.txt`, `pyproject.toml` | packaging |
| `banana_to_pdf/deployment/banana_to_pdf.ipynb` | Colab |
| `banana_to_pdf/assets/DejaVuSans.ttf` | Unicode font for glyphs |
| root `README.md` | add tool row |

## Reuse / reference (do not re-derive)

- `sheets_to_banana/src/encode.py` — the encoder `decode.py` inverts (base-64 alphabet, per-instrument base, MSB-first, `?t=…&a2=…` format). Verbatim reference, not imported.
- `sheets_to_banana/src/mapping.py` — verified partial style map, use to cross-check the shared 9 instruments.
- `sheets_to_banana/deployment/sheets_to_banana.ipynb` — notebook template to copy.
- `sheets_to_banana/tests/` — pytest conventions (`test_<behavior>_<outcome>`, no classes, `caplog` for warnings).

## Verification

1. **Round-trip (strongest):** take a known URL from `sheets_to_banana/tests/test_e2e.py` (or generate one via `encode_url`), run `decode_url`, and assert instrument ids + per-step style indices match the original `MappedTrack`s. This proves decode ⟂ encode.
2. **Unit:** `test_decode.py` — base-64 decode of small known integers; leading-zero padding to `n_bars*16`; `t=` present/absent; polyrhythm-suffix track is skipped with a warning (`caplog`).
3. **Render smoke:** `test_render.py` — render a small 2-instrument, 4-bar arrangement; assert the output `.pdf` exists, is non-empty, and (via fpdf2) has the expected page count; a >36-bar input yields ≥2 pages.
4. **Manual end-to-end:** build a rhythm at bananadrum.net, copy its share URL, run `python -m banana_to_pdf "<url>" -o out.pdf`, open `out.pdf`, confirm: correct instruments (empties omitted), Surdos as three separate rows in WebGUI order, glyphs legible, title hyperlink opens the URL, 4-bar systems paginate.

## Open points (future iterations)

- Polyrhythm (6/8) decoding & rendering — currently detected-and-skipped with a warning.
- Glyph table aesthetics — several glyphs (`⁂` rimshot, `◠` rim, `/` buzz) were read off a screenshot at low confidence; tune against a printed A4 page. The `/` buzz glyph in particular may need to become a multi-character `///` to match the WebGUI's triple-slash icon once cell width allows it.
