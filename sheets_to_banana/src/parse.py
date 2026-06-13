"""Increments 2 & 8: Parse CSV content into Break objects.

Increment 8 adds detection of 6/8 cells: merged cells that span exactly 16
columns (one full bar), contain space-separated note characters, and are not
keywords.  These are extracted as PolyGroup objects before keyword expansion
and stored in Break.polygroups for downstream processing.

Each Break represents a rhythmic section of the song. Within a Break,
each instrument's notes are stored as a flat list of note characters —
all bar groups (bars 1-4, 5-8, …) concatenated in order.

The Z-pattern layout of the CSV (same 64 columns reused for each 4-bar
group) is stitched together here so that downstream code only sees a
single sequence per instrument.

Row types recognised:
  - Empty row          → separator, ignored
  - Section label row  → col 0 matches "N - M" (e.g. "1 - 4"); marks the
                         start of a new 4-bar group
  - Break header row   → col 0 OR col 1 is non-empty (rest of the row is
                         empty) and we are not inside a bar group; marks the
                         start of a new Break. Breaks with no tracks (e.g.
                         the song title row) are dropped from the result.
  - Instrument row     → col 0 is an instrument name, cols 1-64 are notes
"""

import csv
import io
import logging
import re
from dataclasses import dataclass, field

from .keywords import expand_keywords

logger = logging.getLogger(__name__)

# Section label col 0 looks like "1 - 4" or "5-8"
_BAR_RANGE_RE = re.compile(r'^\d+\s*-\s*\d+$')

# Valid note characters that may appear in 6/8 cells
_POLY_NOTE_CHARS = frozenset('XxOSLH/KWD0123456789')


@dataclass
class PolyGroup:
    """A polyrhythm cell detected in an instrument row.

    Represents a merged cell spanning exactly 4 columns (one quarter-note beat):
    one non-empty cell followed by exactly 3 empty cells.  The 4 base
    sixteenth-note slots (start..end inclusive, end = start + 3) are replaced
    by exactly 3 polyrhythmic notes in BananaDrum's polyrhythm model.
    """
    start: int          # 0-based absolute slot index (bar_group_offset + col)
    end: int            # start + 3 (always 4-column span)
    notes: list[str]    # exactly 3 raw note characters (may include '0' for pauses)


@dataclass
class Break:
    name: str
    tracks: dict[str, list[str]] = field(default_factory=dict)
    polygroups: dict[str, list[PolyGroup]] = field(default_factory=dict)


def _assign_poly_slots(cell: str) -> list[str]:
    """Map a 4-column merged cell's raw content to exactly 3 poly note slots.

    Whitespace at the start or end of the cell string indicates a pause (rest)
    at the corresponding position.  Internal-only spaces mean the pause is in
    the middle slot.
    """
    tokens = cell.split()
    if not tokens:
        logger.warning("Empty 6/8 cell content; treating as 3 rests")
        return ['0', '0', '0']
    if len(tokens) > 3:
        logger.warning(
            "6/8 cell has %d tokens (max 3); truncating: %r", len(tokens), cell
        )
        tokens = tokens[:3]
    has_leading  = cell[0]  == ' '
    has_trailing = cell[-1] == ' '
    if len(tokens) == 3:
        return tokens
    if len(tokens) == 2:
        if has_leading:
            return ['0', tokens[0], tokens[1]]
        if has_trailing:
            return [tokens[0], tokens[1], '0']
        return [tokens[0], '0', tokens[1]]   # pause in middle
    # len(tokens) == 1
    if has_leading:
        return ['0', tokens[0], '0']
    return [tokens[0], '0', '0']


def _extract_polygroups(note_cells: list[str], bar_group_offset: int) -> list[PolyGroup]:
    """Scan note_cells for 6/8 polyrhythm cells and return PolyGroup objects.

    A 6/8 cell is a non-empty cell that:
      - contains at least one space (space-separated note chars)
      - consists only of valid note characters (no keyword text)
      - is followed by exactly 3 consecutive empty cells (4-column span)

    Three poly slots are assigned based on leading/trailing whitespace in the
    cell string (see _assign_poly_slots).  Detected cells and their 3 trailing
    empty cells are blanked in-place so that expand_keywords sees rests.
    """
    groups: list[PolyGroup] = []
    i = 0
    while i < len(note_cells):
        raw_cell = note_cells[i]
        cell = raw_cell.strip()   # stripped for detection checks
        if (cell
                and ' ' in cell
                and all(c in _POLY_NOTE_CHARS for c in cell if c != ' ')):
            # Require exactly 3 trailing empty cells (4-column span)
            if (i + 3 < len(note_cells)
                    and note_cells[i + 1].strip() == ''
                    and note_cells[i + 2].strip() == ''
                    and note_cells[i + 3].strip() == ''):
                slots = _assign_poly_slots(raw_cell)  # raw: preserves whitespace
                groups.append(PolyGroup(
                    start=bar_group_offset + i,
                    end=bar_group_offset + i + 3,
                    notes=slots,
                ))
                for j in range(i, i + 4):
                    note_cells[j] = ''
                i += 4
                continue
        i += 1
    return groups


def _normalize_note(cell: str) -> str:
    """Convert a raw CSV cell to a note character or rest marker '0'."""
    stripped = cell.strip()
    return stripped if stripped else '0'


def _finalize_break(brk: Break) -> None:
    """Pad all tracks to the same length, then trim trailing all-rest bars.

    Instruments that appear in only some bar groups end up shorter than
    others. This pads them so every track in the break has equal length,
    then trims trailing bars that are entirely rests across all tracks.
    """
    if not brk.tracks:
        return
    max_len = max(len(v) for v in brk.tracks.values())
    for notes in brk.tracks.values():
        notes.extend(['0'] * (max_len - len(notes)))

    # Find the last step with a non-rest note across all tracks
    last_active = -1
    for notes in brk.tracks.values():
        for i in range(len(notes) - 1, -1, -1):
            if notes[i] != '0':
                last_active = max(last_active, i)
                break
    if last_active >= 0:
        trimmed_len = ((last_active // 16) + 1) * 16
        for notes in brk.tracks.values():
            del notes[trimmed_len:]


def parse_song_title(csv_text: str) -> str:
    """Return the song title from the first break-header row in the CSV.

    The song title row has col 0 empty, col 1 non-empty, and all other cols
    empty.  Returns the raw cell value, or '' if no such row is found.
    """
    reader = csv.reader(io.StringIO(csv_text))
    for raw_row in reader:
        row = raw_row + [''] * max(0, 65 - len(raw_row))
        col0 = row[0].strip()
        col1 = row[1].strip()
        rest_empty = all(c.strip() == '' for c in row[2:65])
        if not col0 and col1 and rest_empty:
            return col1
    return ''


def parse_sheet(csv_text: str) -> list[Break]:
    """Parse CSV text into a list of Break objects.

    Each Break holds one dict mapping instrument name → full note sequence.
    All bar groups within a break are concatenated into one flat list, so
    a 2-bar-group break yields 128-step sequences per instrument.

    Args:
        csv_text: Raw CSV text as returned by fetch_csv.

    Returns:
        List of Break objects in sheet order. Returns an empty list for
        empty input.
    """
    if not csv_text:
        return []
    reader = csv.reader(io.StringIO(csv_text))
    breaks: list[Break] = []
    current_break: Break | None = None
    in_bar_group = False
    bar_group_offset = 0  # steps accumulated before the current bar group
    bar_group_number = 0
    prev_group_instruments: set[str] | None = None
    current_group_instruments: set[str] = set()

    def _close_bar_group() -> None:
        nonlocal prev_group_instruments, current_group_instruments, bar_group_number
        if prev_group_instruments is not None:
            added   = current_group_instruments - prev_group_instruments
            removed = prev_group_instruments - current_group_instruments
            if added or removed:
                break_name = current_break.name if current_break else '?'
                logger.warning(
                    "Break \"%s\" bar group %d has different instruments than group %d: "
                    "+[%s] -[%s]",
                    break_name, bar_group_number + 1, bar_group_number,
                    ', '.join(sorted(added)), ', '.join(sorted(removed)),
                )
        prev_group_instruments = current_group_instruments
        current_group_instruments = set()
        bar_group_number += 1

    for raw_row in reader:
        # Ensure at least 65 cols so indexing is always safe
        row = raw_row + [''] * max(0, 65 - len(raw_row))
        col0 = row[0].strip()
        raw_note_cells = [row[i] for i in range(1, 65)]
        note_cells = [c.strip() for c in raw_note_cells]

        # ── Empty row: separator between bar groups or between breaks ──
        if not col0 and all(c == '' for c in note_cells):
            if in_bar_group:
                _close_bar_group()
                bar_group_offset += 64  # one 64-step group just completed
            in_bar_group = False
            continue

        # ── Section label row: "1 - 4", "5 - 8", etc. ──
        if _BAR_RANGE_RE.match(col0):
            if in_bar_group:
                # No empty row between groups — still increment
                _close_bar_group()
                bar_group_offset += 64
            in_bar_group = True
            if current_break is None:
                # Notes before any break header → create an unnamed break
                current_break = Break(name='')
                breaks.append(current_break)
            continue

        # ── Break header row: name in col 0 or col 1, rest empty, not in bar group ──
        # In many sheets col 0 is empty and the name is in col 1 (merged cell).
        col1 = note_cells[0] if note_cells else ''
        rest_empty = all(c == '' for c in note_cells[1:])
        header_name = col0 or col1
        if header_name and not in_bar_group and (not col0 or not col1) and rest_empty:
            if current_break is not None:
                _finalize_break(current_break)
            current_break = Break(name=header_name)
            breaks.append(current_break)
            bar_group_offset = 0
            bar_group_number = 0
            prev_group_instruments = None
            current_group_instruments = set()
            continue

        # ── Instrument row: inside a bar group ──
        if col0 and in_bar_group and current_break is not None:
            # Pass raw cells so _extract_polygroups can read whitespace position;
            # re-strip after so blanked poly slots appear as rests for expand_keywords.
            groups = _extract_polygroups(raw_note_cells, bar_group_offset)
            note_cells = [c.strip() for c in raw_note_cells]
            if groups:
                if col0 not in current_break.polygroups:
                    current_break.polygroups[col0] = []
                current_break.polygroups[col0].extend(groups)
            notes = [_normalize_note(c) for c in expand_keywords(col0, note_cells)]
            if col0 not in current_break.tracks:
                # Pre-pad with rests for all bar groups before this one
                current_break.tracks[col0] = ['0'] * bar_group_offset
            current_break.tracks[col0].extend(notes)
            current_group_instruments.add(col0)

    if current_break is not None:
        _finalize_break(current_break)

    # Drop header-only rows (e.g. song title) that collected no tracks
    return [b for b in breaks if b.tracks]
