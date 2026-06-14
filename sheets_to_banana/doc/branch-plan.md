# Branch plan: Issue #14 — add "subida" keyword for Repinique

## Context

Issue #14 asks for a new keyword `subida` (Portuguese: "rise"/build-up) that
the Repique track can use, mirroring the existing `Levada`/`Virada`/`Corte`
keyword mechanism in `sheets_to_banana/src/keywords.py`. Two variants exist
in the sheet, distinguished by how many consecutive `subida` cells appear
(one cell per beat, exactly like `Corte` on Surdo 3):

- **Regular subida** — 4 consecutive `subida` cells (1 full bar / 4 beats)
- **Short subida** — 2 consecutive `subida` cells (half bar / 2 beats)

Confirmed with the user:
- `_` in the issue's pattern strings = rest (`'0'`)
- repeated characters (`//`) = repeated single hits
- "short subida" is exactly the **last 2 beats** of "regular subida" — the
  climax. Regular adds 2 extra lead-in beats before that climax.

This decomposes into 3 per-beat patterns:
- `LEAD`  (lead-in beat, used for any beat before the final 2): `X 0 / 0`
- `PENULTIMATE` (2nd-to-last beat of the run): `X 0 / /`
- `LAST` (final beat of the run): `0 W 0 O`

Regular subida = LEAD, LEAD, PENULTIMATE, LAST.
Short subida = PENULTIMATE, LAST.

All characters (`X`, `0`, `/`, `W`, `O`) are already in `_REPIQUE` mapping
table in `mapping.py` (line 45) — no mapping changes needed.

## Implementation

### 1. `sheets_to_banana/src/keywords.py`

Add new pattern constants near `_CORTE_MID`/`_CORTE_END` (around line 34):

```python
_SUBIDA_LEAD = 'X 0 / 0'.split()
_SUBIDA_PENULTIMATE = 'X 0 / /'.split()
_SUBIDA_LAST = '0 W 0 O'.split()
```

Add a `_subida_pattern(cells, i, span)` helper, mirroring `_corte_pattern`
but with 2-step look-ahead (since subida has 3 distinct per-position
patterns, not just mid/end):

```python
def _subida_pattern(cells: list[str], i: int, span: int) -> list[str]:
    """Pick the subida sub-pattern for the cell at `i` based on how many
    more subida cells follow (forward look-ahead only, like _corte_pattern).

    The last cell in a run -> LAST, the second-to-last -> PENULTIMATE,
    any earlier cell -> LEAD.
    """
    next_i = i + span
    has_next = next_i < len(cells) and cells[next_i].lower() == 'subida'
    if not has_next:
        return _SUBIDA_LAST
    next_next_i = next_i + span
    has_next_next = next_next_i < len(cells) and cells[next_next_i].lower() == 'subida'
    return _SUBIDA_PENULTIMATE if not has_next_next else _SUBIDA_LEAD
```

In `expand_keywords`, add a branch alongside the existing Corte special-case:

```python
if cell.lower() == 'corte' and kind == 'high_surdo':
    pattern = _corte_pattern(cells, i, span)
elif cell.lower() == 'subida' and kind == 'repique':
    pattern = _subida_pattern(cells, i, span)
else:
    pattern = _KEYWORD_TABLE.get((cell.lower(), kind))
```

Since each returned pattern is exactly 4 elements (one beat) and `span` is
capped at 4, the existing offset/tiling logic (`offset = i % len(pattern)`,
slice `[offset:offset+span]`) reduces to taking the whole pattern — same as
how Corte already works. No changes needed to that logic or to `parse.py`.

### 2. Tests — `sheets_to_banana/tests/test_keywords.py`

Add a new section (mirroring the existing Corte tests), using
`expand_keywords('Repique', cells)`:

- `test_short_subida_pattern` — 2 consecutive `subida` cells (beats 1-2) →
  `X 0 / / 0 W 0 O`.split()
- `test_regular_subida_pattern` — 4 consecutive `subida` cells (beats 1-4) →
  `X 0 / 0 X 0 / 0 X 0 / / 0 W 0 O`.split()
- `test_subida_case_insensitive` — `SUBIDA`/`Subida`/`subida` all expand
  identically (single beat → `_SUBIDA_LAST`)
- `test_subida_unsupported_for_other_instruments` — `subida` on e.g. `Caixa`
  falls back to rests (existing `_KEYWORD_TABLE.get(...)` returns `None` →
  warning + `'0' * span`)

### 3. End-to-end tests — `sheets_to_banana/tests/test_parse.py`

Mirror `test_short_corte_full_pattern` / `test_long_corte_full_pattern`
(lines ~544-589): add `test_short_subida_full_pattern` and
`test_regular_subida_full_pattern` that build a CSV with `subida` cells on
the Repique row, run `parse_sheet` → `map_break` → `encode_url`, and assert
on the resulting Repique track segment of the URL (track id `'3'`).

## Verification

- `pytest sheets_to_banana/tests/test_keywords.py -v` — new subida unit tests pass
- `pytest sheets_to_banana/tests/test_parse.py -v` — new end-to-end subida tests pass
- `pytest sheets_to_banana/tests -v` — full suite still green (no regressions
  to Corte/Levada/Virada)

## Cleanup

Remove this file before merging to `main` (per the convention used on issue #7).
