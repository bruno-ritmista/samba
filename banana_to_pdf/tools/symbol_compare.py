"""Render a PDF comparing candidate glyphs for mapping.py's GLYPHS dict.

Usage:
    python tools/symbol_compare.py [candidates.txt] [-o out.pdf]
    (reads stdin if candidates.txt is omitted)

Input format: one group per block, separated by a blank line. First line
of a block is the label, remaining lines are Unicode codepoints (hex,
with or without a "U+" prefix), one per line:

    buzz
    168D
    2162
    29FB

    rim
    0631
"""

import argparse
import sys
import unicodedata
from pathlib import Path

from fpdf import FPDF

_FONT_PATH = Path(__file__).parent.parent / 'src' / 'assets' / 'DejaVuSans.ttf'


def _parse_groups(text: str) -> list[tuple[str, list[str]]]:
    groups = []
    for block in text.strip().split('\n\n'):
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue
        label, codes = lines[0], lines[1:]
        glyphs = [chr(int(code.removeprefix('U+').removeprefix('u+'), 16)) for code in codes]
        groups.append((label, glyphs))
    return groups


def _build_pdf(groups: list[tuple[str, list[str]]]) -> FPDF:
    pdf = FPDF(orientation='P', format='A4')
    pdf.set_margins(10, 10, 10)
    pdf.add_font('DejaVu', '', str(_FONT_PATH))
    pdf.add_page()

    pdf.set_font('DejaVu', size=16)
    pdf.cell(0, 10, 'Glyph candidates', new_x='LMARGIN', new_y='NEXT')

    for label, glyphs in groups:
        pdf.ln(4)
        pdf.set_font('DejaVu', size=11)
        pdf.cell(0, 6, label, new_x='LMARGIN', new_y='NEXT')

        tagged = [(f'U+{ord(g):04X}', g) for g in glyphs]

        # actual-size, as it would appear in a 4.5mm grid cell at 8pt (see render.py)
        pdf.set_font('DejaVu', size=8)
        for tag, g in tagged:
            pdf.cell(20, 6, f'{tag}:', border=0)
            pdf.cell(10, 6, g, border=1, align='C')
        pdf.ln(8)

        # enlarged, for legibility comparison
        pdf.set_font('DejaVu', size=28)
        for _, g in tagged:
            pdf.cell(20, 12, g, border=1, align='C')
        pdf.ln(16)

        pdf.set_font('DejaVu', size=7)
        for tag, g in tagged:
            name = unicodedata.name(g, 'UNKNOWN')
            pdf.cell(0, 4, f'{tag}: {name}', new_x='LMARGIN', new_y='NEXT')
        pdf.ln(2)

    return pdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('input', nargs='?', type=Path, help='text file of groups (default: stdin)')
    parser.add_argument('-o', '--out', type=Path, default=Path('symbol_comparison.pdf'))
    args = parser.parse_args()

    text = args.input.read_text(encoding='utf-8') if args.input else sys.stdin.read()
    groups = _parse_groups(text)
    pdf = _build_pdf(groups)
    pdf.output(str(args.out))
    print(args.out)


if __name__ == '__main__':
    main()
