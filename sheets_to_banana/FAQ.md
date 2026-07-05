# FAQ

## Prerequisites

See [README](README.md)

## Getting a sheet in the right format

Copy the [template](https://docs.google.com/spreadsheets/d/1NL_UpLsLf1YSnPphxxP7Mdu-IdTzckSYDjZsCih0LCw/edit?gid=991712970#gid=991712970) into your own Google Drive and enter the notes as described in the sheet "README" don't change the sheet's structure.

## Common errors and what they mean

**"Not a valid Google Sheets URL"**
The link you pasted doesn't look like a Google Sheets link. Copy the full link from your browser's address bar and try again.

**"This sheet doesn't look public..."**
The sheet isn't shared publicly, therefore sheets_to_banana cannot access it. In the Google Sheets file with your notes: File → Share → Share with others → General access: "Anyone with the link".

**"Could not reach Google Sheets — check your internet connection..."**
The request to Google Sheets timed out or failed. Check your internet connection and try again.

**"No breaks found in the sheet."**
The tool couldn't find any recognisable break/section in the sheet. Check that the sheet follows the template's layout.

**"Break N not found."**
The break number you entered is outside the range of breaks in the sheet. Leave the field empty to convert all breaks, or check the sheet for how many breaks it contains.

**"...has no recognised instruments"**
None of the instrument names in that break matched a known instrument. Check the instrument names against the template sheet.

**"Tempo must be a number..."**
The Tempo field must be a plain number (e.g. `120` or `120 bpm`).

## Known limitations

- sheets_to_banana use Google Colab to run in your internet browser. As Colab is intended to run on desktops — there may be some limitations when runnning it on mobile devices.
- A live internet connection is required.
- The `branch_name` field in the notebook is for testing only — leave it blank for normal use.

## Still stuck?

If you still have a question, try reaching out to the person who shared sheetss_to_banana with you.
If you want to report bug or request a feature and you have a GitHub account, please do so [here](https://github.com/bruno-ritmista/samba/issues).