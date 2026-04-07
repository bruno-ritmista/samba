"""Tests for parse.py — Increment 2.

Each test builds a minimal CSV string and asserts on the parsed output.
This lets you verify the parser without needing a real Google Sheet.
"""

import textwrap
import pytest
from sheets_to_banana.parse import parse_sheet, Break


# ── helpers ──────────────────────────────────────────────────────────────────

def make_csv(*rows: list[str]) -> str:
    """Build a CSV string from a list of rows (each row is a list of strings)."""
    import io, csv
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def section_label(bar_range: str = '1 - 4') -> list[str]:
    """A minimal section-label row (col 0 = bar range, rest empty)."""
    return [bar_range] + [''] * 64


def instrument_row(name: str, notes: list[str]) -> list[str]:
    """An instrument row with exactly 64 note cells."""
    padded = (notes + [''] * 64)[:64]
    return [name] + padded


def empty_row() -> list[str]:
    return [''] * 65


def break_header(name: str) -> list[str]:
    return [name] + [''] * 64


# ── basic structure ───────────────────────────────────────────────────────────

def test_empty_csv_returns_empty_list():
    assert parse_sheet('') == []


def test_single_break_has_correct_name():
    csv_text = make_csv(
        break_header('Break A'),
        section_label(),
        instrument_row('Caixa', ['X'] + [''] * 63),
    )
    breaks = parse_sheet(csv_text)
    assert len(breaks) == 1
    assert breaks[0].name == 'Break A'


def test_single_break_single_instrument():
    notes = ['X', '', 'X', ''] + [''] * 60
    csv_text = make_csv(
        break_header('Break A'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    breaks = parse_sheet(csv_text)
    assert 'Caixa' in breaks[0].tracks


def test_instrument_notes_length_is_64_per_bar_group():
    csv_text = make_csv(
        break_header('Break A'),
        section_label(),
        instrument_row('Caixa', ['X'] * 16 + [''] * 48),
    )
    breaks = parse_sheet(csv_text)
    assert len(breaks[0].tracks['Caixa']) == 64


# ── note normalisation ────────────────────────────────────────────────────────

def test_empty_cell_becomes_rest():
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', [''] * 64),
    )
    assert all(n == '0' for n in parse_sheet(csv_text)[0].tracks['Caixa'])


def test_levada_becomes_rest():
    notes = ['Levada'] + [''] * 63
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    assert parse_sheet(csv_text)[0].tracks['Caixa'][0] == '0'


def test_virada_becomes_rest():
    notes = ['Virada'] + [''] * 63
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    assert parse_sheet(csv_text)[0].tracks['Caixa'][0] == '0'


def test_levada_case_insensitive():
    """'LEVADA' and 'levada' should both become rest."""
    for keyword in ('LEVADA', 'Levada', 'levada'):
        notes = [keyword] + [''] * 63
        csv_text = make_csv(
            break_header('B'),
            section_label(),
            instrument_row('Caixa', notes),
        )
        assert parse_sheet(csv_text)[0].tracks['Caixa'][0] == '0'


def test_note_characters_preserved():
    """Note chars like X, 1, 2, O, OO, /, W, S, D should pass through unchanged."""
    chars = ['X', '1', '2', 'O', 'OO', '/', 'W', 'S', 'D', 'x', 'L', 'H']
    notes = chars + [''] * (64 - len(chars))
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Surdo 1a/"2a"', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Surdo 1a/"2a"']
    for i, ch in enumerate(chars):
        assert track[i] == ch


# ── Z-pattern: multiple bar groups concatenated ───────────────────────────────

def test_two_bar_groups_concatenated():
    """Notes from bars 1-4 and bars 5-8 are joined into one 128-step list."""
    notes_group1 = ['X'] + [''] * 63     # beat 1 in bar 1
    notes_group2 = [''] * 15 + ['X'] + [''] * 48  # beat 4 in bar 4 of group 2

    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Caixa', notes_group1),
        empty_row(),
        section_label('5 - 8'),
        instrument_row('Caixa', notes_group2),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    assert len(track) == 128
    assert track[0] == 'X'              # position 0 in group 1
    assert track[64 + 15] == 'X'        # position 15 in group 2


def test_three_bar_groups_concatenated():
    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Caixa', ['X'] + [''] * 63),
        empty_row(),
        section_label('5 - 8'),
        instrument_row('Caixa', [''] * 64),
        empty_row(),
        section_label('9 - 12'),
        instrument_row('Caixa', [''] * 63 + ['X']),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    assert len(track) == 192
    assert track[0] == 'X'
    assert track[191] == 'X'


# ── multiple breaks ───────────────────────────────────────────────────────────

def test_two_breaks_returned():
    csv_text = make_csv(
        break_header('Break A'),
        section_label(),
        instrument_row('Caixa', ['X'] + [''] * 63),
        empty_row(),
        break_header('Break B'),
        section_label(),
        instrument_row('Repique', ['X'] + [''] * 63),
    )
    breaks = parse_sheet(csv_text)
    assert len(breaks) == 2
    assert breaks[0].name == 'Break A'
    assert breaks[1].name == 'Break B'


def test_breaks_have_independent_tracks():
    csv_text = make_csv(
        break_header('Break A'),
        section_label(),
        instrument_row('Caixa', ['X'] + [''] * 63),
        empty_row(),
        break_header('Break B'),
        section_label(),
        instrument_row('Repique', ['X'] + [''] * 63),
    )
    breaks = parse_sheet(csv_text)
    assert 'Caixa' in breaks[0].tracks
    assert 'Caixa' not in breaks[1].tracks
    assert 'Repique' not in breaks[0].tracks
    assert 'Repique' in breaks[1].tracks


# ── absent instruments get padded ─────────────────────────────────────────────

def test_instrument_absent_from_second_bar_group_padded_with_rests():
    """Caixa is in group 1 but not group 2 → its track is padded to 128 steps."""
    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Caixa', ['X'] + [''] * 63),
        instrument_row('Repique', ['X'] + [''] * 63),
        empty_row(),
        section_label('5 - 8'),
        instrument_row('Repique', ['X'] + [''] * 63),  # Caixa absent here
    )
    breaks = parse_sheet(csv_text)
    caixa = breaks[0].tracks['Caixa']
    repique = breaks[0].tracks['Repique']
    assert len(caixa) == 128
    assert len(repique) == 128
    assert all(n == '0' for n in caixa[64:])  # second group is all rests


def test_instrument_absent_from_first_bar_group_padded_with_rests():
    """Repique is not in group 1 but is in group 2 → 64 leading rests."""
    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Caixa', ['X'] + [''] * 63),
        empty_row(),
        section_label('5 - 8'),
        instrument_row('Caixa', ['X'] + [''] * 63),
        instrument_row('Repique', ['X'] + [''] * 63),
    )
    breaks = parse_sheet(csv_text)
    repique = breaks[0].tracks['Repique']
    assert len(repique) == 128
    assert all(n == '0' for n in repique[:64])  # first group is all rests


# ── section label row is not treated as an instrument ─────────────────────────

def test_section_label_row_not_added_as_instrument():
    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Caixa', ['X'] + [''] * 63),
    )
    tracks = parse_sheet(csv_text)[0].tracks
    for key in tracks:
        assert not key.strip().replace(' ', '').replace('-', '').isdigit(), \
            f"Section label '{key}' should not appear as an instrument"


# ── short rows don't crash ────────────────────────────────────────────────────

def test_short_instrument_row_padded_to_64():
    """A row with fewer than 65 columns should be treated as having trailing rests."""
    import io, csv
    # Manually write a row with only 5 note columns
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Break B'])
    writer.writerow(['1 - 4'])
    writer.writerow(['Caixa', 'X', '', 'X', '', 'X'])   # only 5 note cols
    track = parse_sheet(buf.getvalue())[0].tracks['Caixa']
    assert len(track) == 64
    assert track[0] == 'X'
    assert track[2] == 'X'
    assert track[4] == 'X'
    assert all(n == '0' for n in track[5:])


# ── notes before any break header ────────────────────────────────────────────

def test_orphaned_bar_group_creates_unnamed_break():
    """If notes appear before any break header, an unnamed Break is created."""
    csv_text = make_csv(
        section_label('1 - 4'),
        instrument_row('Caixa', ['X'] + [''] * 63),
    )
    breaks = parse_sheet(csv_text)
    assert len(breaks) == 1
    assert breaks[0].name == ''
    assert 'Caixa' in breaks[0].tracks
