---
name: understand-sapu-music-notes
description: Understands percurssion music notes in custom table format as used by samba music group Sapucaiu no Samba.

# Understand Sapu Music Notes

Music notes created by members of Sapucaiu no Samba follow these rules.

---

## File / Sheet structure

- Each CSV/sheet contains notes for **one song**. The song title is in a merged cell in row 1 (exported as the first non-empty cell of row 0).
- The sheet contains one or more **breaks** (Portuguese: *breaks*, *desenhos*, *viradas*). Each break is a self-contained rhythmic section.
- Breaks are stacked vertically, separated by an empty row.
- Within each break, the phrase is split into groups of 4 bars. Each group occupies a horizontal block of rows, also separated by an empty row.

---

## Column layout

Every data row (except the break header and separator rows) has this fixed structure:

| Col 0 | Cols 1–16 | Cols 17–32 | Cols 33–48 | Cols 49–64 | Cols 65–72 |
|---|---|---|---|---|---|
| Label (section or instrument name) | Bar N | Bar N+1 | Bar N+2 | Bar N+3 | BananaDrum link (optional) |

- **Each bar = 16 columns**, one column per sixteenth note.
- Within a bar, the four beats fall at positions **1, 5, 9, 13** (relative to the bar's first column).
- Total useful columns: 1 label + 64 note columns = 65.
- **The same 65-column structure repeats for every 4-bar group**; bars 1–4 use cols 1–64, bars 5–8 also use cols 1–64 (in their own rows), etc.

---

## Row types

### 1. Break header row
A single row with the break name in col 0 (or col 1 if col 0 is empty). All other cells are empty.  
Example: `Break Alegria invade o Pelô`

### 2. Section label row
First row of each 4-bar group. Col 0 contains the bar range (e.g. `1 - 4`, `5 - 8`). Cols 1, 17, 33, 49 each contain a lyric fragment as a cue for that bar. Col 65 may contain a BananaDrum link.

### 3. Instrument rows
One row per instrument. Col 0 = instrument name. Cols 1–64 = notes.

### 4. Empty / separator rows
Rows where all cells are empty. Used to separate breaks and 4-bar groups.

---

## Instruments

Rows appear in this order (one or more may be absent in any given break):

| Row label | Instrument |
|---|---|
| `Surdo 1a/"2a"` | Surdos 1 (lowest) and Surdo 2 (mid) as a combined row |
| `Surdo 3a` | Surdo 3 (highest)|
| `Caixa` | Snare drum |
| `Repique` | Repinique |
| `Timbau` | Timbau |
| `Tamborim` | Tamborim |
| `Chocalho` | Shaker |
| `Agogô` | Double bell |

---

## Note characters

Each non-empty cell in the note area (cols 1–64) contains one character (or a keyword — see below).

### Universal
| Character | Meaning |
|---|---|
| `X` | Standard hit fro all instruments|
| *(empty)* | Rest — no note played |

### Surdo 1a/2a
| Character | Meaning |
|---|---|
| `1` | Surdo 1 plays |
| `2` | Surdo 2 plays |
| `O` | Surdo 1 and Surdo 1 play |

### Surdo 3a
| Character | Meaning |
|---|---|
| `D` | Damped stroke (muffled hit) |
| `W` | Roll stroke (Wirbel in German) |

### Caixa
| Character | Meaning |
|---|---|
| `/` | Rimshot |
| `W` | Roll stroke (Wirbel in German) |

### Repique
| Character | Meaning |
|---|---|
| `S` | Slap |
| `O` | Open tone |
| `/` | Rimshot |
| `W` | Roll stroke (Wirbel in German) |

### Timbau
| Character | Meaning |
|---|---|
| `S` | Slap |
| `O` | Open tone |
| `OO` | two 1/32th pen tone |

### Agogô
| Character | Meaning |
|---|---|
| `L` | Low bell |
| `H` | High bell |

---

## Keyword values: "Levada" and "Virada"

Some cells contain the text **`Levada`** or **`Virada`** instead of a single note character.  
These are **merged cells** in the original Google Sheet; in CSV they appear in the first column of the merged region, with the remaining columns empty.

| Keyword | Meaning |
|---|---|
| `Levada` | The instrument plays its standard groove pattern for the duration of the merged cell (one beat or one full bar) |
| `Virada` | The instrument plays a standard fill/transition pattern for the duration of the merged cell |

The merge span tells you the scope:
- If the keyword repeats every 4 columns (`Levada,,,,Levada,,,,…`), the scope is **one beat per occurrence**.
- If the keyword appears once and the next 15 columns are empty, the scope is **one full bar**.

---

## Example — reading a row

```
Surdo 1a/"2a",  Levada,,,,  Levada,,,,  Levada,,,,  X,,,  ,,,,,,,,,,,,,  1,,,,  2,,,,  1,,,,  2,,,,  …
```

- Bar 1, beat 1: Levada (standard groove)
- Bar 1, beat 2: Levada
- Bar 1, beat 3: Levada
- Bar 1, beat 4: X (hit — the "corte"/cut)
- Bar 2: rests until beat 4
- Bar 2, beat 4: "1" — Surdo 1 enters
- Bar 3–4: alternating 1 / 2 every beat — classic surdo call-and-response re-enters

---
