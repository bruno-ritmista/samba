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

# (instrument_id, style_index) -> Unicode glyph.  # tunable, see doc/design_plan.md
GLYPHS: dict[tuple[str, int], str] = {
    ('0', 1): '▽', ('0', 2): '△',
    ('a', 1): '▼', ('a', 2): '▽', ('a', 3): '△', ('a', 4): '▲',
    ('1', 1): '●', ('1', 2): '○',
    ('2', 1): '●', ('2', 2): '○',
    ('4', 1): '●', ('4', 2): '○',
    ('3', 1): '●', ('3', 2): '◐', ('3', 3): '╱', ('3', 4): '▏', ('3', 5): '~', ('3', 6): '✋', ('3', 7): '◆',
    ('5', 1): '●', ('5', 2): '○', ('5', 3): '~', ('5', 4): '╱',
    ('6', 1): '◯', ('6', 2): '◆', ('6', 3): '●',
    ('7', 1): '○', ('7', 2): '●',  # accent = open ring, muted = filled (matches BananaDrum icon)
    ('8', 1): '○', ('8', 2): '●',
    ('9', 1): '○', ('9', 2): '●',
}
_FALLBACK_GLYPH = '●'
_SURDO_BOTH_GLYPH = '◉'  # tunable: Low+Mid hit on the same step

# Surdos, Caixa, Repinique(+Whippy), Timbau, Tamborim, Chocalho, Agogô(+4-Bell)
_DISPLAY_ORDER = ['7', 'surdo_merged', '5', '3', '4', '6', '2', '1', '0', 'a']

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


def _merge_surdo(low: RawTrack | None, mid: RawTrack | None) -> Row:
    low_styles = low.styles if low else []
    mid_styles = mid.styles if mid else []
    n_steps = len(low_styles) or len(mid_styles)
    low_styles = low_styles or ['0'] * n_steps
    mid_styles = mid_styles or ['0'] * n_steps

    cells: list[str] = []
    for low_s, mid_s in zip(low_styles, mid_styles):
        low_i, mid_i = int(low_s), int(mid_s)
        if low_i and mid_i:
            cells.append(_SURDO_BOTH_GLYPH)
        elif low_i:
            cells.append(_glyph('9', low_i))
        elif mid_i:
            cells.append(_glyph('8', mid_i))
        else:
            cells.append('')
    return Row('Surdo 1a/2a', cells)


def map_tracks(decoded: DecodedArrangement) -> list[Row]:
    """Translate a DecodedArrangement into printable Rows.

    Merges Low ('9') and Mid ('8') Surdo tracks into one "Surdo 1a/2a" row,
    drops rows that are entirely rests, and orders the rest by BananaDrum
    display order (see _DISPLAY_ORDER).
    """
    by_id = {t.instrument_id: t for t in decoded.tracks}
    low = by_id.pop('9', None)
    mid = by_id.pop('8', None)

    rows_by_key: dict[str, Row] = {}
    if low or mid:
        rows_by_key['surdo_merged'] = _merge_surdo(low, mid)
    for instrument_id, track in by_id.items():
        rows_by_key[instrument_id] = _row_for_track(track)

    ordered = [rows_by_key[key] for key in _DISPLAY_ORDER if key in rows_by_key]
    return [row for row in ordered if any(cell for cell in row.cells)]
