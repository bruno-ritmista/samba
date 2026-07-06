"""Tests for mapping.py — Increment 3.

Each test builds a minimal Break and asserts on the mapped output.
"""

import pytest
from sheet_to_banana.parse import Break, PolyGroup
from sheet_to_banana.mapping import map_break, MappedTrack, MappedPolyrhythm


# ── helpers ───────────────────────────────────────────────────────────────────

def make_break(instrument: str, notes: list[str],
               polygroups: dict | None = None) -> Break:
    return Break(name='Test', tracks={instrument: notes},
                 polygroups=polygroups or {})


def single_note(char: str, length: int = 16) -> list[str]:
    """One note at position 0, rest for the remaining steps."""
    return [char] + ['0'] * (length - 1)


def get_track(tracks: list[MappedTrack], instrument_id: str) -> MappedTrack:
    matches = [t for t in tracks if t.instrument_id == instrument_id]
    assert matches, f"No track found for instrument_id='{instrument_id}'"
    return matches[0]


# ── instrument classification ─────────────────────────────────────────────────

def test_agogo_recognised():
    tracks = map_break(make_break('Agogô', ['L'] + ['0'] * 15))
    assert get_track(tracks, '0').instrument_id == '0'


def test_agogo_ascii_variant():
    tracks = map_break(make_break('Agogo', ['L'] + ['0'] * 15))
    assert get_track(tracks, '0').instrument_id == '0'


def test_chocalho_recognised():
    tracks = map_break(make_break('Chocalho', ['X'] + ['0'] * 15))
    assert get_track(tracks, '1').instrument_id == '1'


def test_tamborim_recognised():
    tracks = map_break(make_break('Tamborim', ['X'] + ['0'] * 15))
    assert get_track(tracks, '2').instrument_id == '2'


def test_repique_recognised():
    tracks = map_break(make_break('Repique', ['X'] + ['0'] * 15))
    assert get_track(tracks, '3').instrument_id == '3'


def test_repinique_variant_recognised():
    tracks = map_break(make_break('Repinique', ['X'] + ['0'] * 15))
    assert get_track(tracks, '3').instrument_id == '3'


def test_caixa_recognised():
    tracks = map_break(make_break('Caixa', ['X'] + ['0'] * 15))
    assert get_track(tracks, '5').instrument_id == '5'


def test_timbau_recognised():
    tracks = map_break(make_break('Timbau', ['S'] + ['0'] * 15))
    assert get_track(tracks, '6').instrument_id == '6'


def test_surdo_mor_is_high_surdo():
    tracks = map_break(make_break('Surdo Mor', ['X'] + ['0'] * 15))
    assert get_track(tracks, '7').instrument_id == '7'


def test_surdo_3a_is_high_surdo():
    tracks = map_break(make_break('Surdo 3a', ['X'] + ['0'] * 15))
    assert get_track(tracks, '7').instrument_id == '7'


def test_surdo_split_produces_two_tracks():
    tracks = map_break(make_break('Surdo 1a/"2a"', ['1'] + ['0'] * 15))
    ids = [t.instrument_id for t in tracks]
    assert '9' in ids   # Low Surdo
    assert '8' in ids   # Mid Surdo


def test_unknown_instrument_skipped():
    tracks = map_break(make_break('Pandeiro', ['X'] + ['0'] * 15))
    assert tracks == []


# ── Agogô note mapping ────────────────────────────────────────────────────────

def test_agogo_L_maps_to_1():
    t = get_track(map_break(make_break('Agogô', single_note('L'))), '0')
    assert t.notes[0] == '1'


def test_agogo_H_maps_to_2():
    t = get_track(map_break(make_break('Agogô', single_note('H'))), '0')
    assert t.notes[0] == '2'


def test_agogo_unknown_maps_to_rest():
    t = get_track(map_break(make_break('Agogô', single_note('X'))), '0')
    assert t.notes[0] == '0'


# ── Chocalho note mapping ─────────────────────────────────────────────────────

def test_chocalho_X_maps_to_1():
    t = get_track(map_break(make_break('Chocalho', single_note('X'))), '1')
    assert t.notes[0] == '1'


# ── Tamborim note mapping ─────────────────────────────────────────────────────

def test_tamborim_X_maps_to_1():
    t = get_track(map_break(make_break('Tamborim', single_note('X'))), '2')
    assert t.notes[0] == '1'


# ── Repique note mapping ──────────────────────────────────────────────────────

@pytest.mark.parametrize('char,expected', [
    ('X', '1'), ('x', '2'), ('/', '3'), ('K', '4'),
    ('W', '5'), ('O', '6'), ('S', '7'), ('0', '0'),
])
def test_repique_note_mapping(char, expected):
    t = get_track(map_break(make_break('Repique', single_note(char))), '3')
    assert t.notes[0] == expected


# ── Caixa note mapping ────────────────────────────────────────────────────────

@pytest.mark.parametrize('char,expected', [
    ('X', '1'), ('x', '2'), ('W', '3'), ('/', '4'), ('0', '0'),
])
def test_caixa_note_mapping(char, expected):
    t = get_track(map_break(make_break('Caixa', single_note(char))), '5')
    assert t.notes[0] == expected


# ── Timbau note mapping ───────────────────────────────────────────────────────

def test_timbau_S_maps_to_2():
    t = get_track(map_break(make_break('Timbau', single_note('S'))), '6')
    assert t.notes[0] == '2'


def test_timbau_O_maps_to_3():
    t = get_track(map_break(make_break('Timbau', single_note('O'))), '6')
    assert t.notes[0] == '3'


def test_timbau_OO_maps_to_rest():
    """OO (two 1/32nd tones) is skipped — treated as rest."""
    t = get_track(map_break(make_break('Timbau', single_note('OO'))), '6')
    assert t.notes[0] == '0'


# ── High Surdo note mapping ───────────────────────────────────────────────────

def test_high_surdo_X_maps_to_1():
    t = get_track(map_break(make_break('Surdo Mor', single_note('X'))), '7')
    assert t.notes[0] == '1'


def test_high_surdo_D_maps_to_2():
    t = get_track(map_break(make_break('Surdo Mor', single_note('D'))), '7')
    assert t.notes[0] == '2'


def test_high_surdo_W_maps_to_rest():
    """W (roll) is not supported in High Surdo → rest."""
    t = get_track(map_break(make_break('Surdo Mor', single_note('W'))), '7')
    assert t.notes[0] == '0'


# ── Surdo split note mapping ──────────────────────────────────────────────────

def test_surdo_1_hits_low_surdo_only():
    tracks = map_break(make_break('Surdo 1a/"2a"', single_note('1')))
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert low.notes[0] == '1'
    assert mid.notes[0] == '0'


def test_surdo_2_hits_mid_surdo_only():
    tracks = map_break(make_break('Surdo 1a/"2a"', single_note('2')))
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert low.notes[0] == '0'
    assert mid.notes[0] == '1'


def test_surdo_O_hits_both_tracks():
    """'O' means both Surdo 1 and Surdo 2 play simultaneously."""
    tracks = map_break(make_break('Surdo 1a/"2a"', single_note('O')))
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert low.notes[0] == '1'
    assert mid.notes[0] == '1'


def test_surdo_rest_maps_to_rest_on_both_tracks():
    tracks = map_break(make_break('Surdo 1a/"2a"', ['0'] * 16))
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert all(n == '0' for n in low.notes)
    assert all(n == '0' for n in mid.notes)


# ── track length preserved ────────────────────────────────────────────────────

def test_output_length_matches_input():
    notes = ['X', '0', 'X', '0'] * 16   # 64 steps
    t = get_track(map_break(make_break('Caixa', notes)), '5')
    assert len(t.notes) == 64


def test_surdo_split_track_length_matches_input():
    notes = ['1', '0', '2', 'O'] * 16   # 64 steps
    tracks = map_break(make_break('Surdo 1a/"2a"', notes))
    for t in tracks:
        assert len(t.notes) == 64


# ── polyrhythm translation (Increment 8) ─────────────────────────────────────

def test_no_polygroups_gives_empty_polyrhythms():
    t = get_track(map_break(make_break('Caixa', ['0'] * 16)), '5')
    assert t.polyrhythms == []


def test_polygroup_translated_to_mapped_polyrhythm():
    pg = PolyGroup(start=0, end=3, notes=['X'] * 3)
    brk = make_break('Repique', ['0'] * 16, {'Repique': [pg]})
    t = get_track(map_break(brk), '3')
    assert len(t.polyrhythms) == 1
    mp = t.polyrhythms[0]
    assert mp.start == 0
    assert mp.end == 3
    assert mp.notes == ['1'] * 3   # 'X' → '1' for Repique


def test_polyrhythm_start_end_preserved():
    pg = PolyGroup(start=32, end=35, notes=['x'] * 3)
    brk = make_break('Caixa', ['0'] * 64, {'Caixa': [pg]})
    mp = get_track(map_break(brk), '5').polyrhythms[0]
    assert mp.start == 32
    assert mp.end == 35


def test_multiple_polygroups_all_translated():
    pg1 = PolyGroup(start=0, end=3, notes=['X'] * 3)
    pg2 = PolyGroup(start=4, end=7, notes=['x'] * 3)
    brk = make_break('Caixa', ['0'] * 16, {'Caixa': [pg1, pg2]})
    polys = get_track(map_break(brk), '5').polyrhythms
    assert len(polys) == 2
    assert polys[0].notes == ['1'] * 3
    assert polys[1].notes == ['2'] * 3


def test_surdo_split_polyrhythm_translated_for_both_tracks():
    """'O' in a surdo 6/8 cell hits both Low and Mid Surdo polyrhythms."""
    pg = PolyGroup(start=0, end=3, notes=['O'] * 3)
    brk = make_break('Surdo 1a/"2a"', ['0'] * 16, {'Surdo 1a/"2a"': [pg]})
    tracks = map_break(brk)
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert len(low.polyrhythms) == 1
    assert len(mid.polyrhythms) == 1
    assert low.polyrhythms[0].notes == ['1'] * 3
    assert mid.polyrhythms[0].notes == ['1'] * 3


def test_surdo_split_polyrhythm_1_only_on_low():
    pg = PolyGroup(start=0, end=3, notes=['1'] * 3)
    brk = make_break('Surdo 1a/"2a"', ['0'] * 16, {'Surdo 1a/"2a"': [pg]})
    tracks = map_break(brk)
    low = get_track(tracks, '9')
    mid = get_track(tracks, '8')
    assert low.polyrhythms[0].notes == ['1'] * 3
    assert mid.polyrhythms[0].notes == ['0'] * 3


# ── multiple instruments in one break ─────────────────────────────────────────

def test_multiple_instruments_all_mapped():
    brk = Break(name='Test', tracks={
        'Caixa':    ['X'] + ['0'] * 15,
        'Repique':  ['X'] + ['0'] * 15,
        'Tamborim': ['X'] + ['0'] * 15,
    })
    ids = {t.instrument_id for t in map_break(brk)}
    assert ids == {'5', '3', '2'}
