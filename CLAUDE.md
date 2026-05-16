# PhysioChart — Project Overview

Specialist physiotherapy clinical tool for a Lenovo Yoga running Fedora 43 in tablet mode.
Primary input in body-chart mode is pressure-sensitive stylus/touchscreen. Keyboard primary in TUI.

## Two-app architecture

```
physio-bodychart/          GTK4 / C
  Stylus body chart app
  Writes → ~/Physio-Bodychart/<session>/_session.json
  Writes → ~/.local/share/physio-bodychart/session_current.json  (active session pointer)

physio-assessment/         Python 3.12 / Textual TUI
  Structured clinical assessment + report generation
  Reads  ← session_current.json  (to know which session is active)
  Reads/writes → ~/Physio-Bodychart/<session>/_assessment.json
  Reads/writes → ~/Physio-Bodychart/<session>/_objective.json
```

The two apps are **independent**. Changes to one do not require changes to the other unless the
shared session JSON schema changes. Schema changes require a version bump in both apps.

## Session file layout

Every session lives in its own directory under `~/Physio-Bodychart/`:

```
~/Physio-Bodychart/<session-name>/
  <name>_session.json       GTK-owned: body chart strokes, overlays, regions, patient identity
  <name>_assessment.json    TUI-owned: assessment sections 01–07 (consent → barriers)
  <name>_objective.json     TUI-owned: objective examination sections 01–07
  <name>_report.md          Generated on every save — compact Markdown clinical report
  <name>_raw.txt            Generated on every save — full plain-text raw export of all fields
```

All files are human-readable JSON or plain text. This is intentional and permanent — do not
introduce binary formats or database files. Files are used individually for various clinical tasks.

## Data persistence model

- **No SQLite.** JSON files are the permanent storage format.
- Auto-save on every field change. No save button anywhere.
- Atomic writes (temp file + rename) to prevent corruption.
- The GTK app owns `_session.json`. The TUI owns `_assessment.json` and `_objective.json`.
  Never write to the other app's file.

## Environment

- Fedora 43, GNOME, kitty terminal (GPU-accelerated; enables remote-control focus switching)
- GTK app: build with `ninja -C build` inside `physio-bodychart/`
- TUI: Python 3.12 venv inside `physio-assessment/`; activate before running

## Overarching rules

1. **Button width ≤ ¼ screen** — all interactive button widgets max 25% of available width.
   If a label doesn't fit, place it in an adjacent `Static` widget.
2. **Flag, don't guess clinical content** — if a field label, test name, or clinical term is
   ambiguous, stop and ask before interpreting or inventing content.
3. **No UI logic in storage** — `storage.py` reads/writes JSON only; no Textual imports,
   no clinical decisions. Sections collect/load data; storage persists it.
4. **Never lose data** — auto-save on every field change; atomic writes always.

## Planned phases (not yet built)

- **Phase 3** — Right-panel clinical knowledge base: context engine, `clinical_kb.db`,
  special test widgets with Sn/Sp, pattern matching from body chart data.
  Do not build this until explicitly requested. Do not design current code to prevent it.
