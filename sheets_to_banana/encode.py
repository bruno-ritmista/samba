"""Increment 4: Encode MappedTrack objects into a BananaDrum URL.

Replicates the TypeScript serialisation logic from
packages/bananadrum-core/src/prod/serialisation/.

Encoding:
  - Each track's notes are treated as digits of a base-N number,
    first step = MSB, last step = LSB.
  - N = number of note styles + 1 (for rest), defined per instrument by BananaDrum.
  - The resulting integer is encoded in base 64 using characters 0-9a-zA-Z~_
"""

from urllib.parse import quote

from sheets_to_banana.mapping import MappedTrack

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
        raise ValueError("No tracks to encode")

    steps = len(tracks[0].notes)
    if n_bars is None:
        n_bars = steps // 16

    track_parts = []
    for track in tracks:
        base = _INSTRUMENT_BASE[track.instrument_id]
        encoded = _encode_notes(track.notes, base)
        track_parts.append(track.instrument_id + encoded)

    composition = f"4-4.{tempo}.{n_bars}.1-4.16." + ".".join(track_parts)
    if title:
        return f"https://bananadrum.net/?t={quote(title, safe='')}&a2={composition}"
    return f"https://bananadrum.net/?a2={composition}"
