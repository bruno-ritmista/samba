# sheets_to_banana — Design Plan

Reads a publicly shared Google Sheet containing Sapucaiu no Samba percussion notes
and produces a shareable BananaDrum URL.

## Architecture: 5 increments

### Increment 1 — fetch.py
Converts a Google Sheets URL into CSV text using the free CSV export endpoint
(no API key needed for public sheets).

### Increment 2 — parse.py
Parses the CSV into `Break` objects. Each break holds one dict mapping instrument
name → full note sequence (all bar groups concatenated into one flat list).
The Z-pattern layout (bars 1–4, then 5–8, …) is stitched together automatically.

### Increment 3 — mapping.py
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

### Increment 4 — encode.py
Implements the BananaDrum URL encoding (replicates the TypeScript in
`packages/bananadrum-core/src/prod/serialisation/`):
- Notes are treated as digits of a base-N number (last step = LSB)
- N = number of note styles + 1 (for rest)
- The number is encoded in base 64 using `0-9a-zA-Z~_`

**Bases per instrument:**
`'0'`=3, `'1'`=3, `'2'`=3, `'3'`=8, `'5'`=5, `'6'`=4, `'7'`=3, `'8'`=3, `'9'`=3

**URL format:** `https://bananadrum.net/?a2=4-4.{tempo}.{n_bars}.1-4.16.{track1}.{track2}...`

### Increment 6 — merged_cells.py
Handles note cells that contain multiple note characters separated by spaces
(e.g. `'O         S'`, `'S    O   O'`). These arise from merged cells in the
Google Sheet and represent rhythmic subdivisions that don't fit into the
standard 1/16th-note grid — either **triplets** or **6/8 time**.

**Problem:** BananaDrum's grid is fixed at 1/16th notes. A merged cell spanning
N columns that contains K note characters represents K evenly-spaced hits inside
N sixteenth-note slots — which is only expressible in BananaDrum if K divides N.

**Approach (to be designed):**
- Detect merged-cell strings during parse: a note cell whose value contains
  embedded whitespace (after stripping) is a merged-cell value.
- Record the raw string and the number of columns it spans (inferred from how
  many following empty cells belong to the same merge region).
- Quantise the K hits onto the N-slot grid using nearest-sixteenth rounding, or
  flag the cell as "non-quantisable" and warn the user.
- Common cases to support:
  - 2 hits in 4 slots → hits at slots 0 and 2 (straight eighth notes)
  - 3 hits in 4 slots → triplet → warn/skip (not representable exactly)
  - 2 hits in 3 slots → hits at slots 0 and 2 (dotted-eighth + sixteenth)

**Out of scope for now:** actual 6/8 arrangements; only handle the cases that
can be losslessly mapped onto the 1/16th grid.

### Increment 5 — main.py
CLI entry point:
```
python -m sheets_to_banana <sheets_url> [--break 0] [--tempo 120]
```

### Increment 7 — keywords.py
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

## Verified encoding example
Low Surdo accent on beat 2 and beat 4 of 1 bar:
→ `https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm`  ✓ (tested in BananaDrum)
