"""Increment 3: Render mapped rows into a printable A4 PDF grid.

fpdf2-based: one "system" per 4 bars (64 step-cells) stacked down the
page, paginating automatically when a system would not fit.
"""

from pathlib import Path

from fpdf import FPDF

# Sibling of src/ in the repo; increment 4 packaging must ship this as
# package data so it resolves the same way once pip-installed.
_FONT_PATH = Path(__file__).parent.parent / 'assets' / 'DejaVuSans.ttf'

_MARGIN_MM = 10
_LABEL_WIDTH_MM = 34  # tunable: fits the longest label, "Repinique (Whippy)"
_ROW_HEIGHT_MM = 4.5  # ponytail: tune cell geometry against a printed A4 proof
_FONT_SIZE = 8
_TITLE_FONT_SIZE = 14
_STEPS_PER_BAR = 16
_BARS_PER_SYSTEM = 4
_STEPS_PER_SYSTEM = _STEPS_PER_BAR * _BARS_PER_SYSTEM
_SYSTEM_GAP_MM = 4


def _draw_system(pdf, rows, start_step, n_steps, first_bar_number, label_width, cell_width):
    x0 = pdf.l_margin
    y0 = pdf.get_y()
    n_bars_here = -(-n_steps // _STEPS_PER_BAR)

    pdf.set_x(x0)
    pdf.cell(label_width, _ROW_HEIGHT_MM, '')
    for bar in range(n_bars_here):
        steps_in_bar = min(_STEPS_PER_BAR, n_steps - bar * _STEPS_PER_BAR)
        pdf.cell(cell_width * steps_in_bar, _ROW_HEIGHT_MM, str(first_bar_number + bar), align='C')
    pdf.ln(_ROW_HEIGHT_MM)
    pdf.line(x0, pdf.get_y(), x0 + label_width + cell_width * n_steps, pdf.get_y())

    for row in rows:
        pdf.set_x(x0)
        pdf.cell(label_width, _ROW_HEIGHT_MM, row.label)
        for step in range(n_steps):
            pdf.cell(cell_width, _ROW_HEIGHT_MM, row.cells[start_step + step], align='C')
        pdf.ln(_ROW_HEIGHT_MM)

    grid_bottom_y = pdf.get_y()
    for step in range(0, n_steps + 1, 4):
        pdf.set_line_width(0.3 if step % _STEPS_PER_BAR == 0 else 0.1)
        x = x0 + label_width + cell_width * step
        pdf.line(x, y0, x, grid_bottom_y)
    pdf.set_line_width(0.2)


def _build_pdf(rows, n_bars, title, url):
    pdf = FPDF(orientation='P', format='A4')
    pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
    pdf.set_auto_page_break(False, margin=_MARGIN_MM)
    pdf.add_font('DejaVu', '', str(_FONT_PATH))
    pdf.add_page()

    pdf.set_font('DejaVu', size=_TITLE_FONT_SIZE)
    pdf.cell(0, 8, title or 'Untitled', link=url)
    pdf.ln(10)

    pdf.set_font('DejaVu', size=_FONT_SIZE)
    cell_width = (pdf.w - 2 * _MARGIN_MM - _LABEL_WIDTH_MM) / _STEPS_PER_SYSTEM
    system_height = (len(rows) + 1) * _ROW_HEIGHT_MM
    page_bottom = pdf.h - pdf.b_margin

    total_steps = n_bars * _STEPS_PER_BAR
    for start in range(0, total_steps, _STEPS_PER_SYSTEM):
        if pdf.get_y() + system_height > page_bottom:
            pdf.add_page()
            pdf.set_font('DejaVu', size=_FONT_SIZE)
        n_steps = min(_STEPS_PER_SYSTEM, total_steps - start)
        first_bar_number = start // _STEPS_PER_BAR + 1
        _draw_system(pdf, rows, start, n_steps, first_bar_number, _LABEL_WIDTH_MM, cell_width)
        pdf.ln(_SYSTEM_GAP_MM)

    return pdf


def render_pdf(rows, n_bars, title, url, out_path):
    """Render rows (from mapping.map_tracks) to an A4 PDF at out_path."""
    pdf = _build_pdf(rows, n_bars, title, url)
    pdf.output(str(out_path))
