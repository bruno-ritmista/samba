# sheet_to_banana — Design Plan

This file desctribes the plan to design sheet_to_banana.

## Design increments

### ✅ Increment 1 — fetch custom table-based notes from Google sheets
Converts a Google Sheets URL into CSV text using the free CSV export endpoint
(no API key needed for public sheets).

### ✅ Increment 2 — parse custom table-based notes (one note per cell)
Parses the CSV into `Break` objects. Each break holds one dict mapping instrument
name → full note sequence (all bar groups concatenated into one flat list).
The Z-pattern layout (bars 1–4, then 5–8, …) is stitched together automatically.

### ✅ Increment 3 — map custom table-based notes to Bananadrum notes
Translates CSV instrument names and note characters into BananaDrum instrument IDs
and note style IDs.

**Instrument mapping:**

| CSV name | BananaDrum ID | Note chars → style ID |
|---|---|---|
| Agogô / Agogo | `'0'` | `L`→`'1'` (low), `H`→`'2'` (high) |
| Chocalho | `'1'` | `X`→`'1'` |
| Tamborim | `'2'` | `X`→`'1'` |
| Repique / Repinique | `'3'` | `X`→`'1'`, `x`→`'2'`, `/`→`'3'`, `K`→`'4'`, `W`→`'5'`, `O`→`'6'`, `S`→`'7'` |
| Caixa | `'5'` | `X`→`'1'`, `x`→`'2'`, `W`→`'3'`, `/`→`'4'` |
| Timbau | `'6'` | `S`→`'2'`, `O`→`'3'`, `OO`→skip |
| Surdo 3a / Surdo Mor | `'7'` | `X`→`'1'`, `D`→`'2'`, `W`→skip |
| Surdo 1a/2a, Surdos (for `'2'`/`'O'`) | `'8'` | `'2'`/`O`→`'1'` |
| Surdo 1a/2a, Surdos (for `'1'`/`'O'`) | `'9'` | `'1'`/`O`→`'1'` |

**Surdo split rule:** A "Surdo 1a/2a" or "Surdos" row is split into TWO BananaDrum
tracks. `'1'` hits → Low Surdo `'9'`; `'2'` hits → Mid Surdo `'8'`; `'O'` hits →
**both** tracks (unison). Unknown chars and `W` on Surdo Mor → rest (`'0'`).

### ✅ Increment 4 — encode.py
Implements the BananaDrum URL encoding (replicates the TypeScript in
`packages/bananadrum-core/src/prod/serialisation/`):
- Notes are treated as digits of a base-N number (last step = LSB)
- N = number of note styles + 1 (for rest)
- The number is encoded in base 64 using `0-9a-zA-Z~_`

**Bases per instrument:**
`'0'`=3, `'1'`=3, `'2'`=3, `'3'`=8, `'5'`=5, `'6'`=4, `'7'`=3, `'8'`=3, `'9'`=3

**URL format:** `https://bananadrum.net/?a2=4-4.{tempo}.{n_bars}.1-4.16.{track1}.{track2}...`

### ✅ Increment 5 — intergrate increments 1-5
CLI entry point:
```
python -m sheet_to_banana <sheets_url> [--break 0] [--tempo 120]
```

### ✅ Increment 6 — parse, encode keywords (e.g. levada, virada) from custom table-based notes to Bananadrum notes
Handles merged cells whose text content is a recognised keyword rather than individual
note characters. These cells appear in the Google Sheet when an arranger writes a
shorthand name for a stock pattern (e.g. *levada*, *virada*) spanning several columns.

**Detection:** during parse, any note cell whose stripped value does not consist solely
of known note characters (`X`, `x`, `O`, `S`, `L`, `H`, `/`, `K`, `W`, `D`, `0-9`)
and contains no embedded whitespace is a keyword cell.  A merged keyword cell spans
one or more following empty columns (the same heuristic used for Increment 6).

**Expansion:** the keyword + instrument pair is looked up in a table; the result is a
flat list of note characters whose length equals the number of columns spanned.  If no
match is found the columns are filled with rests and a warning is printed.

**Keyword table (dummy set):**

| Keyword | Instrument | Pattern (per 16 steps unless noted) |
|---|---|---|
| `levada` | Caixa | `X X x / X x / x X x / x X x / x` |
| `levada` | Tamborim | `X x x x X x x x X x x x X x x x` |
| `levada` | Repique | `X x / O X x / O X x / O X x / O` |
| `virada` | Caixa | `X X x / X 0 X 0 X 0 0 0 0 0 0 0` |
| `virada` | Repique | `X 0 X 0 X 0 X 0 X X 0 X X 0 X X` |
| `virada` | Surdo Mor | `0 0 0 0 0 0 0 0 0 0 0 0 X 0 X 0` |

Patterns for other instrument+keyword combinations are filled with rests (with a
warning) until explicitly defined.  The table is data-driven so new entries can be
added without touching any logic.

**Integration point:** `keywords.py` is called inside `parse.py` after the raw note
cells are read but before they are stored in the `Break` object.  The function
signature is:

```python
def expand_keywords(instrument: str, cells: list[str]) -> list[str]:
    """Replace keyword cells with their predefined note sequences.

    Each element of `cells` is either a note character, an empty string
    (rest from a non-merged cell), or a keyword string.  Returns a flat
    list of the same total length with keywords replaced by note characters.
    """
```

### ✅ Increment 7 — Add title in BananaDrum link

Adds a human-readable `?t=` title parameter to the generated URL.

**Example output:**
```
https://bananadrum.net/?t=Mangueira%202023%20-%20Break%20Alegria%20invade%20o%20Pel%C3%B4&a2=...
```

**Source data (from the real sheet CSV):**
- Row 0, col 1: song title — `"As Áfricas Que a Bahia Canta" - Estação Primeira de Mangueira 2023`
- Row 1, col 1: break name — `Break Alegria invade o Pelô   (Zeichen gekreuzte Fäuste)`

**Song title extraction:**
The song title row is the first break-header row in the CSV (col 0 empty, col 1 non-empty, no tracks follow before the next header). Take the text after the last ` - ` separator to get the short form (e.g. `Estação Primeira de Mangueira 2023` → but trimmed further per house style to `Mangueira 2023`).

Rule: split on ` - `, take the last segment, strip surrounding whitespace.

**Break title cleaning:**
Strip any trailing parenthetical comment with `re.sub(r'\s*\(.*\)\s*$', '', name).strip()`.

**Combined title:**
`{song_short} - {break_clean}` → `Mangueira 2023 - Break Alegria invade o Pelô`

**URL encoding:**
`urllib.parse.quote(title, safe='')` — encodes spaces as `%20` and preserves Unicode (e.g. `ô` → `%C3%B4`).

**Implementation touches:**
- `parse.py` — add `parse_song_title(csv_text: str) -> str` that reads the first break-header row (col 0 empty, col 1 non-empty, rest empty) and returns its value, or `''` if absent.
- `encode.py` — add optional `title: str = ''` parameter to `encode_url`; when non-empty, prepend `?t={quoted_title}&` before `a2=`.
- `__main__.py` — call `parse_song_title`, build the combined title, pass it to `encode_url`.

### ✅Increment 8 — parse custom table-based notes in 6/8 time signature

Handle merged cells that span exactly 16 columns (one full bar), contain
space-separated note characters, and are **not** keywords. These represent
6/8 bars: up to 12 evenly-spaced notes replacing 16 sixteenth-note slots.
BananaDrum models this with a polyrhythm that replaces 16 base notes with
12 polyrhythm notes.

**Reference URLs:**
- 16 notes replaced by 1 set of 12 notes: `https://bananadrum.net/?a2=4-4.110.1.1-4.16.00.10.20.3999999-6eI5.50.60.70.80.90`
- 16 notes replaced by 4 sets of 3 notes: `https://bananadrum.net/?a2=4-4.110.1.1-4.16.00.10.20.3999999-geSZ~GGuojKAk.50.60.70.80.90`
- 4 notes replaced by 1 set of 3 notes: `https://bananadrum.net/?a2=4-4.110.1.1-4.16.00.10.20.319000000-3nq.50.60.70.80.90`

That URL uses a single polyrhythm descriptor `0-15-12` (start=0, span=15,
length=12), packed into `6eI5`. For the 16-column case the descriptor is
`i-15-12` per group (or `i-15-n` when the cell contains fewer than 12 notes,
padded to 12 with rests).

**Detection (parse.py):**

A 6/8 cell is a note cell where:
- `span == 16` (one non-empty cell followed by exactly 15 empty cells = 1 full bar)
- `' ' in cell` (multiple note characters separated by spaces)
- The non-space content consists only of valid note characters (not a keyword)

Add a `PolyGroup` dataclass:

```python
@dataclass
class PolyGroup:
    start: int        # 0-based absolute slot index in the full track's flat list
    end: int          # start + 15 (always 16-column span)
    notes: list[str]  # up to 12 raw note characters; pad/truncate to 12
```

Extend `Break`:
```python
@dataclass
class Break:
    name: str
    tracks: dict[str, list[str]] = field(default_factory=dict)
    polygroups: dict[str, list[PolyGroup]] = field(default_factory=dict)
```

In the instrument-row loop in `parse_sheet`, before calling `expand_keywords`,
scan `note_cells` for 6/8 cells: for each position `i` where `note_cells[i]`
is non-empty, has a space, looks like note chars, and is followed by exactly 3
empty cells, extract the raw note chars, build a `PolyGroup` with
`start = bar_group_offset + i`, `end = bar_group_offset + i + 3`, and
`notes = cell.split()` padded/truncated to 6 with `'0'`.  Replace all 4 cells
with `''` so `expand_keywords` sees them as ordinary rests.

Warn and truncate if the cell contains more than 6 note characters.

**Mapping (mapping.py):**

Add `MappedPolyrhythm` and extend `MappedTrack`:

```python
@dataclass
class MappedPolyrhythm:
    start: int        # base slot index (same as PolyGroup.start)
    end: int          # base slot index (same as PolyGroup.end)
    notes: list[str]  # 6 style indices, e.g. ['1','0','1','0','1','0']

@dataclass
class MappedTrack:
    instrument_id: str
    notes: list[str]
    polyrhythms: list[MappedPolyrhythm] = field(default_factory=list)
```

In `map_break`, after building the flat notes for each instrument, also
translate any `PolyGroup` entries in `brk.polygroups[name]` to
`MappedPolyrhythm` using the same note-style table.  For `surdo_split`,
duplicate and translate separately for Low and Mid Surdo tracks.

**Encoding (encode.py):**

Two new helpers:

```python
_POLY_B11 = '0123456789-'  # 11 chars; '-' is index 10

def _pack_polyrhythm_string(s: str) -> str:
    n = 0
    for ch in s:
        n = n * 11 + _POLY_B11.index(ch)
    return _url_encode_number(n)

def _encode_polyrhythms(polys: list[MappedPolyrhythm]) -> str:
    """Build and pack the polyrhythm descriptor string.

    BananaDrum applies polyrhythms in list order.  When applying poly[k],
    all earlier polys have already been applied, so the start/end indices
    must be shifted by the cumulative extra notes those polys added.
    Each 4→6 polyrhythm contributes +2 extra notes.
    """
    cumulative_extra = 0
    parts: list[str] = []
    for poly in sorted(polys, key=lambda p: p.start):
        adj_start = poly.start + cumulative_extra
        span = poly.end - poly.start          # always 3
        length = len(poly.notes)              # always 6
        parts += [str(adj_start), str(span), str(length)]
        cumulative_extra += length - (span + 1)   # 6 - 4 = 2
    return _pack_polyrhythm_string('-'.join(parts))
```

Build the **effective notes list** by splicing polyrhythm notes into the base
notes (replaces the 4 base slots with 6 polyrhythm notes for each group):

```python
def _build_effective_notes(base: list[str], polys: list[MappedPolyrhythm]) -> list[str]:
    out, idx = [], 0
    for poly in sorted(polys, key=lambda p: p.start):
        out.extend(base[idx:poly.start])
        out.extend(poly.notes)
        idx = poly.end + 1
    out.extend(base[idx:])
    return out
```

In `encode_url`, for each track that has polyrhythms:
- Use `_build_effective_notes` instead of `track.notes` as the digit list
- Append `-{_encode_polyrhythms(track.polyrhythms)}` after the encoded notes

**Verified reference (polyrhythm packing):**
Descriptor string `0-15-12` → digits [0,10,1,5,10,1,2] in base 11
→ integer 1 633 029 → base-64 chars `6eI5`. ✓

## Verified encoding example
Low Surdo accent on beat 2 and beat 4 of 1 bar:
→ `https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm`  ✓ (tested in BananaDrum)


### ✅ Increment 9 — Don't convert leading and trailing empty bars to BananaDrum link 

If a break contains leading or trailing bars where every instrument is all rests,
those bars are stripped before encoding.

**Empty bar definition:** a bar (16 steps) where every step of every track is `'0'`
(rest). A bar that contains a polyrhythm merged cell is never all rests by definition.

**Behaviour:**
- Trim leading empty bars **and** trailing empty bars.
- If all bars are empty after trimming → skip the break entirely (no URL emitted) and
  print a WARNING.
- If any bars are trimmed → log INFO with the leading and trailing counts.

**Implementation — `source/mapping.py`:**

Add `trim_empty_bars(tracks)` returning a result object:

```python
@dataclass
class TrimResult:
    tracks: list[MappedTrack]
    lead_bars: int
    trail_bars: int
    all_empty: bool
```

Algorithm:
1. `bar_count = len(tracks[0].notes) // 16`
2. Count `lead_bars`: walk bars from 0 upward until a non-`'0'` step is found in any track.
3. Count `trail_bars`: walk bars from `bar_count - 1` downward until a non-`'0'` step is found.
4. If `lead_bars + trail_bars >= bar_count` → return `TrimResult(all_empty=True, ...)`.
5. `start = lead_bars * 16`, `end = (bar_count - trail_bars) * 16`.
6. For each track: slice `notes[start:end]`; keep only polyrhythms fully within
   `[start, end)` and shift their indices by `-start`.

**Integration — `source/__main__.py`** (after `map_break()`):

```python
result = trim_empty_bars(tracks)
if result.all_empty:
    logger.warning("Break %d \"%s\" — all bars empty, skipping.", num, brk.name)
    continue
if result.lead_bars or result.trail_bars:
    logger.info(
        "Break %d \"%s\" — trimmed %d leading + %d trailing empty bars.",
        num, brk.name, result.lead_bars, result.trail_bars,
    )
tracks = result.tracks
n_bars = max(len(t.notes) for t in tracks) // 16
```