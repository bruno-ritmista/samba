# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A collection of Python tools for working with samba percussion notation. The first completed tool is **sheets_to_banana**: converts a Google Sheets percussion grid into a shareable [BananaDrum](https://bananadrum.net) URL.

Planned tools (branches exist but not yet implemented): `sheets_to_score`, `banana_to_sheet`.

## Commands

Run from the `sheets_to_banana/` directory:

```bash
# Install dev dependencies
pip install -r doc/requirements-dev.txt   # adds pytest

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_parse.py -v

# Run a single test by name
pytest tests/test_parse.py::test_name -v

# Install the package locally
pip install .

# Run the tool (no install needed)
pip install -r requirements.txt
python sheets_to_banana <sheets_url> [--break BREAK] [--tempo TEMPO]
```

CI runs on Python 3.13/Ubuntu via two workflows: `validate_usage_instructions.yml` (checks direct-run and pip-install modes) and `test_suite.yml` (runs pytest after validation passes).

## Architecture: sheets_to_banana

The pipeline runs left-to-right through these modules inside `sheets_to_banana/src/`:

```
Google Sheets URL
  → fetch.py      fetch_csv()         downloads CSV from public Google Sheet
  → parse.py      parse_sheet()       parses CSV into Break objects, stitches Z-pattern layout
  → keywords.py   expand_keywords()   replaces shorthand (levada, virada) with note sequences
  → mapping.py    map_break()         translates instrument names and note chars to BananaDrum IDs
  → encode.py     encode_url()        base-64 encodes tracks into the BananaDrum query string
```

**Key domain concepts:**

- **Break** — a rhythmic section (e.g., chorus). Each has multiple instrument tracks.
- **Z-pattern layout** — the sheet repeats its 64 columns for each group of 4 bars; `parse.py` stitches those groups into one flat note sequence per instrument.
- **Polyrhythm (6/8)** — a merged cell spanning one full bar (16 columns); `parse.py` detects these and `encode.py` encodes them as 3-note triplets.
- **Keywords** — shorthand strings (e.g., `levada`) expand to per-instrument note sequences defined in `keywords.py`.
- **BananaDrum IDs** — each instrument has a numeric ID ('0'–'9') and each note hit-style has its own ID. The mapping is hardcoded in `mapping.py`. Surdo is a special case: a single CSV column splits into two BananaDrum tracks (Low='9', Mid='8').

**URL format produced:**

```
https://bananadrum.net/?a2=4-4.{tempo}.{n_bars}.1-4.16.{track1}.{track2}...
```

Each track is a base-N integer (N = number of hit styles + 1) encoded in custom base-64 (`0-9a-zA-Z~_`), implemented in `encode.py`.

## Key Files

| File | Role |
|---|---|
| `src/__main__.py` | CLI entry point; argument parsing; orchestrates pipeline |
| `src/fetch.py` | Google Sheets CSV download; URL extraction and construction |
| `src/parse.py` | CSV → `Break` / `PolyGroup` objects; Z-pattern stitching |
| `src/keywords.py` | Keyword lookup table and expansion logic |
| `src/mapping.py` | Instrument/note → BananaDrum ID translation |
| `src/encode.py` | Base-64 encoding; polyrhythm encoding; full URL assembly |
| `doc/design-plan.md` | 8 completed increments; explains the motivation behind each piece |
| `deployment/sheets_to_banana.ipynb` | Google Colab notebook for end users |

## Workflow: Issues and New Features

When asked to work on a GitHub issue or implement a new feature, always use a dedicated git worktree and branch — never work directly on `main`.

**Steps to follow before writing any code:**

1. **Check if the issue has a pre-defined branch.** Run `gh issue view <number>` and look for a linked branch, or check `git branch -r` for a matching remote branch (e.g. `bugfix/issue-<number>-*` or similar).
2. **If a branch already exists**, check it out into a new worktree:
   ```bash
   git worktree add ../worktrees/<branch-name> <branch-name>
   ```
3. **If no branch exists**, propose a branch name following the convention `<type>/<short-description>` (e.g. `feature/add-virada-keyword`, `bugfix/fix-levada-overflow`) and confirm with the user before creating it:
   ```bash
   git worktree add -b <branch-name> ../worktrees/<branch-name> main
   ```
4. Work exclusively inside the worktree directory for all edits and tests.
5. When done, remind the user to create a PR from the branch and clean up the worktree with `git worktree remove`.

**Never skip this** — even for small changes. Parallel branches require worktrees to avoid checkout conflicts.

## Domain Skills

Two Claude skills in `.claude/.skills/` capture domain knowledge not derivable from the code:

- `understand-bananadrum/` — BananaDrum web app URL schema and architecture
- `understand-sapu-music-notes/` — samba music theory and notation conventions
