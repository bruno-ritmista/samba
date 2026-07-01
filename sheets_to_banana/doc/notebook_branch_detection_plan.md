# Implementation Plan — Notebook installs from its own branch (issue #9)

Status: **implemented.** See "Status update" near the end for what was done, two bugs found
along the way (one fixed, one still open), and follow-ups.

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

## Status update

- **Done**: Edit 1 (`install_branch` param) and Edit 2
  (`_branch = install_branch.strip() or "main"`) applied to the `generate` cell as specified
  above.
- **New finding #1 (found and fixed)**: Colab's `#@param` options parser bare-quotes any
  `word:` pattern via a naive regex that doesn't respect string boundaries. The original
  placeholder text `"Advanced: leave empty to install from main"` has a colon *inside* the
  string, which corrupted the options JSON and broke the field's type detection. Symptom: Colab
  showed the error `Fehler beim Parsen des ungültigen JSON-Formats`, and once the field failed to
  parse as `type:"string"`, running the cell substituted the typed value into the source
  **unquoted** (`install_branch = bugfix/... #@param ...`), raising `NameError`. Fixed by
  rewording the placeholder to `"Advanced - leave empty to install from main"`. **Lesson for
  future edits to this cell: never put a colon inside a `#@param` option string value** — none
  of the other three params' placeholders have one, which is why only this field broke.
- **New finding #2 (found and fixed)**: the install block was gated by
  `if importlib.util.find_spec("sheets_to_banana") is None:` — "only install if not present at
  all." This has no memory of *which branch* is installed: once any branch is installed, every
  later auto-rerun (the form uses `run:"auto"`, which reruns on every field edit) finds the
  package present and skips the whole block, so changing `install_branch` after the first run
  silently did nothing. Fixed by tracking the last-installed branch in a module-level variable
  (`_installed_branch`, a bare assignment at the cell's top level — persists across auto-reruns
  within the same Colab runtime, and disappears exactly when the installed package would too,
  e.g. on a runtime restart) and reinstalling when the package is missing *or* the requested
  branch differs from the tracked one. Also added `--reinstall-package sheets_to_banana` to the
  `uv pip install` call, scoped to just that one package, as a guarantee that the git-ref switch
  actually replaces the installed code regardless of `uv`'s own "already satisfied" heuristics
  for VCS URLs.
- **Open (known limitation, not planned)**: if a developer keeps `install_branch` set to the
  same branch name and pushes new commits to it, this fix does not pick up the new commits — the
  branch *name* didn't change, so the guard still skips the reinstall. A correct fix needs either
  always-reinstalling while a branch is set (costly: every unrelated field edit, e.g. tweaking
  `tempo`, would pay a ~30s reinstall) or a GitHub API commit-SHA check (adds a network
  dependency). Not building either — not reported, and the existing workaround (retype/toggle the
  `install_branch` field to force a value change) is enough.

## Closing the issue

The change resolves issue #9 (any branch is now testable via Colab by typing its name).
Reference the issue in the commit; the branch `bugfix/install_sheets_to_banana_from_notebook_branch`
already tracks this work.
