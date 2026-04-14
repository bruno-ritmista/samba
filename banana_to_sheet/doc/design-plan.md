# Feature Plan: Banana Drum URL to Google Sheets Converter

---

## Overview

This feature allows a user to take a shareable Banana Drum link and automatically convert its musical content into a Google Sheet. It reuses knowledge from the existing "Sheets to Banana Drum" feature, but works in reverse — decoding the URL and writing the notes into a structured sheet.

---

## Goals

- Make it easy to capture and reuse music from a Banana Drum link without manual transcription.
- Maintain consistency with the existing Google Sheets template format.
- Keep the implementation simple and focused, with clear paths for future improvements.

---

## How It Works (User Journey)

1. The user opens a Google Colab notebook provided for this feature.
2. The user pastes a Banana Drum shareable URL as input.
3. Optionally, the user provides the name of an existing worksheet to append notes to.
4. The notebook runs and either:
   - **Creates a new worksheet** (if no worksheet name is provided), or
   - **Appends to an existing worksheet** (if a worksheet name is provided).
5. The music notes from the Banana Drum link appear in the Google Sheet.

---

## Detailed Behaviour

### Template Detection

- The notebook looks for a worksheet named exactly **"Vorlage"** or **"Template"** (case-sensitive, no numbers in the name).
- Worksheets with numbers in their name are treated as already-copied sheets and are ignored for this purpose.

---

### Mode 1 — Create New Worksheet

Triggered when the user does **not** provide a worksheet name.

1. The notebook identifies the template worksheet.
2. It duplicates the template to create a new, empty worksheet.
3. The new worksheet is named using the **title encoded in the Banana Drum URL**.
   - If the URL contains no title, a **default name** is used (e.g. "Break"), incremented if needed (e.g. "Break 1", "Break 2").
   - If a sheet with that title already exists, the name is incremented (e.g. "My Beat 1", "My Beat 2").
4. The decoded music notes are written into the new worksheet.

---

### Mode 2 — Append to Existing Worksheet

Triggered when the user **provides a worksheet name** as an argument to the notebook.

1. The notebook locates the worksheet by the provided name.
2. It scans the worksheet to find the **last row containing notes**.
   - Column 1 is always populated by the template (instrument names, bar numbers) and is **ignored** for this detection.
   - The notebook scans from **Column 2 onwards** to find the last non-empty row with note data.
3. The decoded notes from the Banana Drum URL are written **below** the existing content.

---

### Note Writing Rules

- Only **individual note characters** are written — no shorthand keywords like "Levada" or "Virada".
- Only note data is written — **no tempo, time signature, or other metadata**.
- The notebook **does not change any cell formatting**. It only fills in note content.

---

### Authorization

- Authorization to read/write Google Sheets is handled by the existing infrastructure already in place for other features. No new setup is required.

---

## Assumptions

- The Banana Drum URL is assumed to be valid. No URL validation is performed in this version.
- The template sheet is always sized appropriately to hold any Banana Drum composition.
- Each Banana Drum URL contains exactly one break.

---

## Out of Scope (Future Increments)

| Topic | Notes |
|---|---|
| **Error handling** | Malformed URLs, missing template sheet, and write failures are not handled in this version. To be addressed in a future increment. |
| **Polyrhythm support** | Banana Drum URLs can encode polyrhythms (e.g. 6/8 bars). Decoding these back into the sheet format is not supported in this version. |
| **Keyword reconstruction** | Keywords like "Levada" and "Virada" will not be reconstructed from individual notes. This is intentional and not planned as a future feature. |

---

## Key Risks & Notes for Implementors

- **Column 1 is not a reliable indicator of where notes end.** It is always filled by the template structure. Always scan Column 2 onwards to detect the last row of actual note content.
- **Sheet naming must be robust.** Both "Vorlage" and "Template" must be supported as template names, and incrementation logic must handle edge cases (e.g. "My Beat", "My Beat 1", "My Beat 2" already existing).
- **Decoding logic is already known** from the "Sheets to Banana Drum" feature and should be reused or referenced directly.

---

*This plan was defined prior to implementation. No code has been written yet.*