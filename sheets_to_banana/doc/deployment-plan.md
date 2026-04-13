# Sheets-to-Banana Deployment Plan

## Goal
Enable non-technical users (zero software development knowledge) to convert Google Sheets notes to BananaDrum URLs by clicking a single link.

## User Profile
Users who can open a web link and operate a simple website, but don't use computers regularly in daily jobs. **Desktop browsers only** (see Mobile Support below).

## Constraints
- Free hosting, minimal setup and maintenance
- Zero user onboarding
- Max ~100 requests/day (rough capacity guideline, not a hard limit — see Monitoring)
- All users share the same notebook (no forking)
- Output: Web URL to BananaDrum
- Error handling: Show user-friendly messages; don't create link if error occurs

---

## System Architecture

### User Flow
1. User has access to a Google Sheets file (shared with them by the sheet owner)
2. Sheet contains a formula-generated hyperlink pointing to a Colab notebook
3. Sheet displays the `sheets_id` value visually **below the link**, with clear instructions to copy it
4. User clicks the link → Colab notebook opens in new tab
5. User copies the `sheets_id` from the Google Sheet and pastes it into the input cell at the top of the notebook
6. Notebook prompts for OAuth permission (once per Colab session)
7. Notebook reads the user's Google Sheet using the pasted `sheets_id`
8. Notebook extracts notes from the sheet
9. User optionally modifies `break` and `tempo` parameters (have defaults)
10. Notebook calls the sheets-to-banana Python module with extracted data
11. Notebook displays generated BananaDrum URL
12. If error occurs, notebook shows user-friendly error message (no URL created)

### Technology Stack
- **Notebook hosting:** Google Colab (free)
- **Source code:** GitHub (sheets-to-banana Python module + notebook)
- **Authentication:** Google OAuth (users grant permission to read their Sheets)
- **Logging:** Google Cloud Logging via a dedicated service account (see Logging)
- **Deployment frequency:** Manual — notebook import pinned to a specific commit hash (see Version Pinning)

---

## Mobile Support
**This deployment is desktop-only and is not mobile-friendly.** Google Colab's interface is not suited to mobile browsers for non-technical users. Supporting mobile would require a significant redesign of the notebook interface and is deferred to a future iteration.

---

## Increment 1: Create Python Notebook to Call sheets-to-banana

### Intended Behavior
The Colab notebook is a self-contained application that:

**Reads sheet ID from user input:**
- The notebook contains a clearly labelled input cell at the very top
- The Google Sheet displays the `sheets_id` value below the Colab link with instructions: _"Copy the ID below and paste it into the first cell of the notebook"_
- The `sheets_id` is the alphanumeric identifier only (not the full URL), extracted from the sheet's own URL via a formula in the template sheet

**Authenticates to Google Sheets:**
- Uses `google.colab.auth.authenticate_user()` to prompt the user for OAuth consent
- Authentication persists for the duration of the Colab session
- Users see: _"This app wants permission to see your Google Sheets"_ consent popup once per session
- The notebook keeps the Colab session alive via a periodic background ping (see Session Persistence below)

**Reads the user's Google Sheet:**
- Uses the pasted `sheets_id` to identify which Sheet to read
- Extracts notes/data from the sheet
- Supports sheets owned by the user as well as sheets shared to the user by others (OAuth authenticates as the user, so all sheets that user can access are readable)

**Provides editable parameters:**
- Displays cells with default values for `break` and `tempo`
- Users can manually edit these before execution
- Sensible defaults allow non-technical users to just run as-is

**Calls sheets-to-banana:**
- Imports the sheets-to-banana Python module from GitHub, pinned to a specific commit hash (see Version Pinning)
- Calls it with: Google Sheet data + `break` + `tempo` parameters
- Returns: BananaDrum URL

**Displays output:**
- Shows the generated BananaDrum URL prominently
- Users can copy/click the URL

**Error handling:**
- Catches exceptions from sheets-to-banana or Google Sheets API
- Displays user-friendly error messages only (no Python tracebacks)
- Example: _"Could not read your Google Sheet. Please check the sheet ID and try again."_
- Does NOT generate a BananaDrum URL if an error occurs

---

## Session Persistence
To minimise how often users are prompted for OAuth re-authentication, the notebook includes an embedded background task that periodically pings the Colab runtime to keep the session alive for as long as possible (up to Colab's free tier maximum of ~12 hours). This logic is part of the notebook itself and does not depend on any external script.

---

## Version Pinning
The notebook imports the sheets-to-banana Python module from GitHub pinned to a **specific commit hash**, not `main`:

```
pip install git+https://github.com/bruno-ritmista/samba@<COMMIT_HASH>#egg=sheets-to-banana
```

This ensures no changes reach users unintentionally.

**Future improvement:** Set up GitHub Actions to run automated tests on the Python module. Based on passing tests, the commit hash in the notebook is manually updated to the validated commit. This creates a controlled release pipeline before expanding to automated deployment.

---

## Logging
All notebook executions are logged to a Google Cloud destination accessible only to the script author.

**What is logged:** timestamp, user email (from OAuth), sheet ID processed.

**Implementation:**
- A dedicated Google Cloud service account is created with minimal permissions (write-only access to the logging destination)
- The service account JSON key is stored in Colab Secrets (not in the notebook code or GitHub repo)
- The notebook retrieves the key from Colab Secrets at runtime and authenticates as the service account to write log entries
- Users cannot see or access these logs — the service account is isolated from the user's own Google account

**Purpose:** Monitor usage trends and detect if traffic approaches or exceeds capacity expectations. The ~100 requests/day figure is a rough architectural guideline, not a hard-enforced limit. If logs show sustained growth beyond this, the architecture will be revisited.

---

## Known Risks & Accepted Limitations

| Risk | Status |
|---|---|
| Colab outages or free tier quota exceeded | **Accepted.** If Colab hits quota, the notebook opens but cells fail to run. No fallback or status page planned at this stage. |
| Google Sheets API quota limits | **Accepted.** Monitored via GCP console. Not enforced at application level. Will be addressed if logs show traffic approaching limits. |
| OAuth re-authentication on new sessions | **Accepted.** Users authenticate once per session. Session keep-alive reduces frequency. |
| Mobile users cannot use the notebook effectively | **Accepted.** Desktop-only. Documented explicitly. |

---

## Out of Scope (Future Iterations)
- Mobile-friendly interface (requires notebook redesign)
- Automated commit hash updates via GitHub Actions CI/CD
- Hard rate limiting enforcement
- Fallback hosting if Colab is unavailable