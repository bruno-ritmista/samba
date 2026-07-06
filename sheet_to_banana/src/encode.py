"""Increments 4 & 8: Encode MappedTrack objects into a BananaDrum URL.

Increment 8 adds polyrhythm encoding: tracks that carry MappedPolyrhythm
objects get their effective notes built by splicing poly notes over the base
notes, and a packed polyrhythm descriptor appended to their URL segment.

Replicates the TypeScript serialisation logic from
packages/bananadrum-core/src/prod/serialisation/.

Encoding:
  - Each track's notes are treated as digits of a base-N number,
    first step = MSB, last step = LSB.
  - N = number of note styles + 1 (for rest), defined per instrument by BananaDrum.
  - The resulting integer is encoded in base 64 using characters 0-9a-zA-Z~_
"""

import logging
from urllib.parse import quote

from sheet_to_banana.mapping import MappedPolyrhythm, MappedTrack

logger = logging.getLogger(__name__)

# Base-64 character table matching BananaDrum's urlNumberToCharacter
_B64 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ~_'

# Number of possible values per step (note styles + 1 for rest), per instrument ID
_INSTRUMENT_BASE: dict[str, int] = {
    '0': 3,   # Agogô
    '1': 3,   # Chocalho
    '2': 3,   # Tamborim
    '3': 8,   # Repinique
    '5': 5,   # Caixa
    '6': 4,   # Timbau
    '7': 3,   # Surdo Mor (High Surdo)
    '8': 3,   # Surdo 1a/2a Mid
    '9': 3,   # Surdo 1a/2a Low
}


def _url_encode_number(n: int) -> str:
    """Encode a non-negative integer in base 64 using BananaDrum's character table."""
    if n == 0:
        return '0'
    output: list[str] = []
    while n > 0:
        n, remainder = divmod(n, 64)
        output.append(_B64[remainder])
    return ''.join(reversed(output))


def _encode_notes(notes: list[str], base: int) -> str:
    """Interpret note-style indices as a base-N number (first step = MSB) and encode."""
    number = 0
    for digit in notes:
        number = number * base + int(digit)
    return _url_encode_number(number)


# ── polyrhythm encoding ───────────────────────────────────────────────────────

_POLY_B11 = '0123456789-'  # 11 chars; '-' is index 10


def _pack_polyrhythm_string(s: str) -> str:
    """Interpret s as a base-11 number (using _POLY_B11) and encode in base 64."""
    n = 0
    for ch in s:
        n = n * 11 + _POLY_B11.index(ch)
    return _url_encode_number(n)


def _encode_polyrhythms(polys: list[MappedPolyrhythm]) -> str:
    """Build and pack the polyrhythm descriptor string for 6/8 cells.

    BananaDrum applies polyrhythms in list order.  When applying poly[k],
    all earlier polys have already been applied, so the start/end indices
    must be shifted by the cumulative note-count change those polys caused.
    Each 4→3 polyrhythm removes 1 note (cumulative_extra = 3 - 4 = -1).
    """
    cumulative_extra = 0
    parts: list[str] = []
    for poly in sorted(polys, key=lambda p: p.start):
        adj_start = poly.start + cumulative_extra
        span = poly.end - poly.start          # always 3 for 4-column cells
        length = len(poly.notes)
        parts += [str(adj_start), str(span), str(length)]
        cumulative_extra += length - (span + 1)   # 3 - 4 = -1
    return _pack_polyrhythm_string('-'.join(parts))


def _build_effective_notes(
    base: list[str], polys: list[MappedPolyrhythm]
) -> list[str]:
    """Splice polyrhythm notes over the base notes.

    For each poly group, the 16 base slots (start..end inclusive) are replaced
    by the poly's notes list.  The result is the sequence BananaDrum encodes.
    """
    out: list[str] = []
    idx = 0
    for poly in sorted(polys, key=lambda p: p.start):
        out.extend(base[idx:poly.start])
        out.extend(poly.notes)
        idx = poly.end + 1
    out.extend(base[idx:])
    return out


def encode_url(
    tracks: list[MappedTrack],
    tempo: int = 120,
    n_bars: int | None = None,
    title: str = '',
) -> str:
    """Build a BananaDrum shareable URL from a list of MappedTrack objects.

    Args:
        tracks:  Ordered list of MappedTrack as produced by mapping.map_break.
        tempo:   BPM (default 120).
        n_bars:  Number of bars. If None, inferred from track length (steps / 16).
        title:   Optional human-readable title added as ?t= parameter.

    Returns:
        A full https://bananadrum.net/ URL.
    """
    if not tracks:
        logger.error("No tracks to encode")
        raise ValueError("No tracks to encode")

    steps = len(tracks[0].notes)
    if n_bars is None:
        n_bars = steps // 16

    track_parts = []
    for track in tracks:
        base = _INSTRUMENT_BASE[track.instrument_id]
        effective = (_build_effective_notes(track.notes, track.polyrhythms)
                     if track.polyrhythms else track.notes)
        encoded = _encode_notes(effective, base)
        segment = track.instrument_id + encoded
        if track.polyrhythms:
            segment += '-' + _encode_polyrhythms(track.polyrhythms)
        track_parts.append(segment)

    composition = f"4-4.{tempo}.{n_bars}.1-4.16." + ".".join(track_parts)
    if title:
        return f"https://bananadrum.net/?t={quote(title, safe='')}&a2={composition}"
    return f"https://bananadrum.net/?a2={composition}"
