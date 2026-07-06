"""True end-to-end coverage (issue #13): real Google Sheet → real pipeline → BananaDrum URL(s).

canonical_csv() is the in-repo record of exactly what the live sheet must
contain. Regenerate the sheet content with:

    python tests/test_e2e.py

then paste the printed CSV into LIVE_SHEET_URL (view-only, populated by hand —
see doc/e2e_test_plan.md for why there is no Sheets-API writer).
"""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.csv_helpers import make_csv, section_label, instrument_row, empty_row, break_header
from sheet_to_banana.fetch import extract_sheet_info, build_export_url

LIVE_SHEET_URL = (
    'https://docs.google.com/spreadsheets/d/'
    '1iksYNiaMQMnQzk6Qsji2RlzqjvoIB_IPf7YyFBqQQYw/edit?gid=1185929018#gid=1185929018'
)

# Frozen after the sheet is populated and each URL is verified in bananadrum.net.
EXPECTED_URLS: list[str] = [
    'https://bananadrum.net/?t=Levada&a2=4-4.120.1.1-4.16.5Bn6Xf3.9Hgm.8SLHS.319000000-3nq',
    'https://bananadrum.net/?t=Virada&a2=4-4.120.1.1-4.16.5BlG4mb.74Tw',
]


def canonical_csv() -> str:
    """Broad multi-break sheet: keywords (levada/virada/corte), 6/8 polyrhythm, surdo split."""
    levada_beat = ['levada'] + [''] * 3
    virada_beat = ['Virada'] + [''] * 3
    corte_beat = ['Corte'] + [''] * 3

    return make_csv(
        break_header('E2E Test Song'),

        break_header('Levada'),
        section_label('1 - 4'),
        instrument_row('Caixa', levada_beat * 4 + [''] * 48),
        instrument_row('Surdo 1a/2a', levada_beat * 4 + [''] * 48),
        instrument_row('Repique', ['X X X'] + [''] * 3 + [''] * 60),
        empty_row(),

        break_header('Virada (Banana Drum)'),
        section_label('1 - 4'),
        instrument_row('Caixa', virada_beat * 2 + [''] * 56),
        instrument_row('Surdo 3', [''] * 4 + corte_beat * 3 + [''] * 48),
    )


def test_e2e_live_sheet(monkeypatch, capsys):
    export_url = build_export_url(*extract_sheet_info(LIVE_SHEET_URL))
    try:
        requests.get(export_url, timeout=10)
    except (requests.ConnectionError, requests.Timeout):
        pytest.skip("Google Sheets unreachable")

    monkeypatch.setattr(sys, 'argv', ['sheet_to_banana', LIVE_SHEET_URL])
    from sheet_to_banana.__main__ import main
    main()

    out = capsys.readouterr().out
    assert out.strip().splitlines() == EXPECTED_URLS


if __name__ == '__main__':
    print(canonical_csv())
