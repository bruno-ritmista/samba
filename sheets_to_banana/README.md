# sheets_to_banana

## What it does

Converts samba percursion notes in custom table-based format from Google Sheets into a [BananaDrum](https://www.bannadrum.net) link.

## Usage

### Python notebook in Google Collab

Open the [sheets_to_banana python notebook in Google Collab](https://colab.research.google.com/github/bruno-ritmista/samba/blob/main/sheets_to_banana/deployment/sheets_to_banana.ipynb) then follow the instructions in the notebook.


### Python scripts on your device

Clone the repository and navigate to it:

```bash
git clone https://github.com/bruno-ritmista/samba.git
cd samba
```

**Option A — Run directly from the repository root (no install required):**

```bash
pip install -r sheets_to_banana/requirements.txt
python sheets_to_banana <sheets_url> [--break INDEX] [--tempo BPM]
```

**Option B — Install the package, then run as a module:**

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