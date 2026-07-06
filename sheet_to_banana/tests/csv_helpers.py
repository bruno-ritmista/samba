"""Shared CSV-building helpers, used by both unit tests and the E2E canonical sheet."""

import csv
import io


def make_csv(*rows: list[str]) -> str:
    """Build a CSV string from a list of rows (each row is a list of strings)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def section_label(bar_range: str = '1 - 4') -> list[str]:
    """A minimal section-label row (col 0 = bar range, rest empty)."""
    return [bar_range] + [''] * 64


def instrument_row(name: str, notes: list[str]) -> list[str]:
    """An instrument row with exactly 64 note cells."""
    padded = (notes + [''] * 64)[:64]
    return [name] + padded


def empty_row() -> list[str]:
    return [''] * 65


def break_header(name: str) -> list[str]:
    return [name] + [''] * 64
