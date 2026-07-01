"""Increment 1: Decode a BananaDrum shareable URL into per-track style indices.

Exact inverse of sheets_to_banana/src/encode.py. Kept self-contained
(constants duplicated, not imported) so this tool has no dependency on
sheets_to_banana.
"""

import logging
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs, unquote

logger = logging.getLogger(__name__)

# Base-64 character table matching BananaDrum's urlNumberToCharacter
_B64 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ~_'

# Number of possible values per step (note styles + 1 for rest), per instrument ID
_INSTRUMENT_BASE: dict[str, int] = {
    '0': 3,   # Agogo
    'a': 5,   # 4-Bell Agogo
    '1': 3,   # Chocalho
    '2': 3,   # Tamborim
    '3': 8,   # Repinique
    '4': 3,   # Repinique (Whippy)
    '5': 5,   # Caixa
    '6': 4,   # Timbau
    '7': 3,   # High Surdo
    '8': 3,   # Mid Surdo
    '9': 3,   # Low Surdo
}


@dataclass
class RawTrack:
    instrument_id: str
    styles: list[str]  # per-step style-index strings, length n_bars*16


@dataclass
class DecodedArrangement:
    title: str
    tempo: int
    n_bars: int
    tracks: list[RawTrack]


def _decode_url_number(s: str) -> int:
    """Decode a base-64 BananaDrum string into an integer."""
    n = 0
    for ch in s:
        n = n * 64 + _B64.index(ch)
    return n


def _decode_notes(encoded: str, base: int, n_steps: int) -> list[str]:
    """Reverse of encode.py's _encode_notes: recover per-step style digits.

    The encoded integer holds the notes as digits of a base-N number
    (first step = MSB). Repeatedly divmod to recover digits LSB-first,
    then pad leading '0' (rest) to n_steps.
    """
    number = _decode_url_number(encoded)
    digits: list[str] = []
    while number > 0:
        number, remainder = divmod(number, base)
        digits.append(str(remainder))
    digits.reverse()
    padding = ['0'] * (n_steps - len(digits))
    return padding + digits


def decode_url(url: str) -> DecodedArrangement:
    """Parse a BananaDrum shareable URL into a DecodedArrangement.

    Tracks carrying a polyrhythm (6/8) segment are skipped with a
    warning — out of scope for iteration 1 (see plan open points).
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    title = unquote(query['t'][0]) if 't' in query else ''

    composition = query['a2'][0]
    fields = composition.split('.')
    tempo = int(fields[1])
    n_bars = int(fields[2])
    n_steps = n_bars * 16
    track_segments = fields[5:]

    tracks: list[RawTrack] = []
    for segment in track_segments:
        instrument_id, rest = segment[0], segment[1:]
        parts = rest.split('-', 1)
        if len(parts) > 1:
            logger.warning(
                "Track '%s' carries a polyrhythm; skipping (unsupported in this iteration).",
                instrument_id,
            )
            continue
        base = _INSTRUMENT_BASE[instrument_id]
        styles = _decode_notes(parts[0], base, n_steps)
        tracks.append(RawTrack(instrument_id, styles))

    return DecodedArrangement(title=title, tempo=tempo, n_bars=n_bars, tracks=tracks)
