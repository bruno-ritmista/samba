# Implementation Plan — Notebook installs from its own branch (issue #9)

Status: **approved, not yet implemented.** This document is a self-contained handover
for a fresh session. Read it top-to-bottom, then apply "The change" section.

## Problem (issue #9)

`sheets_to_banana/deployment/sheets_to_banana.ipynb` is a Colab notebook whose single
code cell installs the package with a **hardcoded git ref**:

```python
_branch = "bugfix/install_sheets_to_banana_from_notebook_branch"
# ...
"git+https://github.com/bruno-ritmista/samba.git@{_branch}#subdirectory=sheets_to_banana"
```

Opening the notebook from any other branch's Colab URL still installs from whatever branch
is hardcoded — so in-progress fixes cannot be tested end-to-end via Colab before merging.
The current stopgap is to hand-edit `_branch` per branch and keep it in sync manually
(see the existing comment in the cell). Two prior attempts to auto-detect the branch at
runtime (reading `document.location.href` via `eval_js` in Colab) were **reverted as
unreliable** — do not resurrect them.

## Decision (why this is the chosen design)

Interviewed the owner. Design choices were evaluated and rejected in this order; recorded
so the next session doesn't re-litigate them:

- **Runtime auto-detection** (read the branch from the Colab URL): rejected — twice-tried,
  twice-failed/reverted. This is the *only* fully-automatic-and-clean option, and it doesn't work.
- **Two notebooks** (a `main` one merged to main + a per-branch dev one): rejected. Anything
  branch-specific that is committed (so it's Colab-openable at a branch URL) must then be
  policed off `main`. `.gitattributes merge=ours` does **not** solve this: GitHub's
  "Merge pull request" button merges server-side and never invokes a local merge driver, so
  a PR merge would still carry the branch's notebook onto `main`. That pushes toward a CI
  self-heal job — more machinery than the problem is worth.
- **Live "all branches" dropdown** (`ipywidgets.Dropdown` populated from the GitHub API):
  rejected on UX. Colab's native form (`#@param`) dropdowns are static hardcoded lists, so a
  *live* dropdown must be an `ipywidgets` widget, which renders as cell **output below** the
  form — it cannot live inside Colab's tidy form panel. Owner did not want that.

**Chosen: a single `#@param` text field in the existing form cell.** The developer types the
branch name; empty means `main`. This is the laziest option that meets every constraint:
- No second notebook, no git hook, no CI, no `.gitattributes`, no drift.
- The committed notebook value is **always empty → `main`**, so it merges to `main`
  trivially and `main` is clean *by construction* — there is nothing to keep off `main`.
- Normal users' experience is unchanged (field left empty → installs `main`).
- Accepted cost: a developer re-types the branch name once per Colab session. Owner
  confirmed developer effort is acceptable; this is strictly less effort than the
  stamp-script/commit/push alternatives.

## The change (single file, two edits)

File: `sheets_to_banana/deployment/sheets_to_banana.ipynb`, the one form code cell
(cell id `generate`, `metadata.cellView == "form"`, source is a **single JSON string**,
not a list of lines — keep that shape).

### Edit 1 — add a form field next to the other params

The cell already has, near the top:

```python
sheets_link = "" #@param {type:"string", placeholder:"Paste the Google Sheets link here"}
break_number = "" #@param {type:"string", placeholder:"Leave empty for all breaks, or enter a number (e.g. 1)"}
tempo = "110" #@param {type:"string", placeholder:"e.g. 110"}
```

Add one line immediately after `tempo`:

```python
install_branch = "" #@param {type:"string", placeholder:"Advanced: leave empty to install from main"}
```

### Edit 2 — derive `_branch` from the field, drop the hardcode

Inside the `if importlib.util.find_spec("sheets_to_banana") is None:` block, replace the
stale comment + hardcoded assignment:

```python
    # Branch to install sheets_to_banana from. There is no automatic way to detect
    # which branch this notebook is running from (see issue #9), so this must be
    # kept in sync by hand: set it to this branch's name when copying the notebook
    # to a new branch, and update it again if the branch is renamed or merged.
    _branch = "bugfix/install_sheets_to_banana_from_notebook_branch"
```

with:

```python
    # Branch to install sheets_to_banana from. Normal users leave install_branch
    # empty and get "main". To test in-progress work, open this notebook from a
    # branch's Colab URL and type that branch's name into the install_branch field.
    _branch = install_branch.strip() or "main"
```

Everything downstream is unchanged — `_branch` still feeds the existing
`f"git+https://github.com/bruno-ritmista/samba.git@{_branch}#subdirectory=sheets_to_banana"`
install line, which already handles branch names containing `/` (the current hardcoded
value has one).

## How to apply the edits (mechanics)

The cell `source` is a single JSON-escaped string, so a naive text editor match is fiddly
(`"` is stored as `\"`, newlines as `\n`). Use this exact-substring replace script; it
avoids reserializing the whole file (keeps the diff minimal) and asserts each match is unique:

```python
import json
p = "sheets_to_banana/deployment/sheets_to_banana.ipynb"
s = open(p, encoding="utf-8").read()
def esc(x): return json.dumps(x)[1:-1]   # produce the file's JSON-escaped form

old1 = esc('tempo = "110" #@param {type:"string", placeholder:"e.g. 110"}\n\nimport importlib')
new1 = esc('tempo = "110" #@param {type:"string", placeholder:"e.g. 110"}\n'
           'install_branch = "" #@param {type:"string", placeholder:"Advanced: leave empty to install from main"}\n\nimport importlib')
assert s.count(old1) == 1, s.count(old1)
s = s.replace(old1, new1)

old2 = esc('''    # Branch to install sheets_to_banana from. There is no automatic way to detect
    # which branch this notebook is running from (see issue #9), so this must be
    # kept in sync by hand: set it to this branch's name when copying the notebook
    # to a new branch, and update it again if the branch is renamed or merged.
    _branch = "bugfix/install_sheets_to_banana_from_notebook_branch"''')
new2 = esc('''    # Branch to install sheets_to_banana from. Normal users leave install_branch
    # empty and get "main". To test in-progress work, open this notebook from a
    # branch's Colab URL and type that branch's name into the install_branch field.
    _branch = install_branch.strip() or "main"''')
assert s.count(old2) == 1, s.count(old2)
s = s.replace(old2, new2)

open(p, "w", encoding="utf-8", newline="").write(s)
print("edited OK")
```

`newline=""` prevents Windows from rewriting `\n` line endings to `\r\n`.

## Verification

1. **Valid notebook:** `python -c "import json; json.load(open('sheets_to_banana/deployment/sheets_to_banana.ipynb', encoding='utf-8'))"` (or `nbformat.read(..., 4)`).
2. **Minimal diff:** `git diff` should touch only the two spots above — the new `install_branch`
   param line and the comment + `_branch` assignment. Nothing else.
3. **Default resolves to main:** confirm `_branch = install_branch.strip() or "main"` yields
   `"main"` when the field is empty and the typed name otherwise
   (`""` → `main`; `" feature/x "` → `feature/x`).
4. **Manual Colab smoke test (optional, do after merge or on the branch):**
   - Open `.../blob/<this-branch>/sheets_to_banana/deployment/sheets_to_banana.ipynb` in Colab,
     type `<this-branch>` into `install_branch`, run → installs from that branch.
   - Leave it empty → installs from `main`.

## Out of scope / explicitly NOT doing

- No git `post-checkout` hook, no stamp script.
- No CI workflow changes, no `.gitattributes`, no merge driver.
- No second/dev notebook, no generation of one notebook from another.
- No runtime branch auto-detection (`eval_js`/`document.location.href`).
- README needs no change: it links the `main` notebook, whose behavior is unchanged.

## Closing the issue

The change resolves issue #9 (any branch is now testable via Colab by typing its name).
Reference the issue in the commit; the branch `bugfix/install_sheets_to_banana_from_notebook_branch`
already tracks this work.
