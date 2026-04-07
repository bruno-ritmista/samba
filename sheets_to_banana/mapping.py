"""Increment 3: Translate parsed notes into BananaDrum instrument/note IDs.

Each CSV instrument row is identified by keyword-matching its label, then
each note character is translated to a BananaDrum note-style index ('0' = rest).

Surdo 1a/2a rows are split into two BananaDrum tracks:
  '1' → Low Surdo ('9'),  '2' → Mid Surdo ('8'),  'O' → both.

BananaDrum instrument IDs:
  '0' Agogô  '1' Chocalho  '2' Tamborim  '3' Repinique
  '5' Caixa  '6' Timbau    '7' High Surdo  '8' Mid Surdo  '9' Low Surdo
"""

import logging
from dataclasses import dataclass
from sheets_to_banana.parse import Break

logger = logging.getLogger(__name__)


@dataclass
class MappedTrack:
    instrument_id: str      # BananaDrum instrument ID ('0'..'9')
    notes: list[str]        # per-step style index: '0'=rest, '1','2',… = hit


# ── note-character → style-index tables ──────────────────────────────────────

_AGOGO   = {'L': '1', 'H': '2'}
_CHOCALHO = {'X': '1'}
_TAMBORIM = {'X': '1'}
_REPIQUE  = {'X': '1', 'x': '2', '/': '3', 'K': '4', 'W': '5', 'O': '6', 'S': '7'}
_CAIXA    = {'X': '1', 'x': '2', 'W': '3', '/': '4'}
_TIMBAU   = {'S': '2', 'O': '3'}          # 'OO' → rest (two 1/32nd tones, skipped)
_HIGH_SURDO = {'X': '1', 'D': '2'}        # 'W' (roll) → rest
_LOW_SURDO  = {'1': '1', 'O': '1','D': '2'}        # Low Surdo plays on '1' and 'O'
_MID_SURDO  = {'2': '1', 'O': '1','D': '2'}        # Mid Surdo plays on '2' and 'O'


def _map(note: str, table: dict[str, str], instrument: str, warn: bool = True) -> str:
    """Look up note in table; return '0' (rest) if not found.

    Logs a warning when a non-rest note character has no entry in the table,
    unless warn=False (used where a rest on this track is expected by design).
    """
    result = table.get(note, '0')
    if warn and result == '0' and note != '0':
        logger.warning("Unmapped note '%s' for instrument '%s' → rest", note, instrument)
    return result


# ── instrument classification ─────────────────────────────────────────────────

def _classify(name: str) -> str | None:
    """Return an internal instrument kind string, or None if unrecognised."""
    n = name.lower()
    if 'surdo' in n:
        # 'Surdo Mor' or 'Surdo 3a' → High Surdo; everything else → split
        if 'mor' in n or '3' in n:
            return 'high_surdo'
        return 'surdo_split'
    if 'caixa'    in n: return 'caixa'
    if 'repique'  in n or 'repinique' in n: return 'repique'
    if 'timbau'   in n: return 'timbau'
    if 'tamborim' in n: return 'tamborim'
    if 'chocalho' in n: return 'chocalho'
    if 'agog'     in n: return 'agogo'   # matches 'agogô' and 'agogo'
    return None


# ── public API ────────────────────────────────────────────────────────────────

def map_break(brk: Break) -> list[MappedTrack]:
    """Translate one Break into a list of MappedTrack objects.

    Unknown instrument names are silently skipped.
    Unknown note characters produce a rest ('0').

    The Surdo 1a/2a row yields TWO MappedTracks (Low Surdo '9' then
    Mid Surdo '8') so that BananaDrum can render them independently.

    Args:
        brk: A Break as produced by parse.parse_sheet.

    Returns:
        Ordered list of MappedTrack, one per BananaDrum track.
    """
    result: list[MappedTrack] = []

    for name, notes in brk.tracks.items():
        kind = _classify(name)
        if kind is None:
            logger.error("Unexpected instrument '%s' — no BananaDrum mapping, skipped", name)
            continue

        if kind == 'surdo_split':
            # '1' notes are silent on Mid Surdo, '2' notes are silent on Low Surdo — both expected
            result.append(MappedTrack('9', [_map(n, _LOW_SURDO,  name, warn=False) for n in notes]))
            result.append(MappedTrack('8', [_map(n, _MID_SURDO,  name, warn=False) for n in notes]))
        elif kind == 'high_surdo':
            result.append(MappedTrack('7', [_map(n, _HIGH_SURDO, name) for n in notes]))
        elif kind == 'caixa':
            result.append(MappedTrack('5', [_map(n, _CAIXA,      name) for n in notes]))
        elif kind == 'repique':
            result.append(MappedTrack('3', [_map(n, _REPIQUE,    name) for n in notes]))
        elif kind == 'timbau':
            result.append(MappedTrack('6', [_map(n, _TIMBAU,     name) for n in notes]))
        elif kind == 'tamborim':
            result.append(MappedTrack('2', [_map(n, _TAMBORIM,   name) for n in notes]))
        elif kind == 'chocalho':
            result.append(MappedTrack('1', [_map(n, _CHOCALHO,   name) for n in notes]))
        elif kind == 'agogo':
            result.append(MappedTrack('0', [_map(n, _AGOGO,      name) for n in notes]))

    return result
