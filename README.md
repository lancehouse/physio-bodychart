# PhysioChart — Specialist Physiotherapy Clinical Tool

A two-app system for comprehensive pain assessment and clinical documentation:
- **GTK Body Chart** (C/GTK4) — Pressure-sensitive stylus drawing with clinical overlays
- **Assessment TUI** (Python/Textual) — Structured assessment narrative and report generation

Both apps synchronize through shared session JSON files, enabling seamless clinical workflow.

---

## Project Structure

```
physio-bodychart/               ← GTK4/C desktop stylus app
├── src/                        ← C source code
├── build/                      ← Compiled output (ninja)
├── meson.build                 ← Meson build config
└── ...

physio-assessment/              ← Python Textual TUI app
├── physio_assessment/          ← Python package
├── pyproject.toml              ← Python dependencies
├── .venv/                       ← Virtual environment (Python 3.12)
└── ...

docs/                           ← Shared documentation
├── CLAUDE_CHAT_ARCHITECTURE_REVIEW.md   ← For architecture review
├── SESSION_SUMMARY_20260508.md          ← Phase 1.11 implementation details
├── ARCHITECTURE_20260508.md             ← System design & data flows
└── ...

claude instructions.txt         ← Original project specification
SESSION_JSON_SCHEMA.md          ← Data contract between apps (THIS FILE)
```

---

## Quick Start

### GTK Body Chart App

```bash
cd physio-bodychart
ninja -C build
./build/physio-bodychart
```

### Python Assessment TUI

```bash
cd physio-assessment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
python -m textual run physio_assessment.tui:PhysioAssessmentTUI
```

---

## Data Synchronization

Both apps share patient session data through JSON files:

**Active Session Pointer:**
```
~/.local/share/physio-bodychart/session_current.json
```

**Full Session Data:**
```
~/.local/share/physio-bodychart/Physio-Bodychart/[patient_id]_[timestamp]/
└── [session_name]_session.json
```

**Synchronization Model:**
- GTK app **owns**: `subjective` (strokes, notes, arrows), `objective` (zones, PPT), `ui` state
- Python app **owns**: `assessment` (narrative fields: history, factors, diagnosis, plan)
- Both apps **read** the other's sections (read-only for owned sections)
- 1-second polling detects changes; atomic writes prevent corruption

See `SESSION_JSON_SCHEMA.md` for the complete data contract.

---

## Building & Testing

### GTK App

```bash
cd physio-bodychart
ninja -C build              # Build
./build/physio-bodychart    # Run
```

Verify compilation:
```bash
ninja -C build 2>&1 | tail -5
```

### Python TUI

```bash
cd physio_assessment
python3 -m py_compile watcher.py storage.py tui.py
```

### Live Testing (Both Apps)

1. Start GTK app (creates session files)
2. Start Python TUI (reads session, shows patient info)
3. Draw in GTK → Python displays chart summary
4. Edit assessment in Python → saved to session JSON
5. Switch sessions in GTK → Python detects change within 1 second

See `docs/SESSION_SUMMARY_20260508.md` for full testing checklist.

---

## Development Phases

### Phase 1 — Foundation ✅
- 1.1–1.5: GTK UI foundation
- 1.6–1.8: Python structure + schemas
- 1.9–1.10: Session list UI + three-panel shell
- **1.11: File watcher + JSON sync** ← CURRENT

### Phase 2 — Core Assessment 🕐
- 2.1–2.8: Wire subjective/objective/diagnosis sections

### Phase 3 — Knowledge Base 🕐
- 3.1–3.6: Clinical patterns + special tests

### Phase 4 — Polish 🕐
- 4.1–4.5: Export, Ollama integration, additional regions

---

## Documentation

**For Architecture Review (Claude Chat Web):**
- Start with: `docs/CLAUDE_CHAT_ARCHITECTURE_REVIEW.md`
- Detailed design: `docs/ARCHITECTURE_20260508.md`

**For Implementation Details:**
- Session 1.11 summary: `docs/SESSION_SUMMARY_20260508.md`
- Data schema: `SESSION_JSON_SCHEMA.md` (this repo)

**For Git Operations:**
- Quick push: `docs/GITHUB_UPDATE_QUICK.txt`
- Detailed guide: `docs/GIT_PUSH_GUIDE.md`

**Original Specification:**
- `claude instructions.txt` (v2)

---

## For Claude Chat Review

This project is designed for iterative architectural review. To get Claude Chat's feedback:

1. Open `docs/CLAUDE_CHAT_ARCHITECTURE_REVIEW.md`
2. Go to https://claude.ai/
3. Paste the content into a conversation
4. Ask: *"Is this architecture ready for Phase 2?"*
5. Implement feedback
6. Push to GitHub

---

## Environment Setup

### GTK Development
- GCC/Clang
- Meson + Ninja
- GTK4 development libraries
- json-c

### Python Development
- Python 3.12 (NOT 3.13 — Textual requires 3.12 for stable operation)
- Virtual environment (`.venv/`)
- Dependencies: `textual`, `pydantic`, `jinja2`

### Recommended
- Git (you're reading this from a git repo)
- A text editor (VS Code, Vim, etc.)
- Terminal with bash/zsh

---

## License

(Add your license here when ready)

---

## Contact

Built for clinical use. Questions about architecture, safety, or implementation?
- See `docs/` for detailed explanations
- Review `claude instructions.txt` for project requirements
- Ask Claude Chat for architectural guidance
