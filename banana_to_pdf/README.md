# banana_to_pdf

## What it does

Converts a shareable [BananaDrum](https://bananadrum.net) link into a printable A4 PDF grid of the samba percussion notes.

❓ Something not working? See the [FAQ](FAQ.md).


## How to use it

Before using banana_to_pdf, make sure you satisfy the [prerequisites](https://github.com/bruno-ritmista/samba/blob/main/banana_to_pdf/README.md#prerequisites).

### Option 1 (recommended for most users): Run on your internet browser

Open the [banana_to_pdf python notebook in Google Colab](https://colab.research.google.com/github/bruno-ritmista/samba/blob/main/banana_to_pdf/deployment/banana_to_pdf.ipynb) then follow the instructions on the screen.


### Option 2 (recommended for advanced users): Run as script on your computer

Clone the [repository](https://github.com/bruno-ritmista/samba) and navigate to it:

```bash
git clone https://github.com/bruno-ritmista/samba.git
cd samba
```

**Option 2.1 — Run directly from the repository root (no install required):**

```bash
pip install -r banana_to_pdf/requirements.txt
python banana_to_pdf <bananadrum_url> [-o out.pdf]
```

**Option 2.2 — Install the package, then run as a module:**

```bash
pip install banana_to_pdf/
python -m banana_to_pdf <bananadrum_url> [-o out.pdf]
```

**Arguments:**
- `<bananadrum_url>` — Shareable BananaDrum URL (from bananadrum.net)
- `-o out.pdf` — Output PDF path (default: derived from the arrangement's title)

**Example:**
```bash
python banana_to_pdf "https://bananadrum.net/?t=Levada&a2=4-4.120.4.1-4.16.1..." -o levada.pdf
```

The script prints the saved PDF path to stdout.

## Prerequisites

**Option 1 (recommended for most users): Run on your internet browser:**
- A Google account.
- A modern browser (Chrome, Firefox, Safari, or Edge).
- A samba arrangement built at [bananadrum.net](https://bananadrum.net), with its shareable link copied.

**Option 2 (recommended for advanced users): Run as script on your computer:**
- Python ≥3.11
- git
- pip
- A samba arrangement built at [bananadrum.net](https://bananadrum.net), with its shareable link copied.

## Reported bugs

The reported bugs for banana_to_pdf can be found [here](https://github.com/bruno-ritmista/samba/issues?q=is%3Aissue%20state%3Aopen%20project%3Abruno-ritmista%2F4%20label%3Abug). 


## Requested features

The requested features for banana_to_pdf can be found [here](https://github.com/bruno-ritmista/samba/issues?q=is%3Aissue%20state%3Aopen%20project%3Abruno-ritmista%2F4%20label%3Afeature). 