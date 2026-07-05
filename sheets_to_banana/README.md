# sheets_to_banana

## What it does

Converts samba percussion notes in custom table-based format from Google Sheets into a [BananaDrum](https://bananadrum.net) link.

❓ Something not working? See the [FAQ](FAQ.md).


## How to use it

Before using sheets_to_banana, make sure you satisfy the prerequisites described below.

### Option 1 (recommended for most users): Run on your internet browser

Open the [sheets_to_banana python notebook in Google Colab](https://colab.research.google.com/github/bruno-ritmista/samba/blob/main/sheets_to_banana/deployment/sheets_to_banana.ipynb) then follow the instructions on the screen.


### Option 2 (recommended for advanced users): Run as script on your computer

Clone the [repository](https://github.com/bruno-ritmista/samba) and navigate to it:

```bash
git clone https://github.com/bruno-ritmista/samba.git
cd samba
```

**Option 2.1 — Run directly from the repository root (no install required):**

```bash
pip install -r sheets_to_banana/requirements.txt
python sheets_to_banana <sheets_url> [--break INDEX] [--tempo BPM]
```

**Option 2.2 — Install the package, then run as a module:**

```bash
pip install sheets_to_banana/
python -m sheets_to_banana <sheets_url> [--break INDEX] [--tempo BPM]
```

**Arguments:**
- `<sheets_url>` — Public Google Sheets URL (anyone-with-link access)
- `--break INDEX` — Which break to encode (1-based; default: all)
- `--tempo BPM` — Tempo in BPM (default: 120)

**Example:**
```bash
python sheets_to_banana https://docs.google.com/spreadsheets/d/ABC123/edit --break 1 --tempo 110
```

The script prints the BananaDrum URL to stdout.

## Prerequisites

**Option 1 (recommended for most users): Run on your internet browser:**
- A Google account.
- A modern browser (Chrome, Firefox, Safari, or Edge).
- A Google Sheet in the expected notation format, shared as "Anyone with the link" — start from the [template sheet](https://docs.google.com/spreadsheets/d/1NL_UpLsLf1YSnPphxxP7Mdu-IdTzckSYDjZsCih0LCw/edit?gid=991712970#gid=991712970) and copy it into your own Drive.

**Option 2 (recommended for advanced users): Run as script on your computer:**
- Python ≥3.11
- git
- pip
- A Google Sheet in the expected notation format, shared as "Anyone with the link" — start from the [template sheet](https://docs.google.com/spreadsheets/d/1NL_UpLsLf1YSnPphxxP7Mdu-IdTzckSYDjZsCih0LCw/edit?gid=991712970#gid=991712970) and copy it into your own Drive.