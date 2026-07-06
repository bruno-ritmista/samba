"""Tests for decode.py — Increment 1.

Anchors reused from sheets_to_banana/tests/test_encode.py (verified in
BananaDrum), so decoding these known-good URLs is a round-trip check
against the encoder without importing across packages.
"""

import logging

from banana_to_pdf.decode import decode_url, _decode_url_number, _decode_notes


# ── _decode_url_number ─────────────────────────────────────────────────────────

def test_decode_zero():
    assert _decode_url_number('0') == 0


def test_decode_single_digit():
    assert _decode_url_number('9') == 9
    assert _decode_url_number('a') == 10
    assert _decode_url_number('z') == 35
    assert _decode_url_number('A') == 36
    assert _decode_url_number('_') == 63


def test_decode_two_digits():
    assert _decode_url_number('10') == 64
    assert _decode_url_number('11') == 65


# ── _decode_notes ───────────────────────────────────────────────────────────────

def test_decode_notes_all_rests():
    assert _decode_notes('0', base=3, n_steps=16) == ['0'] * 16


def test_decode_notes_pads_leading_zeros():
    """A short encoded number must be left-padded to n_steps (rest = '0')."""
    notes = _decode_notes('1', base=3, n_steps=16)
    assert len(notes) == 16
    assert notes == ['0'] * 15 + ['1']


# ── decode_url — verified anchors ───────────────────────────────────────────────

def test_low_surdo_beat_2_and_4_round_trip():
    """Inverse of test_low_surdo_beat_2_and_4 in sheets_to_banana."""
    url = 'https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm'
    arrangement = decode_url(url)

    assert arrangement.title == ''
    assert arrangement.tempo == 120
    assert arrangement.n_bars == 1
    assert len(arrangement.tracks) == 1

    track = arrangement.tracks[0]
    assert track.instrument_id == '9'
    expected = ['0'] * 16
    expected[4] = '1'
    expected[12] = '1'
    assert track.styles == expected


def test_title_decoded_and_unquoted():
    url = 'https://bananadrum.net/?t=Levada%20Ap%C3%B3s&a2=4-4.120.1.1-4.16.9Hgm'
    arrangement = decode_url(url)
    assert arrangement.title == 'Levada Após'


def test_title_absent_defaults_empty():
    url = 'https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm'
    assert decode_url(url).title == ''


def test_multiple_tracks_order_preserved():
    url = 'https://bananadrum.net/?a2=4-4.120.1.1-4.16.90.80.50'
    arrangement = decode_url(url)
    assert [t.instrument_id for t in arrangement.tracks] == ['9', '8', '5']


def test_polyrhythm_only_covered_steps_skipped(caplog):
    """Inverse of test_encode_url_with_polyrhythm_verified in sheets_to_banana.

    Only the polyrhythm-covered steps (beat 1: index 0-3) come back as None;
    the rest of the Repinique track still decodes normally.
    """
    url = ('https://bananadrum.net/?a2='
           '4-4.110.1.1-4.16.00.10.20.310000000-3nq.50.60.70.80.90')
    with caplog.at_level(logging.WARNING):
        arrangement = decode_url(url)

    ids = [t.instrument_id for t in arrangement.tracks]
    assert ids == ['0', '1', '2', '3', '5', '6', '7', '8', '9']

    repinique = next(t for t in arrangement.tracks if t.instrument_id == '3')
    assert repinique.styles == [None, None, None, None] + ['0'] * 12
    assert "Instrument 'Repinique'" in caplog.text
    assert 'polyrhythm' in caplog.text.lower()


def test_polyrhythm_leading_zero_start_decodes(caplog):
    """A polyrhythm group starting at step 0 exercises the leading-zero-loss fix."""
    url = ('https://bananadrum.net/?a2='
           '4-4.110.1.1-4.16.00.10-3nq.2qmIZ-3nq.30.50.60.70.80.90')
    with caplog.at_level(logging.WARNING):
        arrangement = decode_url(url)

    chocalho = next(t for t in arrangement.tracks if t.instrument_id == '1')
    assert chocalho.styles[:4] == [None, None, None, None]
    assert chocalho.styles[4:] == ['0'] * 12


def test_n_bars_two_pads_to_32_steps():
    # 32-step all-rest Low Surdo track encodes to '0'
    url = 'https://bananadrum.net/?a2=4-4.120.2.1-4.16.90'
    arrangement = decode_url(url)
    assert arrangement.n_bars == 2
    assert len(arrangement.tracks[0].styles) == 32
