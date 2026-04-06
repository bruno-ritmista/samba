---
name: understand-bananadrum
description: This skill knows the web-app BananaDrum: 1) understands what this web-app does 2) knows how the web app is implemented 4) privides expertise for debugging, extending, improving, refactoring, creating other scripts that depend on web-app.

# Understand BananaDrum

BananaDrum is a **samba rhythm sequencer web application** — a browser-based drum machine designed for samba bands. Users build percussive arrangements by toggling notes on/off across instrument tracks, then play them back via the Web Audio API.

**Repository path:** `c:\Users\bruno\git\BananaDrum`

---

## Architecture: Layered Monorepo

The codebase is a TypeScript/React monorepo with 4 npm workspace packages in `packages/`:

| Package | Role | Depends on |
|---|---|---|
| `bananadrum-core` | Data model, edit commands, serialisation, undo/redo | — |
| `bananadrum-player` | Web Audio API playback engine, real-time scheduling | core |
| `bananadrum-ui` | React components, animation, user interaction | core + player |
| `bananadrum-webapp` | Entry point, instrument definitions, demo song | all three |

**Build pipeline:** TypeScript → Webpack → `packages/bananadrum-webapp/www/bundle.js`
**Tests:** Mocha + Chai, only on `bananadrum-core` (`npm test` from repo root)

---

## Core Domain Model

All interfaces live in `packages/bananadrum-core/src/prod/types/general.ts`.

- **`BananaDrum`** — top-level container; provides `edit()`, `undo()`, `redo()`, holds the `Arrangement` and `Library`
- **`Arrangement`** — the composition; has `title`, `timeParams`, and an array of `Track`s
- **`Track`** — one instrument's rhythm; contains `Note[]` and `Polyrhythm[]`
- **`Note`** — a single hit or rest at a `Timing`; `noteStyle = null` means rest
- **`Timing`** — immutable `{bar: number, step: number}`; steps are always sixteenths
- **`TimeParams`** — `timeSignature`, `tempo`, `length`, `pulse`, `stepResolution`; validates timings
- **`Polyrhythm`** — a section between two notes with its own subdivided `Note[]` grid
- **`Instrument`** — metadata + audio buffers for different hits; lazily loaded
- **`NoteStyle`** — a specific sound variant of an instrument (e.g. Agogo_Low, Agogo_High); carries muting rules
- **`Library`** — the instrument catalogue; lazy-loads instruments and audio on demand

**Snapshots** (for serialisation/undo): `ArrangementSnapshot`, `SerialisedArrangement` (title + composition string + version)

---

## State Mutations: EditCommands

All changes to an arrangement flow through `bananaDrum.edit(command)`.  
Command types are defined in `packages/bananadrum-core/src/prod/types/edit_commands.ts`.  
The logic that applies them is in `packages/bananadrum-core/src/prod/edit.ts`.  
`UndoRedoStack` (same package) snapshots state before/after each edit.

---

## Reactivity: Publisher/Subscriber

BananaDrum uses a custom pub/sub pattern (not React state for the core model).  
`Publisher` is in `packages/bananadrum-core/src/prod/Publisher.ts`.  
Domain objects expose a `publisher` that fires when they change; UI components subscribe to receive updates.

---

## Playback Engine

`packages/bananadrum-player/src/prod/`:

- **`EventEngine`** — wraps `AudioContext`; schedules upcoming events with a 250ms lookahead
- **`ArrangementPlayer`** — walks the arrangement and emits note events at the right times
- **`TrackPlayer`** — per-track event generator
- **`TimeCoordinator`** — converts `Timing` coordinates to real-time seconds
- **`Muting`** — evaluates muting rules to suppress notes when needed

---

## UI Layer

`packages/bananadrum-ui/src/prod/`:

- **`BananaDrumViewer.tsx`** — root React component
- `components/arrangement/` — tempo/time controls, arrangement-level UI
- `components/track/` — track row display
- `components/note/` — note cell display
- `components/guiderail/` — visual beat guides
- **`AnimationEngine`** — keeps UI animations in sync with audio playback
- **`SelectionManager`** — manages the set of currently selected notes
- **`ModeManager`** — tracks the current editing mode

---

## Application Entry Point

`packages/bananadrum-webapp/src/index.ts`:

1. Shows a loading screen; checks URL params for a shared arrangement and `localStorage` for a saved session
2. Calls `getLibrary().load(bateriaInstruments)` (instruments defined in `bateria-instruments.ts`)
3. Optionally `deserialiseArrangement()` from URL
4. `createBananaDrum(library, snapshot)` → `createBananaDrumPlayer(bananaDrum)` → `createBananaDrumUi(bananaDrumPlayer, wrapper)`
5. Exposes `arrangement`, `arrangementPlayer`, `library`, `bananaDrum`, `bananaDrumPlayer`, `bananaDrumUi` on `window` for debugging

---

## Serialisation

`packages/bananadrum-core/src/prod/serialisation/`:

- Converts an `Arrangement` to a compact composition string for share links
- `serialisers.ts` / `deserialisers.ts` — encode/decode arrangement ↔ URL
- `numeric_functions.ts` — custom number encoding used in the composition string
- Version field in `SerialisedArrangement` guards backwards compatibility

---

## Key Domain Vocabulary

| Term | Meaning |
|---|---|
| Bateria | The percussion section of a samba band (Portuguese) |
| Bar | A measure of music |
| Step | A subdivision of a beat; currently always a sixteenth note |
| Pulse | The main rhythmic reference beat |
| NoteStyle | A sound variant of an instrument (e.g. open vs muted hit) |
| Muting rule | A rule suppressing a note in certain contexts (e.g. "no-double", "every-other", or mute when another instrument plays) |
| Polyrhythm | A section between two notes with an independent subdivided grid |
| Composition string | The URL-encoded compact representation of the full arrangement |
| Snapshot | A serialisable copy of state used for undo/redo and sharing |
| EditCommand | The unit of mutation passed to `bananaDrum.edit()` |
| Lookahead | 250ms buffer the EventEngine uses to pre-schedule audio events |

---

## Typical Investigation Paths

- **Add/modify a note action:** `edit_commands.ts` (define type) → `edit.ts` (implement logic) → UI component that calls `bananaDrum.edit()`
- **Change audio behaviour:** `EventEngine.ts`, `ArrangementPlayer.ts`, `TrackPlayer.ts`, `Muting.ts`
- **Change how an instrument sounds/looks:** `bateria-instruments.ts` (webapp) and `Library.ts` + `Instrument`/`NoteStyle` types (core)
- **Change serialisation/share links:** `serialisation/` folder in core
- **Add a UI component:** `bananadrum-ui/src/prod/components/` and wire into `BananaDrumViewer.tsx`
- **Understand undo/redo:** `UndoRedoStack.ts`, `edit.ts`, snapshot types in `snapshots.ts`
