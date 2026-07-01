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
| 2 | `mapping.py` | Authoritative `INSTRUMENTS`/`GLYPHS` tables, surdo merge, drop-empty-rows, `map_tracks()` | Not started |
| 3 | `render.py` | fpdf2 A4 grid renderer, 4-bar systems, pagination, title hyperlink, Unicode font | Not started |
| 4 | `__main__.py` + packaging | CLI (`decode_url` → `map_tracks` → `render_pdf`), `requirements.txt`, `doc/requirements-dev.txt`, `pyproject.toml` console-script entry | Not started |
| 5 | Colab notebook | `deployment/banana_to_pdf.ipynb` mirroring `sheets_to_banana.ipynb` | Not started |

**Increment 1 implementation notes (for continuing in another session):**
- `src/decode.py` — `decode_url()`, `_decode_url_number()`, `_decode_notes()`, dataclasses `RawTrack`/`DecodedArrangement`. `_B64` and `_INSTRUMENT_BASE` defined locally (not imported from `sheets_to_banana`, per "Reuse / reference" below).
- `tests/test_decode.py` — 11 tests passing, including the two anchors from `sheets_to_banana/tests/test_encode.py` (`test_low_surdo_beat_2_and_4`, `test_encode_url_with_polyrhythm_verified`) decoded in reverse.
- Manually smoke-tested against two real bananadrum.net URLs (20-bar and 15-bar breaks with mixed polyrhythm/non-polyrhythm tracks) — title/tempo/n_bars parsed correctly, non-polyrhythm tracks padded to the right length, polyrhythm tracks correctly detected and skipped with a warning.
- `pyproject.toml` created for `pip install -e .` (needed for `banana_to_pdf.*` imports to resolve in tests); `requirements.txt` / `doc/requirements-dev.txt` deferred to Increment 4 since no new dependency is needed until `render.py` (fpdf2).
- Next step for Increment 2: read `INSTRUMENTS`/`GLYPHS` design already spec'd under "New tool structure" → `src/mapping.py` below; no new open decisions expected, should be a straight implementation.

## Decisions locked with the user

| Topic | Decision |
|---|---|
| Note glyphs | **Unicode symbols** (not ASCII, not embedded icon images) that resemble BananaDrum icons. |
| Glyph table | I provide a sensible default dict; user tunes after seeing a real PDF. |
| Polyrhythm (6/8) | **Out of scope for iteration 1.** Detect a `-<suffix>` on a track segment, warn, skip that track. Open point for future. |
| Layout | **4 bars per "system"** (64 step-cells wide), systems stacked down the page; ~9 systems ≈ 36 bars for a typical (few-instrument) break. |
| Overflow | **Paginate automatically** — spill onto page 2, 3… based on available vertical space. |
| Surdos | Merge Low (`'8'`... actually id `'9'`) + Mid (id `'8'`) tracks back into **one "Surdo 1a/2a" row**. High Surdo (`'7'`) stays its own row. |
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
4. **Manual end-to-end:** build a rhythm at bananadrum.net, copy its share URL, run `python -m banana_to_pdf "<url>" -o out.pdf`, open `out.pdf`, confirm: correct instruments (empties omitted), surdos merged into one row, glyphs legible, title hyperlink opens the URL, 4-bar systems paginate.

## Open points (future iterations)

- Polyrhythm (6/8) decoding & rendering — currently detected-and-skipped with a warning.
- Glyphs for hit styles with no clean single symbol, and muted-surdo damped glyph — currently fallback/skip; refine after a real print proof.
- Glyph table aesthetics — tune against a printed A4 page.
