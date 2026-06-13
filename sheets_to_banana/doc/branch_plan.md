# Branch plan: `feature/add_keyword_corte_for_surdo3` (issue #6)

## Issue

Support the `Corte` keyword for the **Surdo 3** row (BananaDrum "High Surdo",
track id `7`, `_classify` kind `high_surdo`). Two cases:

- **Short corte**: 3 beats, sheet places `Corte` in single-beat cells at
  beat 2, beat 3, beat 4 of bar 1.
- **Long corte**: 7 beats, sheet places `Corte` in single-beat cells at
  bar 1 beat 2-4 and bar 2 beat 1-4 (7 consecutive `Corte` cells).

Confirmed from the linked sheet (`Surdo 3` row):

```
Short: ,,,,,Corte,,,,Corte,,,,Corte,,,,            (cols 5,9,13 → 0-based idx 4,8,12)
Long:  ,,,,,Corte,,,,Corte,,,,Corte,,,,Corte,,,,Corte,,,,Corte,,,,Corte
                                                    (idx 4,8,12,16,20,24,28)
```

Each `Corte` cell is a normal single-beat keyword cell (1 cell + 3 empty
cells = 4 columns), consistent with the convention from issue #7/#2
(`expand_keywords` caps span at 4 / one beat — see
`sheets_to_banana/src/keywords.py:68`).

## Decoded target pattern (from expected URLs)

Decoding the `7...` track segments from the issue's expected output URLs
(base-3, High Surdo: `X`→`1`, `0`→rest):

- Short corte (`74Tw`, 16 steps): hits at 0-based indices `6, 10, 13, 15`
- Long corte (`7cuZDqjc`, 32 steps): hits at 0-based indices
  `6, 10, 14, 18, 22, 26, 29, 31`

Grouping by beat (4 steps each), relative to each beat's start:

| Beat | Short corte | Long corte |
|---|---|---|
| bar1 beat2 (idx 4-7)  | rel pos **2** (idx6) | rel pos **2** (idx6) |
| bar1 beat3 (idx 8-11) | rel pos **2** (idx10) | rel pos **2** (idx10) |
| bar1 beat4 (idx 12-15)| rel pos **1,3** (idx13,15) ← **last** | rel pos **2** (idx14) |
| bar2 beat1 (idx 16-19)| — | rel pos **2** (idx18) |
| bar2 beat2 (idx 20-23)| — | rel pos **2** (idx22) |
| bar2 beat3 (idx 24-27)| — | rel pos **2** (idx26) |
| bar2 beat4 (idx 28-31)| — | rel pos **1,3** (idx29,31) ← **last** |

**Pattern rule**: every `Corte` beat that is followed by another `Corte`
beat ("mid") expands to `0 0 X 0`. The **last** `Corte` beat in a
consecutive run ("end") expands to `0 X 0 X`. This single rule produces
both the short (3-beat) and long (7-beat) corte exactly.

## Implementation

### `sheets_to_banana/src/keywords.py`

1. Add two new pattern constants near `_KEYWORD_TABLE`:

   ```python
   _CORTE_MID = '0 0 X 0'.split()
   _CORTE_END = '0 X 0 X'.split()
   ```

2. Add a small lookahead helper that decides whether the `Corte` cell at
   position `i` (span `span`, after the existing cap-at-4 logic) is the
   last one in a consecutive run of `Corte` cells:

   ```python
   def _corte_pattern(cells: list[str], i: int, span: int) -> list[str]:
       next_i = i + span
       is_last = not (next_i < len(cells) and cells[next_i].lower() == 'corte')
       return _CORTE_END if is_last else _CORTE_MID
   ```

3. In `expand_keywords`, where `pattern` is currently resolved purely from
   `_KEYWORD_TABLE`, special-case `corte` for `high_surdo` before the table
   lookup (keep the table lookup as the fallback for any other
   instrument, which preserves the existing "unsupported keyword" warning
   path):

   ```python
   if cell.lower() == 'corte' and kind == 'high_surdo':
       pattern = _corte_pattern(cells, i, span)
   else:
       pattern = _KEYWORD_TABLE.get((cell.lower(), kind))
   ```

   The rest of the offset/tiling logic is unchanged — since `Corte` cells
   are always beat-aligned (`i % 4 == 0`) and the patterns are exactly 4
   notes long, `offset` is always `0` and the slice is just the pattern
   itself.

No changes needed in `parse.py`, `mapping.py`, or `encode.py` — `Corte`
flows through the same `high_surdo` mapping (`X`→`'1'`) and encoding paths
as any other note character.

## Tests

Add `sheets_to_banana/tests/test_keywords.py` (new file, following the
style of the keyword tests currently in `tests/test_parse.py`):

- `test_corte_mid_beat_pattern`: a single `Corte` cell immediately followed
  by another `Corte` cell expands to `0 0 X 0`.
- `test_corte_last_beat_pattern`: a `Corte` cell with no following `Corte`
  cell expands to `0 X 0 X`.
- `test_corte_case_insensitive`: `'CORTE'`, `'Corte'`, `'corte'` all expand
  the same way.
- `test_corte_unsupported_for_other_instruments`: a `Corte` cell on e.g.
  `Caixa` falls back to rests + warning (existing unsupported-keyword
  behaviour).

Add to `sheets_to_banana/tests/test_parse.py` (or the new keywords test
file) two end-to-end tests reproducing the issue's two example breaks:

- `test_short_corte_full_pattern`: `Surdo 3` row with `Corte` at
  idx 4, 8, 12 (beat2-4 of bar 1, rest empty) → after
  `parse_sheet` + `map_break`, the High Surdo track's 16 notes match
  `0,0,0,0,0,0,X,0,0,0,X,0,0,X,0,X` (mapped to `0/1`), matching the
  decoded `74Tw` segment.
- `test_long_corte_full_pattern`: `Surdo 3` row with `Corte` at
  idx 4,8,12,16,20,24,28 (bar1 beat2 → bar2 beat4) → 32-note track
  matches the decoded `7cuZDqjc` segment.

Optionally, extend one of these into a full `encode_url` round-trip
assertion (`track_parts` segment `== '74Tw'` / `'7cuZDqjc'`) to pin the
exact issue acceptance criteria.

## Files touched

- `sheets_to_banana/src/keywords.py` — add `Corte` pattern constants +
  lookahead dispatch (the only production code change)
- `sheets_to_banana/tests/test_keywords.py` — new file, unit tests for
  `Corte` expansion
- `sheets_to_banana/tests/test_parse.py` — end-to-end short/long corte
  tests (or co-locate in `test_keywords.py`)
