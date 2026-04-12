"""Tests for encode.py — Increment 4.

The verified anchor: Low Surdo accent on beat 2 and beat 4 of 1 bar produces
https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm  (tested in BananaDrum).
"""

import pytest
from sheets_to_banana.encode import (
    encode_url, _url_encode_number, _encode_notes,
    _pack_polyrhythm_string, _encode_polyrhythms, _build_effective_notes,
)
from sheets_to_banana.mapping import MappedTrack, MappedPolyrhythm


# ── _url_encode_number ────────────────────────────────────────────────────────

def test_encode_zero():
    assert _url_encode_number(0) == '0'


def test_encode_single_digit():
    assert _url_encode_number(9) == '9'
    assert _url_encode_number(10) == 'a'
    assert _url_encode_number(35) == 'z'
    assert _url_encode_number(36) == 'A'
    assert _url_encode_number(63) == '_'


def test_encode_two_digits():
    # 64 = 1*64 + 0 → '10'
    assert _url_encode_number(64) == '10'
    # 65 = 1*64 + 1 → '11'
    assert _url_encode_number(65) == '11'


# ── _encode_notes ─────────────────────────────────────────────────────────────

def test_all_rests_encode_to_zero():
    assert _encode_notes(['0'] * 16, base=3) == '0'


def test_single_hit_at_last_step():
    # Last step = LSB = 1 → number = 1
    notes = ['0'] * 15 + ['1']
    assert _encode_notes(notes, base=3) == '1'


def test_single_hit_at_first_step():
    # First step = MSB = base^(n-1)
    # base=3, n=16 → 3^15 = 14348907
    notes = ['1'] + ['0'] * 15
    expected = _url_encode_number(3 ** 15)
    assert _encode_notes(notes, base=3) == expected


# ── encode_url — verified anchor ──────────────────────────────────────────────

def test_low_surdo_beat_2_and_4():
    """Low Surdo accent on beat 2 and beat 4 of 1 bar → verified URL."""
    # 4/4, 16 steps; beat 2 = step 4, beat 4 = step 12 (0-indexed)
    notes = ['0'] * 16
    notes[4] = '1'
    notes[12] = '1'
    tracks = [MappedTrack('9', notes)]
    url = encode_url(tracks, tempo=120, n_bars=1)
    assert url == 'https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm'


# ── encode_url — structure ────────────────────────────────────────────────────

def test_url_starts_with_bananadrum():
    tracks = [MappedTrack('9', ['0'] * 16)]
    url = encode_url(tracks)
    assert url.startswith('https://bananadrum.net/?a2=')


def test_url_contains_tempo():
    tracks = [MappedTrack('9', ['0'] * 16)]
    url = encode_url(tracks, tempo=95)
    assert '.95.' in url


def test_url_contains_n_bars():
    tracks = [MappedTrack('9', ['0'] * 32)]
    url = encode_url(tracks, n_bars=2)
    assert '.2.' in url


def test_n_bars_inferred_from_track_length():
    tracks = [MappedTrack('9', ['0'] * 32)]
    url = encode_url(tracks)
    assert '.2.' in url


def test_multiple_tracks_all_present():
    tracks = [
        MappedTrack('9', ['0'] * 16),
        MappedTrack('8', ['0'] * 16),
        MappedTrack('5', ['0'] * 16),
    ]
    url = encode_url(tracks)
    # Each track segment starts with its instrument ID after a '.'
    assert '.9' in url
    assert '.8' in url
    assert '.5' in url


def test_track_order_preserved():
    tracks = [
        MappedTrack('9', ['1'] + ['0'] * 15),
        MappedTrack('8', ['0'] * 16),
    ]
    url = encode_url(tracks)
    composition = url.split('?a2=')[1]
    # Low Surdo track should appear before Mid Surdo track
    assert composition.index('.9') < composition.index('.8')


def test_empty_tracks_raises():
    with pytest.raises(ValueError):
        encode_url([])


# ── polyrhythm helpers (Increment 8) ─────────────────────────────────────────

def test_pack_polyrhythm_string_known_value():
    """Verified: '0-3-3' packs to '3nq'."""
    assert _pack_polyrhythm_string('0-3-3') == '3nq'


def test_encode_polyrhythms_single_group():
    poly = MappedPolyrhythm(start=0, end=3, notes=['1', '9', '0'])
    assert _encode_polyrhythms([poly]) == '3nq'


def test_encode_polyrhythms_second_beat():
    """A single group starting at beat 2 (slot 4) → descriptor '4-3-3'."""
    poly = MappedPolyrhythm(start=4, end=7, notes=['1'] * 3)
    result = _encode_polyrhythms([poly])
    assert result == _pack_polyrhythm_string('4-3-3')


def test_encode_polyrhythms_two_consecutive_groups():
    """Two consecutive 4-col groups; second adj_start shifts by -1."""
    p1 = MappedPolyrhythm(start=0, end=3, notes=['1'] * 3)
    p2 = MappedPolyrhythm(start=4, end=7, notes=['1'] * 3)
    result = _encode_polyrhythms([p1, p2])
    # adj_start of p2 = 4 + (-1) = 3
    assert result == _pack_polyrhythm_string('0-3-3-3-3-3')


def test_build_effective_notes_no_poly():
    base = ['1', '0'] * 8
    assert _build_effective_notes(base, []) == base


def test_build_effective_notes_replaces_beat():
    base = ['0'] * 16
    poly = MappedPolyrhythm(start=0, end=3, notes=['1'] * 3)
    assert _build_effective_notes(base, [poly]) == ['1'] * 3 + ['0'] * 12


def test_build_effective_notes_partial_replacement():
    """Only beat 2 (slots 4-7) replaced; other beats keep base notes."""
    base = ['1'] * 4 + ['0'] * 4 + ['2'] * 8
    poly = MappedPolyrhythm(start=4, end=7, notes=['3'] * 3)
    result = _build_effective_notes(base, [poly])
    assert result == ['1'] * 4 + ['3'] * 3 + ['2'] * 8


def test_encode_url_with_polyrhythm_verified():
    """Repinique 6/8 on beat 1 at tempo 110.

    Poly descriptor 0-3-3 packs to '3nq' (verified).
    Notes ['1','0','0'] → effective 15-note sequence → number = 8^14 = 64^7
    → encodes to '10000000'.
    Expected URL: …310000000-3nq…
    """
    poly = MappedPolyrhythm(start=0, end=3, notes=['1', '0', '0'])
    tracks = [
        MappedTrack('0', ['0'] * 16),
        MappedTrack('1', ['0'] * 16),
        MappedTrack('2', ['0'] * 16),
        MappedTrack('3', ['0'] * 16, [poly]),
        MappedTrack('5', ['0'] * 16),
        MappedTrack('6', ['0'] * 16),
        MappedTrack('7', ['0'] * 16),
        MappedTrack('8', ['0'] * 16),
        MappedTrack('9', ['0'] * 16),
    ]
    url = encode_url(tracks, tempo=110, n_bars=1)
    assert url == ('https://bananadrum.net/?a2='
                   '4-4.110.1.1-4.16.00.10.20.310000000-3nq.50.60.70.80.90')


# ── instrument bases — round-trip spot checks ─────────────────────────────────

@pytest.mark.parametrize('instrument_id,base', [
    ('0', 3), ('1', 3), ('2', 3), ('3', 8),
    ('5', 5), ('6', 4), ('7', 3), ('8', 3), ('9', 3),
])
def test_all_rest_track_encodes_cleanly(instrument_id, base):
    """All-rest track for every instrument should not raise."""
    tracks = [MappedTrack(instrument_id, ['0'] * 16)]
    url = encode_url(tracks)
    assert f'.{instrument_id}' in url
