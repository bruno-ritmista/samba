"""Tests for render.py — Increment 3."""

from banana_to_pdf.mapping import Row
from banana_to_pdf.render import _build_pdf, render_pdf


def _rows(n_bars, n_rows=2):
    cells = ['●'] * (n_bars * 16)
    return [Row(f'Instrument {i}', cells) for i in range(n_rows)]


def test_render_pdf_writes_nonempty_file(tmp_path):
    out_path = tmp_path / 'out.pdf'
    render_pdf(_rows(4), n_bars=4, title='Test Break', url='https://bananadrum.net/?a2=x', out_path=out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_small_arrangement_fits_one_page():
    pdf = _build_pdf(_rows(4), n_bars=4, title='Test Break', url='https://bananadrum.net/?a2=x')
    assert len(pdf.pages) == 1


def test_large_arrangement_paginates():
    pdf = _build_pdf(_rows(200, n_rows=5), n_bars=200, title='Long Break', url='https://bananadrum.net/?a2=x')
    assert len(pdf.pages) >= 2
