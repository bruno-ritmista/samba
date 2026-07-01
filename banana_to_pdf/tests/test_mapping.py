"""Tests for mapping.py — Increment 2."""

import logging

from banana_to_pdf.decode import DecodedArrangement, RawTrack
from banana_to_pdf.mapping import map_tracks


def _arrangement(tracks: list[RawTrack]) -> DecodedArrangement:
    return DecodedArrangement(title='', tempo=120, n_bars=1, tracks=tracks)


def test_simple_track_mapped_to_glyphs():
    styles = ['0'] * 16
    styles[0] = '1'
    styles[4] = '2'
    arrangement = _arrangement([RawTrack('5', styles)])  # Caixa

    rows = map_tracks(arrangement)

    assert len(rows) == 1
    assert rows[0].label == 'Caixa'
    assert rows[0].cells[0] == '●'
    assert rows[0].cells[4] == '○'
    assert rows[0].cells[1] == ''


def test_surdo_low_and_mid_merged_into_one_row():
    low = RawTrack('9', ['0', '1', '0', '1'])
    mid = RawTrack('8', ['0', '0', '1', '1'])
    rows = map_tracks(_arrangement([low, mid]))

    assert len(rows) == 1
    assert rows[0].label == 'Surdo 1a/2a'
    assert rows[0].cells == ['', '○', '○', '◉']  # low-only, mid-only, both (accent = open ring)


def test_all_rest_row_dropped():
    rows = map_tracks(_arrangement([RawTrack('5', ['0'] * 16)]))
    assert rows == []


def test_display_order_surdo_before_caixa():
    high_surdo = RawTrack('7', ['1'] + ['0'] * 15)
    caixa = RawTrack('5', ['1'] + ['0'] * 15)
    rows = map_tracks(_arrangement([caixa, high_surdo]))
    assert [r.label for r in rows] == ['High Surdo', 'Caixa']


def test_unmapped_style_falls_back_and_warns(caplog):
    # Repinique (base 8) has no glyph for style index 7 → falls to fallback
    styles = ['0'] * 15 + ['7']
    with caplog.at_level(logging.WARNING):
        rows = map_tracks(_arrangement([RawTrack('4', styles)]))  # Whippy has no style 7 in GLYPHS

    assert rows[0].cells[-1] == '●'
