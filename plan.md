# sheets_to_pdf — Design Plan

Reads percussion notes from a Google Sheet in a custom
table-based format, converts them to ABC notation, renders
a traditional percussion music score, and writes the outputs
back to the same Google Sheet and its Drive folder.

## Overview

Each Google Sheet containing percussion notes gets:
- An Apps Script menu with two render triggers
- An `[abc]` tab storing the intermediate ABC notation text
- A `[scores]` tab storing the rendered score as an image
- A PDF saved to the same Drive folder as the Sheet

A single shared Colab notebook (opened via a link in the
Sheet) runs the pipeline. It authenticates as the logged-in
Google user — no credentials or secrets required anywhere.
All pipeline source code lives in this GitHub repo and is
cloned at runtime by the notebook.

## Architecture

```
Google Sheet
├── Notes tab(s)         ← source: table-based percussion notes
├── [abc] tab            ← intermediate: ABC notation text + metadata
│   ├── A1: Sheet ID     ← written by Apps Script before opening Colab
│   ├── B1: trigger mode ← "full" or "render_only"
│   └── A2: ABC content  ← generated or manually edited
└── [scores] tab         ← output: rendered score PNG

Google Drive (same folder as Sheet)
└── <sheet_title>.pdf    ← output: printable score

GitHub (this repo)
├── sheets_to_pdf/
│   ├── fetch.py
│   ├── parse.py
│   ├── mapping.py
│   ├── to_abc.py
│   ├── render.py
│   ├── upload.py
│   └── notebook.ipynb   ← orchestration only
```

## Trigger flow

1. User clicks "Render: Convert notes → ABC + Render" or
   "Render: Re-render ABC" from the Apps Script menu in the Sheet
2. Apps Script writes the Sheet ID and trigger mode to `[abc]!A1:B1`
3. Apps Script opens the Colab notebook URL in a new tab
4. User clicks "Run All" in Colab
5. Colab authenticates as the logged-in Google user
6. Colab reads Sheet ID and mode from `[abc]!A1:B1`
7. Pipeline runs according to mode (see below)
8. Outputs written back to Sheet and Drive

## Two trigger modes

### "full" — Convert notes → ABC + Render
Runs the entire pipeline:
fetch → parse → map → generate ABC → write to [abc] tab
→ render → upload PDF to Drive → write PNG to [scores] tab

### "render_only" — Re-render manually edited ABC  
Skips fetch/parse/generate. Reads ABC content from `[abc]!A2`,
renders it, and updates the PDF and [scores] tab.
Use this after manually tweaking the ABC notation.

## ABC notation storage

The entire ABC content for all breaks in the Sheet is stored
as a single string in cell `[abc]!A2`. ABC notation is plain
text (ASCII), human-readable, and manually editable.

The `[abc]` tab has a red background to signal it is
generated content. Users should not edit it directly except
when intentionally tweaking notation before a "render_only"
trigger. The tab may optionally be hidden.

## Rendering parameters

- Layout: continuous flow, all breaks stacked vertically
  with titles, single page
- Page format: screen-optimised (tall custom page, not A4)
- One PNG and one PDF produced per Sheet

These are hardcoded for now and will be revisited during
validation.

## Dependencies (installed at Colab runtime)

- abcm2ps (ABC → PostScript)
- ghostscript / ps2pdf (PostScript → PDF)
- imagemagick (PDF → PNG)
- gspread (Google Sheets API)
- google-auth (Colab user authentication)

---

## Increments

### Increment 1 — Apps Script instrumentation

Add an Apps Script to the Google Sheet that:
- Adds a "Render" menu with two items:
  - "Convert notes → ABC + Render"
  - "Re-render ABC"
- On click: creates `[abc]` and `[scores]` tabs if they
  don't exist, sets `[abc]` tab background to red
- Writes Sheet ID to `[abc]!A1`
- Writes trigger mode ("full" or "render_only") to `[abc]!B1`
- Opens the Colab notebook GitHub URL in a new browser tab

The Apps Script is manually added once to each Sheet that
needs rendering. It is self-contained and does not depend on
any Python code.

### Increment 2 — Colab notebook skeleton

A notebook stored at `sheets_to_pdf/notebook.ipynb` that:
- Clones this GitHub repo
- Installs apt and pip dependencies
- Authenticates the user via `google.colab.auth`
- Mounts Google Drive
- Reads Sheet ID from `[abc]!A1` and mode from `[abc]!B1`
- Routes to full pipeline or render-only based on mode
- Reports success or failure clearly to the user

The notebook contains no source logic — only orchestration
calls to the modules below.

### Increment 3 — fetch.py

Reads all tabs from the Google Sheet identified by the Sheet
ID. Identifies which tabs contain percussion note tables
(heuristic TBD during implementation — likely based on
header row structure). Returns each tab's content as CSV
text.

Reuses or adapts fetch.py from the existing `sheets_to_banana`
branch if applicable.

### Increment 4 — parse.py

Parses CSV content from one or more tabs into a list of
Break objects. Each Break has:
- A title (derived from the sheet tab name or table header)
- A dict mapping instrument name → flat list of note
  characters at 16th-note resolution
- Bar count

Handles the Z-pattern layout (bars 1–4, then 5–8, …),
stitching them into a single flat sequence per instrument.

Reuses or adapts parse.py from `sheets_to_banana` if
applicable.

### Increment 5 — mapping.py

Translates parsed instrument names and note characters into
ABC notation equivalents:
- Assigns each instrument a fixed staff line position
- Assigns each note character a notehead type and ABC pitch
- Handles the Surdo 1a/2a split into two voices
- Maps rests and unknown/skip characters to ABC rests (z)

Instrument-to-staff-position mapping is defined as constants
and will be tuned during validation.

### Increment 6 — to_abc.py

Converts a list of Break objects (post-mapping) into a single
ABC notation string containing all breaks sequentially, each
with its own X: index and T: title. Writes the resulting
string to `[abc]!A2` via the Sheets API.

ABC structure per break:
- One V: voice per instrument, clef=perc
- %%score groups all voices with bar lines joined
- Instrument names shown via name= in V: header
- 16th notes, M:4/4, tempo TBD

Page/layout directives (%%pagewidth, %%staffsep, %%scale)
are hardcoded for screen-optimised single-page output.

### Increment 7 — render.py

Reads ABC content from `[abc]!A2` and runs the local
rendering pipeline:

```
abcm2ps input.abc -O output.ps
ps2pdf output.ps output.pdf
convert -density 150 output.pdf output.png
```

Produces two output files:
- `<sheet_title>.pdf`
- `<sheet_title>.png`

All intermediate files are written to the Colab session's
temp directory.

### Increment 8 — upload.py

- Uploads `<sheet_title>.pdf` to the same Google Drive folder
  that contains the source Sheet (folder resolved via Drive
  API from the Sheet ID), overwriting any previous version
- Writes `<sheet_title>.png` as an image anchored to cell A1
  of the `[scores]` tab, replacing any existing image
