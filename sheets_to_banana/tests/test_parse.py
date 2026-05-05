"""Tests for parse.py — Increment 2.

Each test builds a minimal CSV string and asserts on the parsed output.
This lets you verify the parser without needing a real Google Sheet.
"""

import textwrap
import pytest
from sheets_to_banana.parse import parse_sheet, Break, PolyGroup


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


def test_levada_expands_to_pattern_for_caixa():
    """'Levada' spanning 16 cols on Caixa should expand to the full levada/Caixa pattern."""
    notes = ['Levada'] + [''] * 15 + ['X'] + [''] * 47  # keyword spans 16, then a note
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    expected = 'X X x / X x / x X x / x X x / x'.split()
    assert track[:16] == expected
    assert track[16] == 'X'


def test_levada_beat_position_selects_correct_slice():
    """A 4-col levada on beat 2 (col 4) should yield notes 5-8, not notes 1-4."""
    pattern = 'X X x / X x / x X x / x X x / x'.split()
    # beat 1: levada cols 0-3, beat 2: levada cols 4-7, beat 3: X, beat 4: empty
    notes = ['levada'] + [''] * 3 + ['levada'] + [''] * 3 + ['X'] + [''] * 55
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    assert track[0:4] == pattern[0:4]   # beat 1 → notes 1-4
    assert track[4:8] == pattern[4:8]   # beat 2 → notes 5-8
    assert track[8] == 'X'


def test_virada_expands_to_pattern_for_caixa():
    """'Virada' spanning 16 cols on Caixa should expand to the virada/Caixa pattern."""
    notes = ['Virada'] + [''] * 15 + [''] * 48
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    expected = 'X X x / X 0 x 0'.split()
    assert track[:8] == expected


def test_keyword_case_insensitive():
    """'LEVADA', 'Levada', and 'levada' should all expand to the same pattern."""
    expected_first = 'X X x / X x / x X x / x X x / x'.split()[0]
    for keyword in ('LEVADA', 'Levada', 'levada'):
        notes = [keyword] + [''] * 15 + [''] * 48
        csv_text = make_csv(
            break_header('B'),
            section_label(),
            instrument_row('Caixa', notes),
        )
        assert parse_sheet(csv_text)[0].tracks['Caixa'][0] == expected_first


def test_unknown_keyword_fills_with_rests():
    """An unrecognised keyword should fill its span with rests (with a warning)."""
    notes = ['zarabatana'] + [''] * 15 + [''] * 48
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Caixa']
    assert all(n == '0' for n in track[:16])


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


# ── 6/8 cells (Increment 8) ──────────────────────────────────────────────────

def test_68_cell_detected_as_polygroup():
    """A 4-column merged cell (1 filled + 3 empty) produces a PolyGroup."""
    notes = ['X X X'] + [''] * 3 + [''] * 60
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    brk = parse_sheet(csv_text)[0]
    assert 'Repique' in brk.polygroups
    pgs = brk.polygroups['Repique']
    assert len(pgs) == 1
    pg = pgs[0]
    assert pg.start == 0
    assert pg.end == 3
    assert pg.notes == ['X', 'X', 'X']


def test_68_cell_replaced_with_rests_in_track():
    """The 4 columns of a 6/8 cell become rests in the flat notes track."""
    notes = ['X X X'] + [''] * 3 + [''] * 60
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    track = parse_sheet(csv_text)[0].tracks['Repique']
    assert all(n == '0' for n in track[:4])


def test_68_slot_assignment_no_leading_trailing():
    """'X O' with no outer spaces → pause in middle → ['X', '0', 'O']."""
    notes = ['X O'] + [''] * 3 + [''] * 60
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    pg = parse_sheet(csv_text)[0].polygroups['Repique'][0]
    assert pg.notes == ['X', '0', 'O']


def test_68_slot_assignment_leading_space():
    """' X O' with leading space → pause at start → ['0', 'X', 'O']."""
    import io, csv as csv_mod
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(['B'])
    writer.writerow(['1 - 4'])
    writer.writerow(['Repique', ' X O', '', '', ''] + [''] * 60)
    brk = parse_sheet(buf.getvalue())[0]
    pg = brk.polygroups['Repique'][0]
    assert pg.notes == ['0', 'X', 'O']


def test_68_slot_assignment_trailing_space():
    """'X O ' with trailing space → pause at end → ['X', 'O', '0']."""
    import io, csv as csv_mod
    buf = io.StringIO()
    writer = csv_mod.writer(buf)
    writer.writerow(['B'])
    writer.writerow(['1 - 4'])
    writer.writerow(['Repique', 'X O ', '', '', ''] + [''] * 60)
    brk = parse_sheet(buf.getvalue())[0]
    pg = brk.polygroups['Repique'][0]
    assert pg.notes == ['X', 'O', '0']


def test_68_cell_truncated_warns_on_excess_tokens(caplog):
    """More than 3 tokens in a 6/8 cell emits a warning and keeps first 3."""
    import logging
    notes = ['X X X X'] + [''] * 3 + [''] * 60
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    with caplog.at_level(logging.WARNING):
        brk = parse_sheet(csv_text)[0]
    pg = brk.polygroups['Repique'][0]
    assert len(pg.notes) == 3
    assert pg.notes == ['X', 'X', 'X']
    assert 'truncating' in caplog.text.lower()


def test_68_cell_start_accounts_for_bar_group_offset():
    """In the second bar group (offset=64) the PolyGroup start is 64 + col."""
    notes_g1 = [''] * 64
    notes_g2 = ['X X X'] + [''] * 3 + [''] * 60
    csv_text = make_csv(
        break_header('B'),
        section_label('1 - 4'),
        instrument_row('Repique', notes_g1),
        empty_row(),
        section_label('5 - 8'),
        instrument_row('Repique', notes_g2),
    )
    pgs = parse_sheet(csv_text)[0].polygroups['Repique']
    assert len(pgs) == 1
    assert pgs[0].start == 64
    assert pgs[0].end == 67


def test_two_consecutive_68_cells_are_independent():
    """Two adjacent 4-column 6/8 cells produce two separate PolyGroups."""
    notes = (['X X X'] + [''] * 3
           + ['x x x'] + [''] * 3
           + [''] * 58)
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    pgs = parse_sheet(csv_text)[0].polygroups['Repique']
    assert len(pgs) == 2
    assert pgs[0].start == 0 and pgs[0].end == 3
    assert pgs[1].start == 4 and pgs[1].end == 7


def test_keyword_not_detected_as_68_cell():
    """A keyword (no space in content) spanning 4 columns is NOT a 6/8 cell."""
    notes = ['Levada'] + [''] * 15 + [''] * 48
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', notes),
    )
    brk = parse_sheet(csv_text)[0]
    assert 'Caixa' not in brk.polygroups or brk.polygroups['Caixa'] == []


def test_4col_span_required_not_3():
    """A merged cell with only 2 trailing empty cells (3-col span) is not a 6/8 cell."""
    notes = ['X X X'] + [''] * 2 + ['X'] + [''] * 59
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Repique', notes),
    )
    brk = parse_sheet(csv_text)[0]
    assert 'Repique' not in brk.polygroups or brk.polygroups['Repique'] == []


def test_break_without_68_cells_has_empty_polygroups():
    """A break with no 6/8 cells has an empty polygroups dict."""
    csv_text = make_csv(
        break_header('B'),
        section_label(),
        instrument_row('Caixa', ['X'] + [''] * 63),
    )
    brk = parse_sheet(csv_text)[0]
    assert brk.polygroups == {}


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
