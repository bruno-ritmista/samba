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

# Display names for warnings, duplicated from mapping.py (not imported, since
# mapping.py imports this module — would be a circular import).
_INSTRUMENT_NAME: dict[str, str] = {
    '0': 'Agogô',
    'a': '4-Bell Agogô',
    '1': 'Chocalho',
    '2': 'Tamborim',
    '3': 'Repinique',
    '4': 'Repinique (Whippy)',
    '5': 'Caixa',
    '6': 'Timbau',
    '7': 'High Surdo',
    '8': 'Mid Surdo',
    '9': 'Low Surdo',
}

# Base-11 alphabet for the packed polyrhythm descriptor (digits + '-' as separator)
_POLY_B11 = '0123456789-'


@dataclass
class RawTrack:
    instrument_id: str
    styles: list[str | None]  # per-step style-index strings, length n_bars*16; None = polyrhythm step (skipped)


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


def _decode_polyrhythm_descriptor(packed: str) -> list[tuple[int, int, int]]:
    """Reverse of encode.py's _encode_polyrhythms + _pack_polyrhythm_string.

    Returns a list of (adj_start, span, length) triples — adj_start/length are
    in the *effective* (encoded) note-index space, span is always 3 (a 6/8
    polyrhythm always replaces 4 base steps with `length` notes).

    Packing the descriptor treats each character as a base-11 digit, so a
    single leading '0' character can be lost the same way _decode_notes must
    pad leading zero note-digits — but only the very first field can ever be
    empty this way (str(int) never produces internal leading zeros), so an
    empty leading field is unambiguously '0'.
    """
    number = _decode_url_number(packed)
    digits: list[int] = []
    while number > 0:
        number, remainder = divmod(number, 11)
        digits.append(remainder)
    digits.reverse()
    fields = ''.join(_POLY_B11[d] for d in digits).split('-')
    if fields[0] == '':
        fields[0] = '0'
    if len(fields) % 3 != 0 or not all(f.isdigit() for f in fields):
        raise ValueError(f"malformed polyrhythm descriptor {packed!r}")
    values = [int(f) for f in fields]
    return [tuple(values[i:i + 3]) for i in range(0, len(values), 3)]


def _decode_polyrhythm_track(encoded: str, packed: str, base: int, n_steps: int) -> list[str | None]:
    """Decode a track segment that carries one or more polyrhythm sections.

    Only the step ranges actually covered by a polyrhythm come back as None
    (skipped); every other step decodes normally.
    """
    groups = _decode_polyrhythm_descriptor(packed)
    extra = sum(length - (span + 1) for _, span, length in groups)
    effective = _decode_notes(encoded, base, n_steps + extra)

    styles: list[str | None] = []
    eff_idx = base_idx = cumulative_extra = 0
    for adj_start, span, length in groups:
        base_start = adj_start - cumulative_extra
        pass_through = base_start - base_idx
        styles.extend(effective[eff_idx:eff_idx + pass_through])
        eff_idx += pass_through
        base_idx += pass_through
        styles.extend([None] * (span + 1))
        base_idx += span + 1
        eff_idx += length
        cumulative_extra += length - (span + 1)
    styles.extend(effective[eff_idx:])
    return styles


def decode_url(url: str) -> DecodedArrangement:
    """Parse a BananaDrum shareable URL into a DecodedArrangement.

    Steps covered by a polyrhythm (6/8) section decode to None (skipped) —
    triplet decoding is out of scope for this iteration — but the rest of
    that track's steps decode normally.
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
        if instrument_id not in _INSTRUMENT_BASE:
            logger.warning(
                "Unrecognised instrument id '%s'; skipping that track.", instrument_id,
            )
            continue
        base = _INSTRUMENT_BASE[instrument_id]
        name = _INSTRUMENT_NAME.get(instrument_id, instrument_id)
        parts = rest.split('-', 1)
        if len(parts) > 1:
            encoded, packed = parts
            try:
                styles = _decode_polyrhythm_track(encoded, packed, base, n_steps)
            except Exception as e:
                logger.warning(
                    "Instrument '%s' has an unreadable polyrhythm section; skipping the whole track (%s).",
                    name, e,
                )
                continue
            logger.warning(
                "Instrument '%s' has a polyrhythm section; those notes will be skipped.",
                name,
            )
        else:
            styles = _decode_notes(parts[0], base, n_steps)
        tracks.append(RawTrack(instrument_id, styles))

    return DecodedArrangement(title=title, tempo=tempo, n_bars=n_bars, tracks=tracks)
