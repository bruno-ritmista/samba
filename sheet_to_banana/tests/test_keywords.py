"""Tests for keywords.py — the `Corte` keyword on Surdo 3 (issue #6).

`Corte` is a run-length shorthand on the High Surdo (Surdo 3) row:
  - a corte beat followed by another corte beat → '0 0 X 0' (mid)
  - the last corte beat in a run               → '0 X 0 X' (end)

These unit tests exercise expand_keywords directly; end-to-end short/long
corte coverage (through parse_sheet + map_break + encode_url) lives in
test_parse.py.
"""

import pytest
from sheet_to_banana.keywords import expand_keywords


def _corte_beat(cells: list[str], beat: int) -> list[str]:
    """Return the 4 expanded cells for a given 0-based beat index."""
    result = expand_keywords('Surdo 3', cells)
    return result[beat * 4:beat * 4 + 4]


def test_corte_mid_beat_pattern():
    """A Corte cell immediately followed by another Corte cell → '0 0 X 0'."""
    # beat 1: Corte, beat 2: Corte (so beat 1 is 'mid')
    cells = (['Corte'] + [''] * 3) * 2 + [''] * 56
    assert _corte_beat(cells, 0) == '0 0 X 0'.split()


def test_corte_last_beat_pattern():
    """A Corte cell with no following Corte cell → '0 X 0 X'."""
    # single Corte on beat 1, nothing after
    cells = ['Corte'] + [''] * 63
    assert _corte_beat(cells, 0) == '0 X 0 X'.split()


def test_corte_case_insensitive():
    """'CORTE', 'Corte', and 'corte' all expand identically."""
    for keyword in ('CORTE', 'Corte', 'corte'):
        cells = [keyword] + [''] * 63
        assert _corte_beat(cells, 0) == '0 X 0 X'.split()


def test_corte_unsupported_for_other_instruments():
    """Corte on a non-High-Surdo row falls back to rests (unsupported keyword)."""
    cells = ['Corte'] + [''] * 63
    result = expand_keywords('Caixa', cells)
    assert result[0:4] == ['0', '0', '0', '0']


# ── 'Subida' on Repique (issue #14) ──────────────────────────────────────────
#
# `Subida` is also a run-length shorthand on the Repique row:
#   - the last subida beat in a run        → '0 W 0 O' (climax)
#   - the second-to-last beat in a run     → 'X 0 / /' (penultimate)
#   - any earlier beat in the run          → 'X 0 / 0' (lead-in)


def test_short_subida_pattern():
    """A 2-beat subida run expands to the penultimate + last patterns."""
    cells = (['Subida'] + [''] * 3) * 2 + [''] * 56
    result = expand_keywords('Repique', cells)
    assert result[0:4] == 'X 0 / /'.split()
    assert result[4:8] == '0 W 0 O'.split()


def test_regular_subida_pattern():
    """A 4-beat subida run expands to lead-in, lead-in, penultimate, last."""
    cells = (['Subida'] + [''] * 3) * 4 + [''] * 48
    result = expand_keywords('Repique', cells)
    assert result[0:4]   == 'X 0 / 0'.split()
    assert result[4:8]   == 'X 0 / 0'.split()
    assert result[8:12]  == 'X 0 / /'.split()
    assert result[12:16] == '0 W 0 O'.split()


def test_subida_case_insensitive():
    """'SUBIDA', 'Subida', and 'subida' all expand identically."""
    for keyword in ('SUBIDA', 'Subida', 'subida'):
        cells = [keyword] + [''] * 63
        result = expand_keywords('Repique', cells)
        assert result[0:4] == '0 W 0 O'.split()


def test_subida_unsupported_for_other_instruments():
    """Subida on a non-Repique row falls back to rests (unsupported keyword)."""
    cells = ['Subida'] + [''] * 63
    result = expand_keywords('Caixa', cells)
    assert result[0:4] == ['0', '0', '0', '0']
