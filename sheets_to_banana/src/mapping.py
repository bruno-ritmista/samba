"""Increments 3 & 8: Translate parsed notes into BananaDrum instrument/note IDs.

Increment 8 adds translation of PolyGroup objects (from parse.py) into
MappedPolyrhythm objects attached to each MappedTrack.

Each CSV instrument row is identified by keyword-matching its label, then
each note character is translated to a BananaDrum note-style index ('0' = rest).

Surdo 1a/2a rows are split into two BananaDrum tracks:
  '1' → Low Surdo ('9'),  '2' → Mid Surdo ('8'),  'O' → both.

BananaDrum instrument IDs:
  '0' Agogô  '1' Chocalho  '2' Tamborim  '3' Repinique
  '5' Caixa  '6' Timbau    '7' High Surdo  '8' Mid Surdo  '9' Low Surdo
"""

import logging
from dataclasses import dataclass, field
from sheets_to_banana.parse import Break, PolyGroup

logger = logging.getLogger(__name__)

_warned: set[tuple[str, str]] = set()  # (note, instrument) pairs already warned


@dataclass
class MappedPolyrhythm:
    start: int          # base slot index (same as PolyGroup.start)
    end: int            # base slot index (same as PolyGroup.end)
    notes: list[str]    # exactly 3 style indices (mapped from raw note chars; '0' = pause)


@dataclass
class MappedTrack:
    instrument_id: str                          # BananaDrum instrument ID ('0'..'9')
    notes: list[str]                            # per-step style index: '0'=rest, '1','2',… = hit
    polyrhythms: list[MappedPolyrhythm] = field(default_factory=list)


# ── note-character → style-index tables ──────────────────────────────────────

_AGOGO   = {'L': '1', 'H': '2'}
_CHOCALHO = {'X': '1', 'x': '2'}
_TAMBORIM = {'X': '1', 'x': '2'}
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
        key = (note, instrument)
        if key not in _warned:
            _warned.add(key)
            if ' ' in note:
                logger.warning(
                    "Instrument '%s' has a note ('%s') that does not seem to be in 4/4 nor 6/8 time signature, so it is not supported by the conversion tool yet. It will be skipped.",
                    instrument, note,
                )
            else:
                logger.warning(
                    "Note '%s' for instrument '%s' is not supported by the conversion tool. It will be skipped.",
                    note, instrument,
                )
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


# ── helpers ───────────────────────────────────────────────────────────────────

def _translate_polys(
    polygroups: list[PolyGroup],
    table: dict[str, str],
    instrument: str,
    warn: bool = True,
) -> list[MappedPolyrhythm]:
    return [
        MappedPolyrhythm(
            pg.start, pg.end,
            [_map(n, table, instrument, warn=warn) for n in pg.notes],
        )
        for pg in polygroups
    ]


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

        pgs = brk.polygroups.get(name, [])

        if kind == 'surdo_split':
            # '1' notes are silent on Mid Surdo, '2' notes are silent on Low Surdo — both expected
            result.append(MappedTrack('9', [_map(n, _LOW_SURDO,  name, warn=False) for n in notes],
                                      _translate_polys(pgs, _LOW_SURDO,  name, warn=False)))
            result.append(MappedTrack('8', [_map(n, _MID_SURDO,  name, warn=False) for n in notes],
                                      _translate_polys(pgs, _MID_SURDO,  name, warn=False)))
        elif kind == 'high_surdo':
            result.append(MappedTrack('7', [_map(n, _HIGH_SURDO, name) for n in notes],
                                      _translate_polys(pgs, _HIGH_SURDO, name)))
        elif kind == 'caixa':
            result.append(MappedTrack('5', [_map(n, _CAIXA,      name) for n in notes],
                                      _translate_polys(pgs, _CAIXA,      name)))
        elif kind == 'repique':
            result.append(MappedTrack('3', [_map(n, _REPIQUE,    name) for n in notes],
                                      _translate_polys(pgs, _REPIQUE,    name)))
        elif kind == 'timbau':
            result.append(MappedTrack('6', [_map(n, _TIMBAU,     name) for n in notes],
                                      _translate_polys(pgs, _TIMBAU,     name)))
        elif kind == 'tamborim':
            result.append(MappedTrack('2', [_map(n, _TAMBORIM,   name) for n in notes],
                                      _translate_polys(pgs, _TAMBORIM,   name)))
        elif kind == 'chocalho':
            result.append(MappedTrack('1', [_map(n, _CHOCALHO,   name) for n in notes],
                                      _translate_polys(pgs, _CHOCALHO,   name)))
        elif kind == 'agogo':
            result.append(MappedTrack('0', [_map(n, _AGOGO,      name) for n in notes],
                                      _translate_polys(pgs, _AGOGO,      name)))

    return result


# ── increment 9: trim leading/trailing empty bars ─────────────────────────────

@dataclass
class TrimResult:
    tracks: list[MappedTrack]
    lead_bars: int
    trail_bars: int
    all_empty: bool


def trim_empty_bars(tracks: list[MappedTrack]) -> TrimResult:
    """Remove leading and trailing bars where every track is all rests ('0').

    A bar is 16 steps. A bar is empty when every step of every track is '0'.

    Args:
        tracks: List of MappedTrack objects (all same length, multiple of 16).

    Returns:
        TrimResult with the (possibly shorter) tracks and trim counts.
        If every bar is empty, all_empty=True and tracks is an empty list.
    """
    if not tracks:
        return TrimResult(tracks=[], lead_bars=0, trail_bars=0, all_empty=True)

    bar_count = len(tracks[0].notes) // 16

    def bar_is_empty(bar_index: int) -> bool:
        start = bar_index * 16
        end = start + 16
        for t in tracks:
            if any(n != '0' for n in t.notes[start:end]):
                return False
            for p in t.polyrhythms:
                if p.start < end and p.end >= start and any(n != '0' for n in p.notes):
                    return False
        return True

    lead_bars = 0
    while lead_bars < bar_count and bar_is_empty(lead_bars):
        lead_bars += 1

    trail_bars = 0
    while trail_bars < bar_count - lead_bars and bar_is_empty(bar_count - 1 - trail_bars):
        trail_bars += 1

    if lead_bars + trail_bars >= bar_count:
        return TrimResult(tracks=[], lead_bars=lead_bars, trail_bars=trail_bars, all_empty=True)

    start = lead_bars * 16
    end = (bar_count - trail_bars) * 16

    trimmed: list[MappedTrack] = []
    for t in tracks:
        new_notes = t.notes[start:end]
        new_polys = [
            MappedPolyrhythm(p.start - start, p.end - start, p.notes)
            for p in t.polyrhythms
            if p.start >= start and p.end < end
        ]
        trimmed.append(MappedTrack(t.instrument_id, new_notes, new_polys))

    return TrimResult(tracks=trimmed, lead_bars=lead_bars, trail_bars=trail_bars, all_empty=False)
