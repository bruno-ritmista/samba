# Banana-to-PDF Deployment Plan

## Goal
Enable non-technical users (zero software development knowledge) to convert a BananaDrum shareable link into a printable PDF via a simple workflow.

## User Profile
Users who can open a web link and operate a simple website, but don't use computers regularly in daily jobs. **Desktop browsers only** (see Mobile Support below).

## Constraints
- Free hosting, minimal setup and maintenance
- Zero user onboarding
- Notebook source hosted on GitHub; all users open the same notebook, each in their own Colab session
- Output: downloadable PDF file
- Error handling: Show user-friendly messages; don't generate a PDF if an error occurs

---

## System Architecture

### User Flow
1. User builds a samba arrangement at [bananadrum.net](https://bananadrum.net) and copies its shareable link
2. User opens the [banana_to_pdf notebook](../deployment/banana_to_pdf.ipynb) on Colab
3. User pastes the BananaDrum link into the `bananadrum_url` field
4. Notebook decodes the link, maps instruments/notes, and renders an A4 PDF grid
5. Notebook triggers a browser download of the PDF
6. If an error occurs, notebook shows a user-friendly message (no PDF generated)

### Technology Stack
- **Notebook hosting:** GitHub (same repo as banana_to_pdf module); opened via Colab link
- **Source code:** GitHub (banana_to_pdf Python module + notebook)
- **Authentication:** None required — decoding works entirely from the URL's query string
- **Deployment frequency:** Manual — notebook installs from the `main` branch by default (see Version Pinning)

---

## Mobile Support
**This deployment is desktop-only and is not mobile-friendly.** Google Colab's interface is not suited to mobile browsers for non-technical users. Supporting mobile would require a significant redesign of the notebook interface and is deferred to a future iteration.

---

## Session Persistence
To minimise how often users are interrupted by Colab session timeouts, the notebook runs a background daemon thread on startup that prevents the Python kernel from being killed due to inactivity (same pattern as `sheets_to_banana`'s notebook). This extends the kernel's active window up to Colab's free tier maximum (~12 hours). It does not bypass Colab's hard session limits.

---

## Version Pinning
The notebook installs the banana_to_pdf Python module from GitHub via `uv pip install`, from a branch (`main` by default). The `branch_name` field lets a tester point the notebook at an in-progress branch instead — normal users leave it blank. UV is used instead of pip for significantly faster installs, reducing the time users wait on the setup cell.

---

## Known Risks & Accepted Limitations

| Risk | Status |
|---|---|
| Colab outages or free tier quota exceeded | **Accepted.** If Colab hits quota, the notebook opens but cells fail to run. No fallback or status page planned at this stage. |
| Session timeout after ~12 hours | **Accepted.** Users authenticate once per session. Session keep-alive reduces frequency of kernel restarts within the 12-hour window. |
| Mobile users cannot use the notebook effectively | **Accepted.** Desktop-only. Documented explicitly. |
| 6/8 polyrhythm sections are skipped, not rendered | **Accepted.** Out of scope for this iteration (see `doc/design-plan.md`). Affected instruments still render their non-polyrhythm notes, with a warning. |

---

## Out of Scope (Future Iterations)
- Mobile-friendly interface (requires notebook redesign)
- Polyrhythm (6/8) rendering
- Fallback hosting if Colab is unavailable
- Usage logging/monitoring
