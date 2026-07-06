# FAQ

## Prerequisites

See [README](README.md)

## Getting a BananaDrum link

Build your samba arrangement at [bananadrum.net](https://bananadrum.net), then use its share/copy-link feature to get the URL to paste into banana_to_pdf.

## Common errors and what they mean

**"Could not read that link. Please check it was copied from bananadrum.net and try again."**
The pasted text isn't a BananaDrum URL, or is missing/malformed the parts banana_to_pdf needs. Copy the full link from bananadrum.net's share feature and try again.

**"No recognised instruments with notes were found in that link."**
The BananaDrum URL is correct, but every instrument was was empty after unrecognised instruments/notes were skipped. Add some notes in BananaDrum and generate the URL again.

**"Instrument '...' has a polyrhythm section; those notes will be skipped."**
6/8 polyrhythm sections aren't supported yet (see Known limitations) — the rest of that instrument's notes still render normally.

## Known limitations

- banana_to_pdf uses Google Colab to run in your internet browser. As Colab is intended to run on desktops, there may be some limitations when running it on mobile devices.
- A live internet connection is required.
- 6/8 polyrhythm sections are not rendered — notes in those sections are skipped with a warning.
- The `branch_name` field in the notebook is for testing only — leave it blank for normal use.

## Still stuck?

If you still have a question, try reaching out to the person who shared banana_to_pdf with you.
If you want to report a bug or request a feature and you have a GitHub account, please do so [here](https://github.com/bruno-ritmista/samba/issues).
