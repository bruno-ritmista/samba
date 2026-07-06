# Sheet-to-Banana Deployment Plan

## Goal
Enable non-technical users (zero software development knowledge) to convert Google Sheets notes to BananaDrum URLs via a simple workflow accessible from a link in the Google Sheet.

## User Profile
Users who can open a web link and operate a simple website, but don't use computers regularly in daily jobs. **Desktop browsers only** (see Mobile Support below).

## Constraints
- Free hosting, minimal setup and maintenance
- Zero user onboarding
- Max ~100 requests/day (rough capacity guideline, not a hard limit — see Monitoring)
- Notebook source hosted on GitHub; all users open the same notebook, each in their own Colab session
- Output: Web URL to BananaDrum
- Error handling: Show user-friendly messages; don't create link if error occurs

---

## System Architecture

### User Flow
1. User has access to a Google Sheets file (shared with them by the sheet owner)
2. Sheet contains a formula-generated hyperlink pointing to the Colab notebook on GitHub
3. Sheet displays the `sheets_url` value visually **below the link**, with clear instructions to copy it
4. User clicks the link → Colab notebook opens in new tab
5. User copies the `sheets_url` from the Google Sheet and pastes it into the input cell at the top of the notebook
6. Notebook validates the pasted value and extracts the sheet ID (accepts full URL or bare ID)
7. Notebook reads the user's Google Sheet using the public CSV export URL (no authentication required — sheet must be shared with "anyone with link can view")
8. Notebook extracts notes from the sheet
9. User optionally modifies `break` and `tempo` parameters (have defaults)
10. Notebook calls the sheet-to-banana Python module with extracted data
11. Notebook displays generated BananaDrum URL
12. If error occurs, notebook shows user-friendly error message (no URL created)

### Technology Stack
- **Notebook hosting:** GitHub (same repo as sheet-to-banana module); opened via Colab link
- **Source code:** GitHub (sheet-to-banana Python module + notebook)
- **Authentication:** None required for sheet reading (public CSV export URL)
- **Logging:** Deferred to a future increment (see Increment: Logging)
- **Deployment frequency:** Manual — notebook import pinned to a specific commit hash (see Version Pinning)

---

## Mobile Support
**This deployment is desktop-only and is not mobile-friendly.** Google Colab's interface is not suited to mobile browsers for non-technical users. Supporting mobile would require a significant redesign of the notebook interface and is deferred to a future iteration.

---

## ✅ Increment 1: Create Python Notebook to Call sheet-to-banana

### Intended Behavior
The Colab notebook is a self-contained application that:

**Reads sheet URL from user input:**
- The notebook contains a clearly labelled input cell at the very top
- The Google Sheet displays the sheet URL below the Colab link with instructions: _"Copy the link below and paste it into the first cell of the notebook"_
- The notebook accepts either a full Google Sheets URL or a bare sheet ID

**Validates and normalises input:**
- Accepts a full Google Sheets URL (`https://docs.google.com/spreadsheets/d/<ID>/...`) or a bare sheet ID
- Extracts the sheet ID from the URL using a regex match on `spreadsheets/d/([a-zA-Z0-9_-]+)`
- Strips leading/trailing whitespace
- Shows a user-friendly error if the input matches neither pattern (e.g. _"That doesn't look like a Google Sheets link. Please copy the link from the sheet and try again."_)
- Does not proceed to fetch if validation fails

**Reads the user's Google Sheet:**
- Uses the extracted sheet ID to construct a public CSV export URL
- No API key or OAuth required — sheet must be accessible to "anyone with link can view"
- Calls the existing `fetch.py` module directly

**Provides editable parameters:**
- Displays cells with default values for `break` and `tempo`
- Users can manually edit these before execution
- Sensible defaults allow non-technical users to just run as-is

**Calls sheet-to-banana:**
- Imports the sheet-to-banana Python module from GitHub, pinned to a specific commit hash (see Version Pinning)
- Calls it with: Google Sheet data + `break` + `tempo` parameters
- Returns: BananaDrum URL

**Displays output:**
- Shows the generated BananaDrum URL prominently
- Users can copy/click the URL

**Error handling:**
- Catches exceptions from sheet-to-banana or the CSV fetch
- Displays user-friendly error messages only (no Python tracebacks)
- Example: _"Could not read your Google Sheet. Please check the link and try again."_
- Does NOT generate a BananaDrum URL if an error occurs

---

## Session Persistence
To minimise how often users are interrupted by Colab session timeouts, the notebook runs a background daemon thread on startup that prevents the Python kernel from being killed due to inactivity:

```python
import threading, time

def _keep_alive():
    while True:
        time.sleep(60)

_t = threading.Thread(target=_keep_alive, daemon=True)
_t.start()
```

This extends the kernel's active window up to Colab's free tier maximum (~12 hours). It does not bypass Colab's hard session limits. This logic is part of the notebook itself and does not depend on any external script.

---

## Version Pinning
The notebook installs the sheet-to-banana Python module from GitHub pinned to a **specific commit hash**, not `main`:

```python
import subprocess
subprocess.run(["pip", "install", "uv", "-q"], check=True)
subprocess.run(
    ["uv", "pip", "install", "--system", "-q",
     "git+https://github.com/bruno-ritmista/samba@<COMMIT_HASH>#egg=sheet-to-banana"],
    check=True
)
```

UV is used instead of pip for significantly faster installs (typically 3–10x), reducing the time users wait on the setup cell.

This ensures no changes reach users unintentionally.

---

## ⌛ Increment 2: Automated Deployment Validation and Notebook Update Process

When the Python module is updated and a new commit is ready for release:

1. **CI validation:** GitHub Actions runs the existing test suite (`pytest`) against the new commit on push to `main`
2. **Manual release step:** On passing tests, the deployer updates the commit hash in the notebook file on GitHub and pushes the change
3. **Verification:** All users who open the Colab link after the push automatically receive the new version (Colab fetches the notebook from GitHub at open time)

This creates a controlled release pipeline. Notebook updates are a deliberate manual step — not automated pushes — giving the deployer a final review gate before users are affected.

**Future improvement:** Automate the hash update step via a GitHub Actions workflow that updates the notebook file and opens a PR for review, triggered by passing CI on `main`.

---

## ⌛ Increment 3: Logging

All notebook executions are logged to a Google Cloud destination accessible only to the script author.

**What is logged:** timestamp, sheet ID processed.

**Privacy note:** If user email is logged in future, a visible disclosure must be added to the notebook (GDPR/LGPD requirement). At minimum, the notebook should state what data is collected.

**Implementation:**
- A dedicated Google Cloud service account is created with minimal permissions (write-only access to the logging destination)
- The service account credentials are embedded in the notebook in a write-only, narrowly scoped form (Colab Secrets are per-user and cannot be accessed from other users' sessions — a different approach is required, e.g. a backend proxy or a write-only embedded token)
- Users cannot access or modify these logs

**Purpose:** Monitor usage trends and detect if traffic approaches or exceeds capacity expectations. The ~100 requests/day figure is a rough architectural guideline, not a hard-enforced limit. If logs show sustained growth beyond this, the architecture will be revisited.

---

## Known Risks & Accepted Limitations

| Risk | Status |
|---|---|
| Colab outages or free tier quota exceeded | **Accepted.** If Colab hits quota, the notebook opens but cells fail to run. No fallback or status page planned at this stage. |
| Google Sheets CSV export unavailable | **Accepted.** Monitored indirectly via error reports. If the public CSV export URL changes behaviour, `fetch.py` will need updating. |
| Session timeout after ~12 hours | **Accepted.** Users authenticate once per session. Session keep-alive reduces frequency of kernel restarts within the 12-hour window. |
| Mobile users cannot use the notebook effectively | **Accepted.** Desktop-only. Documented explicitly. |

---

## Out of Scope (Future Iterations)
- Mobile-friendly interface (requires notebook redesign)
- Hard rate limiting enforcement
- Fallback hosting if Colab is unavailable
- Automated commit hash updates via GitHub Actions CI/CD (currently a manual step after CI passes)
