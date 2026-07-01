"""Increment 2: Translate decoded BananaDrum tracks into printable rows.

Authoritative id/style schema, cross-checked against BananaDrum's
bateria-instruments.ts (not inverted from sheets_to_banana's mapping.py,
which only covers the subset of styles that tool emits).
"""

import logging
from dataclasses import dataclass

from banana_to_pdf.decode import DecodedArrangement, RawTrack

logger = logging.getLogger(__name__)

# id -> (display_name, base, [style labels, index 0 unused ('0' = rest)])
INSTRUMENTS: dict[str, tuple[str, int, list[str]]] = {
    '0': ('Agogô', 3, ['low', 'high']),
    'a': ('4-Bell Agogô', 5, ['low-low', 'low', 'high', 'high-high']),
    '1': ('Chocalho', 3, ['accent', 'ghost']),
    '2': ('Tamborim', 3, ['accent', 'ghost']),
    '3': ('Repinique', 8, ['center', 'edge', 'rimshot', 'rim', 'buzz', 'hand', 'slap']),
    '4': ('Repinique (Whippy)', 3, ['accent', 'ghost']),
    '5': ('Caixa', 5, ['accent', 'ghost', 'buzz', 'rimshot']),
    '6': ('Timbau', 4, ['open', 'slap', 'bass']),
    '7': ('High Surdo', 3, ['accent', 'muted']),
    '8': ('Mid Surdo', 3, ['accent', 'muted']),
    '9': ('Low Surdo', 3, ['accent', 'muted']),
}

# (instrument_id, style_index) -> Unicode glyph, read off a real BananaDrum
# WebGUI screenshot 2026-07-01 (still tunable, see doc/design_plan.md).
# The real GUI reuses the same glyph for the same *kind* of hit across
# instruments (X=strong/center accent, x=light/edge/ghost, etc.) rather
# than giving each instrument its own bespoke set — mirrored here.
GLYPHS: dict[tuple[str, int], str] = {
    ('a', 1): '↓', ('a', 2): 'v', ('a', 3): '^', ('a', 4): '↑',  # low-low..high-high
    ('0', 1): 'v', ('0', 2): '^',  # reuse 4-Bell's 'low'/'high'
    ('1', 1): 'X', ('1', 2): 'x',
    ('2', 1): 'X', ('2', 2): 'x',
    ('4', 1): 'X', ('4', 2): 'x',
    ('3', 1): 'X', ('3', 2): 'x', ('3', 3): '⁂', ('3', 4): '◠', ('3', 5): '/', ('3', 6): '○', ('3', 7): '✱',
    ('5', 1): 'X', ('5', 2): 'x', ('5', 3): '/', ('5', 4): '⁂',  # buzz, rimshot (shared w/ Repinique)
    ('6', 1): '○', ('6', 2): '✱', ('6', 3): '●',  # open, slap (shared w/ Repinique), bass
    ('7', 1): '○', ('7', 2): '●',  # accent = open ring, muted = filled (matches BananaDrum icon)
    ('8', 1): '○', ('8', 2): '●',
    ('9', 1): '○', ('9', 2): '●',
}
_FALLBACK_GLYPH = '●'

# BananaDrum WebGUI top-to-bottom order.
_DISPLAY_ORDER = ['0', 'a', '1', '2', '3', '4', '5', '6', '7', '8', '9']

_warned: set[tuple[str, int]] = set()


@dataclass
class Row:
    label: str
    cells: list[str]  # one glyph per step, '' = rest


def _glyph(instrument_id: str, style_index: int) -> str:
    if style_index == 0:
        return ''
    key = (instrument_id, style_index)
    glyph = GLYPHS.get(key)
    if glyph is not None:
        return glyph
    if key not in _warned:
        _warned.add(key)
        logger.warning(
            "No glyph mapped for instrument '%s' style index %d; using fallback.",
            instrument_id, style_index,
        )
    return _FALLBACK_GLYPH


def _row_for_track(track: RawTrack) -> Row:
    label = INSTRUMENTS[track.instrument_id][0]
    cells = [_glyph(track.instrument_id, int(s)) for s in track.styles]
    return Row(label, cells)


def map_tracks(decoded: DecodedArrangement) -> list[Row]:
    """Translate a DecodedArrangement into printable Rows.

    Drops rows that are entirely rests, and orders the rest by BananaDrum
    display order (see _DISPLAY_ORDER). High/Mid/Low Surdo stay separate
    rows, matching the WebGUI, since their accent/muted glyphs are only
    distinguishable per-drum.
    """
    by_id = {t.instrument_id: t for t in decoded.tracks}
    rows_by_key = {instrument_id: _row_for_track(track) for instrument_id, track in by_id.items()}

    ordered = [rows_by_key[key] for key in _DISPLAY_ORDER if key in rows_by_key]
    return [row for row in ordered if any(cell for cell in row.cells)]
