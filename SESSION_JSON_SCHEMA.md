# Session JSON Schema — Data Contract Between Apps

This document defines the JSON schema that synchronizes the GTK body chart and Python assessment TUI. **Both apps must maintain compatibility with this schema.**

---

## Quick Reference

| Block | Owner | Purpose | Apps |
|-------|-------|---------|------|
| `subjective` | GTK | Strokes, notes, arrows, links | GTK writes, Python reads |
| `objective` | GTK | Zones, PPT points | GTK writes, Python reads |
| `ui` | GTK | Layout, view settings | GTK writes, Python reads |
| `assessment` | Python | Narrative fields | Python writes, GTK reads |
| `report` | Legacy | Old format (deprecated) | Both read for compat |

---

## Files and Locations

### session_current.json
**Purpose:** Active session pointer (Python discovers which session to work on)
**Location:** `~/.local/share/physio-bodychart/session_current.json`
**Owner:** GTK
**Update Frequency:** Every significant change (stroke commit, overlay change, etc.)
**Schema Version:** 2

```json
{
  "schema_version": 2,
  "session_file": "/home/user/Physio-Bodychart/JB_07_05_2026_1430/JB_07_05_2026_1430_session.json",
  "session_id": "JB",
  "session_label": "Lower back assessment",
  "date": "2026-05-07T14:30:00Z",
  "body_chart": {
    "strokes": [],
    "symptom_types_used": [0, 2],
    "views_drawn": [0, 1]
  }
}
```

**Fields:**
- `schema_version` (int) — Schema version; Python checks this for compatibility
- `session_file` (string) — Absolute path to full session JSON; Python reads this to know which file to open
- `session_id` (string) — Patient ID (e.g., initials)
- `session_label` (string) — Human-readable session description
- `date` (ISO8601 string) — Session creation timestamp
- `body_chart.strokes` (array) — Summary of strokes (currently empty in this file)
- `body_chart.symptom_types_used` (array of ints) — Symptom type indices drawn (0=pain constant, 2=paraesthesia, etc.)
- `body_chart.views_drawn` (array of ints) — Body views with content (0=anterior, 1=posterior, etc.)

---

### Full Session JSON
**Purpose:** Complete session data (all clinical information)
**Location:** `~/.local/share/physio-bodychart/Physio-Bodychart/[session_name]/[session_name]_session.json`
**Owner:** GTK (writes), Python (reads/writes assessment block)
**Update Frequency:** After every stroke, note, objective item, or assessment edit
**Schema Version:** 2

```json
{
  "version": 2,
  "patient_id": "JB",
  "session_label": "Lower back assessment",
  "session_name": "JB_07_05_2026_1430",
  "created": 1714953600,
  "modified": 1714954200,
  
  "launched_by": "tui",
  "workflow_stage": "03_objective",
  "body_chart_requested": false,
  "body_chart_complete": true,
  
  "ui": {
    "layout_mode": 0,
    "right_slot_views": [0, 1]
  },
  
  "subjective": {
    "strokes": [
      {
        "type": 0,
        "view": 0,
        "wide": false,
        "pts": [
          [50.0, 100.0, 0.8],
          [51.0, 101.0, 0.85],
          [52.0, 102.0, 0.9]
        ]
      }
    ],
    "notes": [
      {
        "view": 0,
        "bx": 50.0,
        "by": 100.0,
        "number": 1,
        "temporal": 0,
        "depth": 0,
        "quality": 0,
        "avg": 6,
        "worst": 8,
        "text": "(1) Constant sharp pain, 6/10 avg, 8/10 worst"
      }
    ],
    "arrows": [
      {
        "view": 0,
        "x1": 50.0,
        "y1": 100.0,
        "cx": 55.0,
        "cy": 105.0,
        "x2": 60.0,
        "y2": 110.0
      }
    ],
    "link_matrix": [[0, 1], [1, 0]],
    "link_relations": [
      {"from": 0, "to": 1, "state": 1}
    ],
    "link_summary_active": false,
    "link_summary_view": 0,
    "link_summary_bx": 12.0,
    "link_summary_by": 378.0
  },
  
  "objective": {
    "zones": [
      {
        "type": 0,
        "view": 0,
        "points": [[50.0, 100.0], [55.0, 105.0], [60.0, 110.0]]
      }
    ],
    "points": [
      {
        "type": 0,
        "view": 0,
        "bx": 50.0,
        "by": 100.0,
        "ppt": 3.5
      }
    ]
  },
  
  "neuro": {},
  
  "assessment": {
    "history": "Patient reports 3-month history of lower back pain...",
    "agg_factors": "Bending, lifting, prolonged sitting",
    "ease_factors": "Lying down, stretching, heat",
    "behaviour_24hr": "Pain worse in morning, improves with movement",
    "diagnosis": "Mechanical low back pain, likely discogenic component",
    "plan": "Graduated return to activity, core strengthening, review in 2 weeks",
    "clinical_notes": "Reassured patient regarding benign nature of presentation",
    "modified": 1714954200
  },
  
  "report": {
    "assessment": "...",
    "plan": "...",
    "clinical_notes": "...",
    "note_subj": [
      {
        "hist": "...",
        "aggs": "...",
        "ease": "...",
        "24hr": "..."
      }
    ]
  }
}
```

---

## Workflow Fields (v2+)

**New in Schema Version 2:**
- `launched_by` (string) — Which app created this session: `"tui"`, `"gtk"`, or `"standalone"`
- `workflow_stage` (string) — Last completed section identifier (e.g., `"01_consent"`, `"03_objective"`)
- `body_chart_requested` (boolean) — Whether TUI has requested GTK to launch (used for handoff)
- `body_chart_complete` (boolean) — Whether body chart has been completed in this session

**Purpose:** Enable bidirectional workflow between TUI (primary entry point) and GTK (body chart component).

---

## Schema Details

### Ownership Rules (Critical for Data Integrity)

**GTK owns and writes:**
- `subjective` block (all fields)
- `objective` block (all fields)
- `ui` block (all fields)
- Top-level metadata (`version`, `patient_id`, `session_label`, `session_name`, `created`, `modified`)

**Python owns and writes:**
- `assessment` block (all fields)

**Both read:**
- Everything they don't own

**Both preserve:**
- Sections they don't own (never delete or modify)

### Synchronization Guarantees

1. **No overlapping writes** — GTK and Python never write to the same block
2. **Atomic writes** — Temp file + rename prevents corruption
3. **Debouncing** — App ignores its own writes within 2 seconds (via timestamp check)
4. **Polling** — Python polls `session_current.json` every 1 second; full session file checked on session switch

### Version Compatibility

If `version` in the JSON doesn't match an app's expected version:
- **GTK:** Logs warning, continues (tolerant reader)
- **Python:** Pydantic models use `extra='ignore'` to ignore unknown fields

**Breaking schema changes require:**
1. Version bump (e.g., 2 → 3)
2. Update both apps to handle new version
3. Migration logic if old data must be transformed

### Data Types

**Numeric:**
- Coordinates (body space): float
- Pressure: float (0.0–1.0)
- Intensity scores: int (0–10)
- Timestamps: int (seconds since epoch) or ISO8601 string

**Arrays:**
- Stroke points: `[x, y, pressure]`
- Body coordinates: `[x, y]` (0–200 width, 0–400 height)
- Symptom/view IDs: indices into enum (0-based)

**Strings:**
- Text fields: UTF-8, unlimited length (but practical limit ~8KB per field in GTK)
- ISODate8601: `2026-05-07T14:30:00Z`

---

## Migration Path (If Needed)

When schema changes are necessary:

1. **Prepare both apps** — Implement new schema handling in both codebases
2. **Test together** — Verify both apps read/write new schema correctly
3. **Version bump** — Increment `version` in schema
4. **Backward compat** — Both apps should still read old `version` (with graceful degradation)
5. **Announce breaking change** — Document in release notes if old schema stops being supported

---

## Example: Adding a New Field

**Scenario:** Python team wants to add `severity_region` (which body region is most affected) to assessment.

**Steps:**

1. **Python adds field:**
   ```python
   # In models.py or storage.py
   assessment["severity_region"] = "lumbar"  # or cervical, thoracic, etc.
   ```

2. **Python writes to JSON:**
   ```json
   "assessment": {
     "severity_region": "lumbar",
     ...
   }
   ```

3. **GTK reads it (tolerantly):**
   - GTK's json reader ignores unknown fields
   - Existing GTK code continues to work

4. **GTK can optionally use it:**
   - Later, GTK can read `severity_region` to highlight the relevant body area
   - But it doesn't need to immediately — just needs to preserve it

5. **Version bump only if:**
   - Field is required (GTK must write it)
   - Schema structure changes (not just new optional field)

---

## Testing Synchronization

Before committing schema changes:

1. ✅ Both apps can read the new schema
2. ✅ Both apps write the new schema correctly
3. ✅ Concurrent writes don't corrupt JSON
4. ✅ Session switch detects changes within 1 second
5. ✅ Assessment edits persist in session JSON
6. ✅ GTK doesn't lose drawing data during Python updates

See `docs/SESSION_SUMMARY_20260508.md` for full testing checklist.

---

## Changelog

### Version 2 (Current)
- Added `session_file` and `session_label` to `session_current.json`
- Added `assessment` block to full session JSON (Python-owned)
- Schema version field for compatibility checking

### Version 1 (Legacy)
- Original schema
- No `session_file` in session_current.json
- Assessment data in `report.assessment` only

---

## References

- GTK persistence code: `physio-bodychart/src/persistence.c`
- Python storage code: `physio-assessment/storage.py`
- File watcher: `physio-assessment/watcher.py`
- Full architecture: `docs/ARCHITECTURE_20260508.md`
