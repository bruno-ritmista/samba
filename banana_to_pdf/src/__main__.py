"""Increment 4: CLI entry point for banana_to_pdf.

Usage:
    python -m banana_to_pdf <bananadrum_url> [-o out.pdf]
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from pathlib import Path

from banana_to_pdf.decode import decode_url
from banana_to_pdf.mapping import map_tracks
from banana_to_pdf.render import render_pdf

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path.cwd() / 'output'


def _default_output_path(title: str) -> str:
    slug = re.sub(r'[^\w\-]+', '_', title).strip('_') if title else ''
    name = f'{slug}.pdf' if slug else f'Bananadrum_{datetime.now():%Y%m%d_%H%M%S}.pdf'
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return str(OUTPUT_DIR / name)


def main() -> None:
    logging.basicConfig(level=logging.WARNING, format='%(levelname)-8s %(name)s: %(message)s', stream=sys.stderr)

    parser = argparse.ArgumentParser(
        prog='python -m banana_to_pdf',
        description='Convert a BananaDrum shareable URL into a printable PDF grid.',
    )
    parser.add_argument('url', help='BananaDrum shareable URL')
    parser.add_argument('-o', '--output', default=None,
                        help='Output PDF path (default: derived from title)')
    args = parser.parse_args()

    try:
        decoded = decode_url(args.url)

        rows = map_tracks(decoded)
        if not rows:
            logger.error("No recognised instruments with notes; nothing to render.")
            sys.exit(1)

        out_path = args.output or _default_output_path(decoded.title)
        render_pdf(rows, decoded.n_bars, decoded.title, args.url, out_path)
    except Exception as e:
        logger.error("Failed to generate PDF: %s", e)
        sys.exit(1)

    print(out_path)


if __name__ == '__main__':
    main()
