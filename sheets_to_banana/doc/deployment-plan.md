# Sheets-to-Banana Deployment Plan

**Goal:** Enable non-technical users (zero software development knowledge) to convert Google Sheets notes to BananaDrum URLs by clicking a single link.

**User Profile:** Users who can open a web link and operate a simple website, but don't use computers regularly in daily jobs. Desktop and mobile browsers, most common browsers supported.

**Constraints:**
- Free hosting, minimal setup and maintenance
- Zero user onboarding
- Max 100 requests/day
- All users share the same notebook (no forking)
- Output: Web URL to BananaDrum
- Error handling: Show user-friendly messages; don't create link if error occurs

---

## System Architecture

### User Flow
1. User has access to a Google Sheets file (public or shared with them)
2. Sheet contains a formula-generated hyperlink pointing to a Colab notebook with `sheets_id` parameter
3. User clicks the link \u2192 Colab notebook opens in new tab
4. Notebook prompts for OAuth permission (one-time, persists indefinitely)
5. Notebook reads Google Sheets ID from URL parameter
6. Notebook reads user's Google Sheet to extract notes
7. User optionally modifies "break" and "tempo" parameters (have defaults)
8. Notebook calls sheets-to-banana Python module with extracted data
9. Notebook displays generated BananaDrum URL
10. If error occurs, notebook shows user-friendly error message (no URL created)

### Technology Stack
- **Notebook hosting:** Google Colab (free)
- **Source code:** GitHub (sheets-to-banana Python module + notebook)
- **Authentication:** Google OAuth (users grant permission to read their Sheets)
- **Deployment frequency:** Manual (auto-update from GitHub on each notebook run, potential GitHub Actions trigger later)

---

## Increment 1: Create Python Notebook to Call sheets-to-banana

### Intended Behavior
The Colab notebook is a self-contained application that:

1. **Reads URL parameters:**
   - Extracts `sheets_id` from the URL the notebook was opened with
   - Example: `https://colab.research.google.com/github/bruno-ritmista/samba/blob/sheets_to_banana/sheets_to_banana/notebook/sheets_to_banana.ipynb?sheets_id=ABC123XYZ`

2. **Authenticates to Google Sheets:**
   - Prompts user for OAuth permission on first run
   - Stores authentication token for future runs (persists across sessions)
   - User sees: "This app wants permission to see your Google Sheets" consent popup

3. **Reads the user's Google Sheet:**
   - Uses the `sheets_id` parameter to identify which Sheet to read
   - Extracts notes/data from the Sheet

4. **Provides editable parameters:**
   - Displays cells with default values for `break` and `tempo`
   - Users can manually edit these before execution
   - Sensible defaults allow non-technical users to just run as-is

5. **Calls sheets-to-banana:**
   - Imports the sheets-to-banana Python module (from GitHub)
   - Calls it with: Google Sheet data + break + tempo parameters
   - Returns: BananaDrum URL

6. **Displays output:**
   - Shows the generated BananaDrum URL prominently
   - Users can copy/click the URL

7. **Error handling:**
   - Catches exceptions from sheets-to-banana or Google Sheets API
   - Displays **user-friendly error messages only** (no Python tracebacks)
   - Example: "Could not read your Google Sheet. Please check the sheet ID and try again."
   - Does NOT generate a BananaDrum URL if error occurs

### Gaps & Questions

**CRITICAL BLOCKER:**
- **How does the notebook read URL parameters?** Colab doesn't natively expose URL query parameters to Python. What mechanism will be used?
  - Option A: User manually pastes the sheets_id into a cell (breaks "zero interaction" requirement)
  - Option B: Notebook uses JavaScript to extract from `window.location.href` (complex, browser-dependent)
  - Option C: Use a wrapper (Google Apps Script) that passes data via notebook cell variable (workaround)
  - Option D: Other approach?

**Authentication:**
- **Where is the OAuth token stored?** Colab sessions are ephemeral. Does the token persist via:
  - Colab's built-in authentication (if available)?
  - Google Drive mounted in Colab (user's account)?
  - External service (complicates setup)?
- **What if token expires or is revoked?** Graceful re-auth or error?

**Google Sheets Reading:**
- **Which cell/range contains the notes to convert?** This must be defined/standardized in the Sheet template.
- **What if the Sheet doesn't exist or user lacks permission?** Error message handling.

**sheets-to-banana Import:**
- **How does the notebook import sheets-to-banana from GitHub?**
  - `pip install git+https://github.com/bruno-ritmista/samba@main#egg=sheets-to-banana`?
  - Clone the repo and `import` locally?
  - Copy code inline?
- **What are the dependencies (
