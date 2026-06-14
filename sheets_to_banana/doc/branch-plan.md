# Plan: Resolve issue #10 — "3/4 beat with pause at start" misparsed

## Context

GitHub issue #10 reports that merged 4-column cells representing a 3/4
(triplet) beat with a pause/rest among the 3 notes are misinterpreted by
`sheets_to_banana/src/parse.py`. Two root causes were confirmed by tracing
the issue's example sheet
(`1dRzleJkezMSH844_jLYRy93TIrxFL93YeBQ6EUA63Lg`) and decoding both the
"observed" BananaDrum URL and the issue's "is" descriptions — the decoded
output matches the issue text exactly, confirming the cell→column mapping
and current behaviour:

| Cell (raw) | Current result | Cause |
|---|---|---|
| `"X    X"` (2 tokens, no outer spaces) | `[X,0,X]` | `_assign_poly_slots` "pause in middle" default — **already matches the convention, no change** |
| `"X"` (1 token, no spaces at all) | not detected → 4/4 `[X,0,0,0]` | detection requires a space; per user this is **intentional** (sheet would need editing to opt into 3/4) |
| `"      X"` (1 token, leading spaces only) | not detected → 4/4 `[X,0,0,0]` | **BUG 1**: detection strips the cell before checking for a space, so leading/trailing-only whitespace is lost |
| `"           X"` (1 token, leading spaces only) | not detected → 4/4 `[X,0,0,0]` | same as above |

### Confirmed convention (from issue author)

For a detected 4-column merged cell with fewer than 3 note tokens:
- If the cell **starts with whitespace**, there's a pause at the **start**.
- If the cell **ends with whitespace**, there's a pause at the **end**.
- If the cell starts with a note character, that note is at the **start**.
- If the cell ends with a note character, that note is at the **end**.
- If a single note has whitespace on **both** sides, the note is in the **middle**.
- A cell is only treated as a 3/4 polygroup if it contains **at least one
  space** somewhere (leading, trailing, or internal) — a bare `"X"` with no
  whitespace stays a normal 4/4 hit (unchanged behaviour).

Applying this to the 1-token case gives:
- leading space only → `['0', '0', token]` (pause-start, note-end)
- trailing space only → `[token, '0', '0']` (note-start, pause-end) — **already correct in current code**
- both leading and trailing space → `['0', token, '0']` (note in middle)

The 2-token branch in `_assign_poly_slots` already implements this rule
correctly (leading→`['0',t0,t1]`, trailing→`[t0,t1,'0']`, neither→`[t0,'0',t1]`)
and needs **no change**.

## Fix — `sheets_to_banana/src/parse.py`

### 1. `_extract_polygroups` — fix detection (around line 113)

Currently:
```python
raw_cell = note_cells[i]
cell = raw_cell.strip()   # stripped for detection checks
if (cell
        and ' ' in cell
        and all(c in _POLY_NOTE_CHARS for c in cell if c != ' ')):
```

`cell = raw_cell.strip()` removes leading/trailing whitespace *before* the
`' ' in cell` check, so a cell like `"      X"` (only leading spaces, no
internal space) is never detected. Change the space check to look at
`raw_cell` instead of the stripped `cell`:

```python
raw_cell = note_cells[i]
cell = raw_cell.strip()   # stripped for detection checks
if (cell
        and ' ' in raw_cell
        and all(c in _POLY_NOTE_CHARS for c in cell if c != ' ')):
```

### 2. `_assign_poly_slots` — fix the 1-token branch (around line 91-94)

Currently:
```python
    # len(tokens) == 1
    if has_leading:
        return ['0', tokens[0], '0']
    return [tokens[0], '0', '0']
```

This always treats leading whitespace as "pause in the middle", which is
wrong when there's *no* trailing whitespace (note should go at the end).
Replace with:

```python
    # len(tokens) == 1
    if has_leading and has_trailing:
        return ['0', tokens[0], '0']   # pause both sides -> note in middle
    if has_leading:
        return ['0', '0', tokens[0]]   # pause at start -> note at end
    return [tokens[0], '0', '0']       # note at start (trailing pause or none)
```

Update the function's docstring to describe the corrected leading/trailing/
both rule for single-token cells.

## Tests — `sheets_to_banana/tests/test_parse.py`

Add new cases alongside the existing `test_68_slot_assignment_*` tests
(around line 442), using the same `make_csv`/`instrument_row` helpers:

1. **Leading-space single token now detected**: cell `"      X"` (6 spaces +
   `X`) followed by 3 empty cells → `pg.notes == ['0', '0', 'X']`.
2. **Trailing-space single token (regression check)**: cell `"X      "`
   (already worked, but add explicit 1-token coverage) →
   `pg.notes == ['X', '0', '0']`.
3. **Both leading and trailing space, single token**: cell `"  X  "` →
   `pg.notes == ['0', 'X', '0']`.
4. **Bare single character still not detected (regression check)**: cell
   `"X"` with 3 trailing empty cells → `'Repique' not in brk.polygroups or
   brk.polygroups['Repique'] == []` (mirrors
   `test_break_without_68_cells_has_empty_polygroups` / existing
   `test_keyword_not_detected_as_68_cell` style).

Keep the existing 2-token tests (`test_68_slot_assignment_no_leading_trailing`,
`_leading_space`, `_trailing_space`) unchanged — they already match the
confirmed convention and should continue to pass.

## Verification

From `sheets_to_banana/`:
```bash
pytest tests/test_parse.py -v
pytest tests/ -v
```
All existing tests should continue to pass; the new tests should pass with
the two code changes above and fail without them (confirm by temporarily
reverting the fix).

## Out of scope / known limitations

- The example sheet's `bar1 beat2` (`"X    X"`) and `bar1 beat3` (`"X"`)
  cells don't change under this fix per the confirmed convention above —
  fixing those would require editing the example sheet's cell contents
  (adding trailing spaces), not a parsing change.
