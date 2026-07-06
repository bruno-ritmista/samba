"""Tests for __main__.py — Increment 4."""

import re
import sys
from pathlib import Path

from banana_to_pdf.__main__ import _default_output_path, main


def test_default_output_path_from_title():
    assert Path(_default_output_path('Levada Após')).name == 'Levada_Após.pdf'


def test_default_output_path_falls_back_when_title_empty():
    name = Path(_default_output_path('')).name
    assert re.fullmatch(r'Bananadrum_\d{8}_\d{6}\.pdf', name)


def test_main_end_to_end_writes_pdf(tmp_path, monkeypatch, capsys):
    url = 'https://bananadrum.net/?a2=4-4.120.1.1-4.16.9Hgm'
    out_path = tmp_path / 'out.pdf'
    monkeypatch.setattr(sys, 'argv', ['banana_to_pdf', url, '-o', str(out_path)])

    main()

    assert out_path.exists()
    assert out_path.stat().st_size > 0
    assert str(out_path) in capsys.readouterr().out
