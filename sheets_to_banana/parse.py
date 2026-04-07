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
  - Break header row   → non-empty col 0, note columns all empty, not
                         inside a bar group; marks the start of a new Break
  - Instrument row     → col 0 is an instrument name, cols 1-64 are notes
"""

import csv
import io
import re
from dataclasses import dataclass, field

_KEYWORDS_AS_REST = {'levada', 'virada'}

# Section label col 0 looks like "1 - 4" or "5-8"
_BAR_RANGE_RE = re.compile(r'^\d+\s*-\s*\d+$')


@dataclass
class Break:
    name: str
    tracks: dict[str, list[str]] = field(default_factory=dict)


def _normalize_note(cell: str) -> str:
    """Convert a raw CSV cell to a note character or rest marker '0'.

    Empty cells and Levada/Virada keywords both become '0'.
    All other values are returned as-is (e.g. 'X', '1', '2', 'O', 'OO').
    """
    stripped = cell.strip()
    if not stripped or stripped.lower() in _KEYWORDS_AS_REST:
        return '0'
    return stripped


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

    for raw_row in reader:
        # Ensure at least 65 cols so indexing is always safe
        row = raw_row + [''] * max(0, 65 - len(raw_row))
        col0 = row[0].strip()
        note_cells = [row[i].strip() for i in range(1, 65)]

        # ── Empty row: separator between bar groups or between breaks ──
        if not col0 and all(c == '' for c in note_cells):
            in_bar_group = False
            continue

        # ── Section label row: "1 - 4", "5 - 8", etc. ──
        if _BAR_RANGE_RE.match(col0):
            in_bar_group = True
            if current_break is None:
                # Notes before any break header → create an unnamed break
                current_break = Break(name='')
                breaks.append(current_break)
            continue

        # ── Break header row: non-empty name, no notes, not in a bar group ──
        if col0 and not in_bar_group and all(c == '' for c in note_cells):
            if current_break is not None:
                _finalize_break(current_break)
            current_break = Break(name=col0)
            breaks.append(current_break)
            continue

        # ── Instrument row: inside a bar group ──
        if col0 and in_bar_group and current_break is not None:
            notes = [_normalize_note(c) for c in note_cells]
            if col0 not in current_break.tracks:
                current_break.tracks[col0] = []
            current_break.tracks[col0].extend(notes)

    if current_break is not None:
        _finalize_break(current_break)

    return breaks
