"""Increment 5: CLI entry point for sheets_to_banana.

Usage:
    python -m sheets_to_banana <sheets_url> [--break INDEX] [--tempo BPM]

Options:
    <sheets_url>     Google Sheets URL (public / anyone-with-link).
    --break INDEX    Which break to encode, 1-based (default: print all).
    --tempo BPM      Tempo in BPM (default: 120).
"""

import argparse
import logging
import re
import sys

from sheets_to_banana.fetch import fetch_csv
from sheets_to_banana.parse import parse_sheet, parse_song_title
from sheets_to_banana.mapping import map_break
from sheets_to_banana.encode import encode_url

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s %(name)s: %(message)s',
        stream=sys.stderr,
    )


def main() -> None:
    _setup_logging()

    parser = argparse.ArgumentParser(
        prog='python -m sheets_to_banana',
        description='Convert a public Google Sheet of percussion notes into a BananaDrum URL.',
    )
    parser.add_argument('url', help='Google Sheets URL (public share link)')
    parser.add_argument('--break', dest='break_index', type=int, default=None,
                        metavar='INDEX', help='Break to encode, 1-based (default: all)')
    parser.add_argument('--tempo', type=int, default=120,
                        metavar='BPM', help='Tempo in BPM (default: 120)')
    args = parser.parse_args()

    try:
        csv_text = fetch_csv(args.url)
    except ValueError as e:
        logger.error("Invalid URL: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to fetch sheet: %s", e)
        sys.exit(1)

    raw_song_title = parse_song_title(csv_text)
    # Take the segment after the last ' - ' (e.g. "... - Mangueira 2023" → "Mangueira 2023")
    song_short = raw_song_title.split(' - ')[-1].strip() if raw_song_title else ''

    breaks = parse_sheet(csv_text)

    if not breaks:
        logger.error("No breaks found in sheet.")
        sys.exit(1)

    if args.break_index is not None:
        if args.break_index < 1 or args.break_index > len(breaks):
            logger.error(
                "Break %d out of range (sheet has %d break(s): 1–%d).",
                args.break_index, len(breaks), len(breaks),
            )
            sys.exit(1)
        selected = [(args.break_index, breaks[args.break_index - 1])]
    else:
        selected = [(i + 1, brk) for i, brk in enumerate(breaks)]

    for num, brk in selected:
        tracks = map_break(brk)
        if not tracks:
            logger.error("Break %d \"%s\" — no recognised instruments.", num, brk.name)
            continue

        n_bars = max(len(t.notes) for t in tracks) // 16
        logger.info("Break %d \"%s\" — %d bars", num, brk.name, n_bars)
        for name, notes in brk.tracks.items():
            hit_count = sum(1 for n in notes if n != '0')
            logger.info("  %-20s  %d hits", name, hit_count)

        clean_break = re.sub(r'\s*\(.*\)\s*$', '', brk.name).strip()
        title = f"{song_short} - {clean_break}" if song_short else clean_break
        url = encode_url(tracks, tempo=args.tempo, n_bars=n_bars, title=title)
        print(url)


if __name__ == '__main__':
    main()
