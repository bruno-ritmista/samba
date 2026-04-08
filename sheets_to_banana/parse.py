"""Increment 2: Parse CSV content into Break objects.

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


@dataclass
class Break:
    name: str
    tracks: dict[str, list[str]] = field(default_factory=dict)


def _normalize_note(cell: str) -> str:
    """Convert a raw CSV cell to a note character or rest marker '0'."""
    stripped = cell.strip()
    return stripped if stripped else '0'


def _finalize_break(brk: Break) -> None:
    """Pad all tracks in a break to the same length with rests.

    Instruments that appear in only some bar groups end up shorter than
    others. This pads them so every track in the break has equal length.
    """
    if not brk.tracks:
        return
    max_len = max(len(v) for v in brk.tracks.values())
    for notes in brk.tracks.values():
        notes.extend(['0'] * (max_len - len(notes)))


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
        note_cells = [row[i].strip() for i in range(1, 65)]

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
