"""Increment 3: Render mapped rows into a printable A4 PDF grid.

fpdf2-based: one "system" per 4 bars (64 step-cells) stacked down the
page, paginating automatically when a system would not fit.
"""

from pathlib import Path

from fpdf import FPDF

# Ships as package data (see pyproject.toml [tool.setuptools.package-data]),
# so this sibling-of-render.py path resolves the same editable or installed.
_FONT_PATH = Path(__file__).parent / 'assets' / 'DejaVuSans.ttf'

_MARGIN_MM = 10
_LABEL_WIDTH_MM = 34  # tunable: fits the longest label, "Repinique (Whippy)"
_ROW_HEIGHT_MM = 4.5  # ponytail: tune cell geometry against a printed A4 proof
_FONT_SIZE = 8
_TITLE_FONT_SIZE = 14
_FOOTER_FONT_SIZE = 7
_STEPS_PER_BAR = 16
_BARS_PER_SYSTEM = 4
_STEPS_PER_SYSTEM = _STEPS_PER_BAR * _BARS_PER_SYSTEM
_SYSTEM_GAP_MM = 4
_GRID_GREY = (170, 170, 170)
_LINK_BLUE = (0, 0, 238)
_FOOTER_TEXT = 'This file was created by banana_to_pdf'


class _BananaDrumPDF(FPDF):
    def footer(self):
        self.set_y(-7)
        self.set_font('DejaVu', size=_FOOTER_FONT_SIZE)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, _FOOTER_TEXT, align='C')
        self.set_text_color(0, 0, 0)


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
    rows_top_y = pdf.get_y()
    grid_right_x = x0 + label_width + cell_width * n_steps
    pdf.line(x0, rows_top_y, grid_right_x, rows_top_y)

    for row in rows:
        pdf.set_x(x0)
        pdf.cell(label_width, _ROW_HEIGHT_MM, row.label)
        for step in range(n_steps):
            pdf.cell(cell_width, _ROW_HEIGHT_MM, row.cells[start_step + step], align='C')
        pdf.ln(_ROW_HEIGHT_MM)
        pdf.set_draw_color(*_GRID_GREY)
        pdf.set_line_width(0.1)
        pdf.line(x0 + label_width, pdf.get_y(), grid_right_x, pdf.get_y())
        pdf.set_draw_color(0, 0, 0)

    grid_bottom_y = pdf.get_y()

    pdf.set_draw_color(*_GRID_GREY)
    pdf.set_line_width(0.1)
    for step in range(0, n_steps + 1):
        x = x0 + label_width + cell_width * step
        pdf.line(x, rows_top_y, x, grid_bottom_y)
    pdf.set_draw_color(0, 0, 0)

    for step in range(0, n_steps + 1, 4):
        x = x0 + label_width + cell_width * step
        if step % _STEPS_PER_BAR == 0:
            # Bar boundaries span the header row too; beat divisions inside a
            # bar would otherwise cut through the centered bar-number text.
            pdf.set_line_width(0.3)
            pdf.line(x, y0, x, grid_bottom_y)
        else:
            pdf.set_line_width(0.1)
            pdf.line(x, rows_top_y, x, grid_bottom_y)
    pdf.set_line_width(0.2)


def _draw_title(pdf, title, url):
    link_text = ' (Bananadrum Link)'

    pdf.set_font('DejaVu', size=_TITLE_FONT_SIZE)
    title_w = pdf.get_string_width(title)
    pdf.set_font('DejaVu', style='U', size=_TITLE_FONT_SIZE)
    link_w = pdf.get_string_width(link_text)

    pdf.set_x((pdf.w - title_w - link_w) / 2)
    pdf.set_font('DejaVu', size=_TITLE_FONT_SIZE)
    pdf.cell(title_w, 8, title)
    pdf.set_font('DejaVu', style='U', size=_TITLE_FONT_SIZE)
    pdf.set_text_color(*_LINK_BLUE)
    pdf.cell(link_w, 8, link_text, link=url)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)


def _build_pdf(rows, n_bars, title, url):
    pdf = _BananaDrumPDF(orientation='P', format='A4')
    pdf.set_margins(_MARGIN_MM, _MARGIN_MM, _MARGIN_MM)
    pdf.set_auto_page_break(False, margin=_MARGIN_MM)
    pdf.add_font('DejaVu', '', str(_FONT_PATH))
    pdf.add_page()

    if title:
        _draw_title(pdf, title, url)

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
