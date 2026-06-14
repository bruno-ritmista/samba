"""Increment 7: Expand keyword cells to predefined note sequences."""

import logging
import re

logger = logging.getLogger(__name__)

# Characters that constitute a valid note cell (single or multi-char)
_NOTE_CHARS_RE = re.compile(r'^[XxOSLH/KWD0-9]+$', re.IGNORECASE)

# (keyword_lower, instrument_kind) → note sequence
_KEYWORD_TABLE: dict[tuple[str, str], list[str]] = {
    ('levada', 'surdo_split'):  '2 0 0 1 0 0 0 2 0 0 0 1 0 0 0 0'.split(),
    ('levada', 'high_surdo'):   '0 0 0 0 X 0 X 0 0 0 0 0 X X 0 X'.split(),
    ('levada', 'repique'):      'X x / O X x / O X x / O X x / O'.split(),
    ('levada', 'caixa'):        'X X x / X x / x X x / x X x / x'.split(),
    ('levada', 'tamborim'):     'X x x x X x x x X x x x X x x x'.split(),
    ('levada', 'chocalho'):     'X x x x X x x x X x x x X x x x'.split(),
    ('levada', 'agogo'):        'L 0 0 H H 0 L 0 L 0 H 0 H 0 0 L'.split(),
    ('virada', 'surdo_split'):  '2 0 0 0 0 1 0 0'.split(),
    ('virada', 'high_surdo'):   '0 0 0 0 0 0 X 0'.split(),
    ('virada', 'repique'):      'X x / O X 0 / 0'.split(),
    ('virada', 'caixa'):        'X X x / X 0 x 0'.split(),
    ('virada', 'tamborim'):     'X x x x X 0 x 0'.split(),
    ('virada', 'chocalho'):     'X x x x X 0 x 0'.split(),
    ('virada', 'agogo'):        'L 0 0 H H 0 L 0'.split(),
}

# 'Corte' on Surdo 3 (high_surdo) is not a fixed pattern but a run-length
# shorthand: each beat carrying a 'Corte' cell expands based on whether it is
# followed by another 'Corte' beat. A 'mid' beat (followed by more corte) hits
# once on its third step; the 'end' beat (last in the run) hits twice. This one
# rule reproduces both the 3-beat short corte and the 7-beat long corte.
_CORTE_MID = '0 0 X 0'.split()
_CORTE_END = '0 X 0 X'.split()


def _classify(name: str) -> str:
    """Map a raw instrument name to its canonical kind for table lookup."""
    n = name.lower()
    if 'surdo' in n:
        return 'high_surdo' if ('mor' in n or '3' in n) else 'surdo_split'
    if 'repique' in n or 'repinique' in n: return 'repique'
    if 'caixa'    in n: return 'caixa'
    if 'tamborim' in n: return 'tamborim'
    if 'chocalho' in n: return 'chocalho'
    if 'agog'     in n: return 'agogo'
    return n  # fallback: normalised raw name


def _is_keyword(cell: str) -> bool:
    return bool(cell) and ' ' not in cell and not _NOTE_CHARS_RE.match(cell)


def _corte_pattern(cells: list[str], i: int, span: int) -> list[str]:
    """Pick the corte sub-pattern for the cell at `i` (covering `span` cols).

    A corte beat is 'end' when it is the last in a consecutive run of corte
    cells (no corte cell at the next beat), otherwise 'mid'. Corte cells are
    always one beat apart, so the next corte (if any) sits at i + span.
    """
    next_i = i + span
    is_last = not (next_i < len(cells) and cells[next_i].lower() == 'corte')
    return _CORTE_END if is_last else _CORTE_MID


def expand_keywords(instrument: str, cells: list[str]) -> list[str]:
    """Replace keyword cells with their predefined note sequences.

    Each element of `cells` is either a note character, an empty string
    (rest from a non-merged cell), or a keyword string.  Returns a flat
    list of the same total length with keywords replaced by note characters.
    """
    kind = _classify(instrument)
    result: list[str] = []
    i = 0
    while i < len(cells):
        cell = cells[i]
        if not _is_keyword(cell):
            result.append(cell)
            i += 1
            continue

        # Span = keyword cell + consecutive following empty cells (merged range)
        span = 1
        while i + span < len(cells) and cells[i + span] == '':
            span += 1
        span = min(span, 4)  # keywords always cover exactly one beat (4 sixteenth-note steps)

        if cell.lower() == 'corte' and kind == 'high_surdo':
            pattern = _corte_pattern(cells, i, span)
        else:
            pattern = _KEYWORD_TABLE.get((cell.lower(), kind))
        if pattern is None:
            logger.warning(
                "Note '%s' for instrument '%s' is not supported by the conversion tool. It will be skipped.",
                cell, instrument,
            )
            result.extend(['0'] * span)
        else:
            # Slice from the pattern at the beat-aligned offset so that a
            # keyword on beat 2 (i=4) gets notes 5-8, beat 3 gets 9-12, etc.
            offset = i % len(pattern)
            tiled = pattern * ((offset + span) // len(pattern) + 1)
            result.extend(tiled[offset:offset + span])

        i += span

    return result
