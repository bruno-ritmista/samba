"""Tests for trim_empty_bars() — Increment 9."""

import pytest
from sheet_to_banana.mapping import MappedTrack, MappedPolyrhythm, trim_empty_bars


# ── helpers ───────────────────────────────────────────────────────────────────

def make_track(notes: list[str], instrument_id: str = '5',
               polys: list[MappedPolyrhythm] | None = None) -> MappedTrack:
    return MappedTrack(instrument_id=instrument_id, notes=notes, polyrhythms=polys or [])


def empty_bar() -> list[str]:
    return ['0'] * 16


def hit_bar(hit_pos: int = 0) -> list[str]:
    bar = ['0'] * 16
    bar[hit_pos] = '1'
    return bar


# ── no trimming needed ────────────────────────────────────────────────────────

def test_no_empty_bars_unchanged():
    notes = hit_bar() * 4
    track = make_track(notes)
    result = trim_empty_bars([track])
    assert not result.all_empty
    assert result.lead_bars == 0
    assert result.trail_bars == 0
    assert result.tracks[0].notes == notes


# ── trailing empty bars ───────────────────────────────────────────────────────

def test_single_trailing_empty_bar_removed():
    notes = hit_bar() + empty_bar()
    result = trim_empty_bars([make_track(notes)])
    assert not result.all_empty
    assert result.trail_bars == 1
    assert result.lead_bars == 0
    assert len(result.tracks[0].notes) == 16


def test_two_trailing_empty_bars_removed():
    notes = hit_bar() + empty_bar() + empty_bar()
    result = trim_empty_bars([make_track(notes)])
    assert result.trail_bars == 2
    assert len(result.tracks[0].notes) == 16


# ── leading empty bars ────────────────────────────────────────────────────────

def test_single_leading_empty_bar_removed():
    notes = empty_bar() + hit_bar()
    result = trim_empty_bars([make_track(notes)])
    assert not result.all_empty
    assert result.lead_bars == 1
    assert result.trail_bars == 0
    assert len(result.tracks[0].notes) == 16


# ── both ends ────────────────────────────────────────────────────────────────

def test_leading_and_trailing_both_trimmed():
    notes = empty_bar() + hit_bar() + empty_bar() + empty_bar()
    result = trim_empty_bars([make_track(notes)])
    assert result.lead_bars == 1
    assert result.trail_bars == 2
    assert len(result.tracks[0].notes) == 16


# ── all bars empty ────────────────────────────────────────────────────────────

def test_all_empty_returns_all_empty_flag():
    notes = empty_bar() * 4
    result = trim_empty_bars([make_track(notes)])
    assert result.all_empty
    assert result.tracks == []


def test_all_empty_single_bar():
    result = trim_empty_bars([make_track(empty_bar())])
    assert result.all_empty
    assert result.tracks == []


# ── empty input ───────────────────────────────────────────────────────────────

def test_no_tracks_returns_all_empty():
    result = trim_empty_bars([])
    assert result.all_empty
    assert result.tracks == []


# ── multiple tracks ───────────────────────────────────────────────────────────

def test_bar_not_empty_if_any_track_has_hit():
    track_a = make_track(empty_bar() + empty_bar(), instrument_id='5')
    track_b = make_track(empty_bar() + hit_bar(), instrument_id='3')
    result = trim_empty_bars([track_a, track_b])
    assert not result.all_empty
    assert result.lead_bars == 1
    assert result.trail_bars == 0
    assert len(result.tracks[0].notes) == 16
    assert len(result.tracks[1].notes) == 16


def test_all_tracks_trimmed_consistently():
    track_a = make_track(empty_bar() + hit_bar() + empty_bar(), instrument_id='5')
    track_b = make_track(empty_bar() + hit_bar() + empty_bar(), instrument_id='3')
    result = trim_empty_bars([track_a, track_b])
    assert result.lead_bars == 1
    assert result.trail_bars == 1
    for t in result.tracks:
        assert len(t.notes) == 16


# ── polyrhythm index adjustment ───────────────────────────────────────────────

def test_polyrhythm_indices_shifted_after_leading_trim():
    # 2 bars: bar 0 empty, bar 1 has a poly at steps 16-19
    poly = MappedPolyrhythm(start=16, end=19, notes=['1', '1', '1'])
    notes = empty_bar() + hit_bar()
    track = make_track(notes, polys=[poly])
    result = trim_empty_bars([track])
    assert result.lead_bars == 1
    assert len(result.tracks[0].polyrhythms) == 1
    mp = result.tracks[0].polyrhythms[0]
    assert mp.start == 0   # shifted by -16
    assert mp.end == 3


def test_bar_with_only_polyrhythm_content_is_not_empty():
    # bar 0 has only a poly (notes all '0'), bar 1 has a hit — bar 0's poly has
    # non-rest notes, so bar 0 is NOT empty and nothing is trimmed.
    poly = MappedPolyrhythm(start=0, end=3, notes=['1', '1', '1'])
    notes = empty_bar() + hit_bar()
    track = make_track(notes, polys=[poly])
    result = trim_empty_bars([track])
    assert not result.all_empty
    assert result.lead_bars == 0
    assert result.tracks[0].polyrhythms == [poly]


def test_bar_with_only_all_rest_polyrhythm_is_empty():
    # bar 0 has a poly whose notes are all '0' (a fully-rest polygroup), bar 1
    # has a hit — bar 0 is still empty and is trimmed along with its poly.
    poly = MappedPolyrhythm(start=0, end=3, notes=['0', '0', '0'])
    notes = empty_bar() + hit_bar()
    track = make_track(notes, polys=[poly])
    result = trim_empty_bars([track])
    assert result.lead_bars == 1
    assert result.tracks[0].polyrhythms == []


def test_all_polygroup_bar_not_trimmed_as_empty():
    # A single bar where every step is '0' in `notes` but a polyrhythm spans
    # the whole bar with real hits — this is the "all beats are polygroups"
    # case from issue feedback; the bar must NOT be treated as empty.
    poly = MappedPolyrhythm(start=0, end=15, notes=['1', '1', '1'])
    notes = empty_bar()
    track = make_track(notes, polys=[poly])
    result = trim_empty_bars([track])
    assert not result.all_empty
    assert len(result.tracks[0].notes) == 16
    assert result.tracks[0].polyrhythms == [poly]


def test_polyrhythm_not_in_trimmed_region_preserved():
    # 3 bars: bar 0 empty, bar 1 has hit + poly, bar 2 empty
    poly = MappedPolyrhythm(start=16, end=19, notes=['1', '1', '1'])
    notes = empty_bar() + hit_bar() + empty_bar()
    track = make_track(notes, polys=[poly])
    result = trim_empty_bars([track])
    assert result.lead_bars == 1
    assert result.trail_bars == 1
    assert len(result.tracks[0].polyrhythms) == 1
    assert result.tracks[0].polyrhythms[0].start == 0
