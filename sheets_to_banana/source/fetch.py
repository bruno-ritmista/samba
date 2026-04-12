"""Increment 1: Fetch CSV content from a Google Sheets URL.

Google Sheets can export any public sheet as CSV without an API key.
We just need to extract the spreadsheet ID (and optional sheet tab ID)
from the URL the user copies from their browser, then hit the export endpoint.
"""

import re
import requests


def extract_sheet_info(url: str) -> tuple[str, str | None]:
    """Extract the spreadsheet ID and optional sheet tab gid from a Sheets URL.

    Supports the common URL formats:
      https://docs.google.com/spreadsheets/d/SHEET_ID/edit#gid=GID
      https://docs.google.com/spreadsheets/d/SHEET_ID/edit
      https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=GID

    Returns:
        (sheet_id, gid) where gid may be None if not present in the URL.

    Raises:
        ValueError: if the URL does not look like a Google Sheets URL.
    """
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Not a valid Google Sheets URL: {url}")

    sheet_id = match.group(1)

    # gid can appear after #, & or ? — e.g. #gid=0 or &gid=123
    gid_match = re.search(r'[#&?]gid=(\d+)', url)
    gid = gid_match.group(1) if gid_match else None

    return sheet_id, gid


def build_export_url(sheet_id: str, gid: str | None) -> str:
    """Build the CSV export URL for a Google Sheet.

    This URL works for any sheet shared as "anyone with the link can view".
    No API key or login required.
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid is not None:
        url += f"&gid={gid}"
    return url


def fetch_csv(url: str) -> str:
    """Download the CSV content of a public Google Sheet.

    Args:
        url: Any Google Sheets URL (edit, share, or export link).

    Returns:
        The sheet content as a CSV string.

    Raises:
        ValueError: if the URL is not a Google Sheets URL.
        requests.HTTPError: if the download fails (e.g. sheet is private).
    """
    sheet_id, gid = extract_sheet_info(url)
    export_url = build_export_url(sheet_id, gid)
    response = requests.get(export_url)
    response.raise_for_status()
    response.encoding = 'utf-8'
    return response.text
