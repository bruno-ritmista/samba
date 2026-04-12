# sheets_to_banana

Converts a Google Sheet of samba percussion notes into a shareable BananaDrum link.

## What it does

Takes a public Google Sheets URL containing percussion notes in a custom table-based format and generates a URL to play those notes in [BananaDrum](https://bananadrum.net).

## Usage

```bash
python -m sheets_to_banana <sheets_url> [--break INDEX] [--tempo BPM]
```

**Arguments:**
- `<sheets_url>` — Public Google Sheets URL (anyone-with-link access)
- `--break INDEX` — Which break to encode (1-based; default: all)
- `--tempo BPM` — Tempo in BPM (default: 120)

**Example:**
```bash
python -m sheets_to_banana https://docs.google.com/spreadsheets/d/ABC123/edit --break 1 --tempo 110
```

The script prints the BananaDrum URL to stdout.

## Installation

```bash
pip install -r requirements.txt
```
