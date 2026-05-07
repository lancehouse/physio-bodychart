# PhysioBodyChart — Phase 2 Implementation Plan

**Status:** Planning  
**Last updated:** 2026-05-01  
**json-c already linked** — no new library dependency needed for JSON save/load (meson.build line 8).

---

## Overview

Phase 2 adds four major capabilities on top of the existing subjective body chart:

| Phase | Name | Goal |
|-------|------|------|
| 2A | Session identity + JSON save/load | Foundation: named sessions, persist all data, reload and continue |
| 2B | Objective body chart | Clinician-measured findings: drawn zones + point measurements |
| 2C | Neurological testing module | Structured neuro assessment, standalone + region-anchored |
| 2D | Report/summary editor | TUI-style text editor, auto-populated from all chart data |
| 2E | Export bundle refactor | Named bundle: subj image + obj image + report + JSON, all together |

Each phase is independently completable. 2B depends on 2A. 2C depends on 2B. 2D depends on 2A/2B/2C. 2E depends on all prior phases.

---

## Cross-cutting architectural decisions

**All decisions confirmed ✓**

### ✓ Decision 1: Top-level navigation — SIDEBAR

Mode switching stays in the sidebar. No top tab strip (preserves vertical canvas space on ThinkPad 11e). Sidebar expands from 110px → **150px**. Compact 3-button mode strip at top of sidebar: `[Sx] [Obj] [Rpt]`. Sidebar tool content below adapts per mode.

```
┌─────────┬────────────────────────────────────────────┐
│[Sx][Obj]│                                            │
│  [Rpt]  │  full-height canvas (unchanged)            │
│─────────│                                            │
│ tools   │                                            │
│ for     │                                            │
│ current │                                            │
│ mode    │                                            │
└─────────┴────────────────────────────────────────────┘
```

### ✓ Decision 2: ObjZone vs reusing Stroke struct

`ObjZone` (drawn zone on objective chart) is structurally identical to `Stroke` but uses a different type enum. Two options:
- **Separate struct** `ObjZone` with `ObjZoneType` — clean separation, slight code duplication
- **Reuse `Stroke`** with a `chart_type` flag (0=subj, 1=obj) — less code but mixes concerns

Recommendation: separate struct, keep subjective and objective drawing machinery independent.

### ✓ Decision 3: Neuro level pre-population

The neuro form rows = spinal levels. Options:
- **Curated shortlist** (C5/C6/C7/C8/T1/L2/L3/L4/L5/S1) with an "add level" button
- **Full C2–S4 grid** (~28 rows), always visible

Recommendation: curated shortlist + add button. Most assessments use <12 levels.

### ✓ Decision 4: Report auto-section editing

When you hit "Regenerate" on the report, what happens to text you've manually added inside auto-sections?
- **Overwrite**: simple, but destroys edits
- **Preserve manual, replace auto-tagged ranges only**: complex but better UX

Recommendation: preserve manual additions. Auto-sections are tagged with a GtkTextTag; regenerate only replaces those tagged ranges.

### ✓ Decision 5: Session folder structure — FOLDER PER SESSION

Each session lives in its own folder. Filename convention: `INITIALS_DD_MM_YYYY_HHMM`

```
~/PhysioChart/JB_01_05_2026_1430/
    JB_01_05_2026_1430_session.json
    JB_01_05_2026_1430_subj.png
    JB_01_05_2026_1430_obj.png
    JB_01_05_2026_1430_report.txt
    JB_01_05_2026_1430.pdf
```

### JSON schema (all phases)

```json
{
  "version": 2,
  "patient_id": "JB",
  "session_name": "JB_20260501",
  "created": 1746057600,
  "modified": 1746061200,
  "subjective": {
    "strokes": [
      { "type": 0, "view": 0, "wide": false, "pts": [[x, y, p], ...] }
    ],
    "notes": [
      { "view": 0, "bx": 12.0, "by": 30.0, "number": 1,
        "temporal": 0, "depth": 0, "quality": 0, "avg": 3, "worst": 7 }
    ],
    "arrows": [
      { "view": 0, "x1": 10.0, "y1": 20.0, "cx": 15.0, "cy": 25.0, "x2": 20.0, "y2": 30.0 }
    ],
    "link_relations": [
      { "from": 0, "to": 1, "state": 1 }
    ]
  },
  "objective": {
    "zones": [
      { "type": 0, "view": 0, "wide": false, "pts": [[x, y, p], ...] }
    ],
    "points": [
      { "type": 0, "view": 0, "bx": 50.0, "by": 100.0,
        "value": 250.0, "unit": "kPa", "label": "PPT 250kPa" }
    ]
  },
  "neuro": {
    "levels": [
      { "level": "L4", "sens_l": 0, "sens_r": 1,
        "pwr_l": 5, "pwr_r": 4, "ref_l": 2, "ref_r": 2, "notes": "" }
    ],
    "babinski_l": false,
    "babinski_r": false,
    "hyperreflexia": false,
    "spasticity": false,
    "clonus": false,
    "umn_notes": "",
    "fasciculations": false,
    "wasting": false,
    "hypotonia": false,
    "lmn_notes": ""
  },
  "report": {
    "text": "SUBJECTIVE\n══════════\n...\nOBJECTIVE\n══════════\n..."
  }
}
```

---

## Phase 2A — Session identity + JSON save/load

### Goal
Every session has a patient ID. All data (strokes, notes, arrows, objective findings, neuro, report) persists to a JSON file. Existing sessions can be reopened and continued. Strokes can be deleted individually (undo already works; this is about the erase tool working on objective chart too — confirm scope).

**Unlocks:** All later phases can save/load their data.

### New files
- `src/persistence.c` — JSON serialise/deserialise for all AppState data
- `src/persistence.h`

### Existing files changed
| File | Change |
|------|--------|
| `src/canvas.h` | Add `patient_id[32]`, `session_name[64]`, `session_file[512]`, `time_t session_created` to AppState |
| `src/main.c` | Show launch dialog before `window_create`; pass patient ID into AppState |
| `src/window.c` | File tab: replace "Save SVG" with "Save Session"; add "Open Session"; auto-save hook on mode/tab switch |
| `src/session.c` | Thin wrapper: export functions now use `session_name` as filename base; delegate to persistence.c for JSON |

### Key new structs

```c
// persistence.h
gboolean persistence_save(AppState *app, const char *path);
gboolean persistence_load(AppState *app, const char *path);
void     persistence_autosave(AppState *app);  // saves to app->session_file
```

### UI changes
- **Launch dialog:** "Patient ID:" text entry field (max 16 chars, alphanumeric + hyphen). Two buttons: "New Session" / "Open Existing…". Open Existing shows a file chooser filtered to `*.json` starting in `~/PhysioChart/`.
- **File tab:** "Save Session" (JSON), "Open Session", "Export Bundle" (all images + PDF — Phase 2E).
- **Auto-save:** Triggered when switching modes. Saves **everything** — JSON + all PNG images. Status line shows "Saved 10:42". Images must include sufficient padding so no edge content is clipped.

### Confirmed decisions for 2A
1. ✓ Folder per session — `~/PhysioChart/JB_01_05_2026_1430/`
2. ✓ Recent sessions list (not file picker) — compact list of past sessions in the launch dialog, tappable
3. ✓ Delete stroke: undo + erase tool sufficient; no additional 2A scope needed

---

## Phase 2B — Objective body chart

### Goal
A second full body chart for clinician-measured findings. Drawn zones (allodynia, hyperalgesia, erythema, temp asymmetry) use the same pressure-sensitive stroke engine with distinct colours/patterns. Point measurements (PPT, temporal summation) are tap-to-place with a numeric entry popover.

**Unlocks:** Region-anchored neuro testing (2C) can anchor to this chart's dermatome overlay.

### New files
- `src/obj_chart.c` — objective chart drawing, hit-testing, point entry popover
- `src/obj_chart.h`

### Existing files changed
| File | Change |
|------|--------|
| `src/canvas.h` | New enums + structs (see below); add obj arrays to AppState; add `AppMode` enum |
| `src/canvas.c` | Dispatch draw/erase/point-tap to obj canvas when `current_mode == MODE_OBJECTIVE` |
| `src/window.c` | Add top-level mode tab strip; obj-chart sidebar toolbar (zone type buttons + point tool) |
| `src/persistence.c` | Serialise/deserialise obj_zones and obj_points |

### Key new structs/enums

```c
// canvas.h additions

typedef enum {
    APP_MODE_SUBJECTIVE = 0,
    APP_MODE_OBJECTIVE,
    APP_MODE_REPORT,
    APP_MODE_COUNT
} AppMode;

typedef enum {
    OBJ_ZONE_ALLODYNIA = 0,   /* light touch → pain — yellow */
    OBJ_ZONE_HYPERALGESIA,    /* increased pain response — orange */
    OBJ_ZONE_ERYTHEMA,        /* visible redness — red/pink */
    OBJ_ZONE_TEMP_COOL,       /* cool asymmetry — blue */
    OBJ_ZONE_TEMP_WARM,       /* warm asymmetry — red */
    OBJ_ZONE_COUNT
    /* Add new types here — JSON version bump required */
} ObjZoneType;

typedef enum {
    OBJ_PT_PPT = 0,           /* pressure pain threshold — kPa or kg/cm² */
    OBJ_PT_TEMPORAL_SUM,      /* temporal summation — NRS 0-10 */
    OBJ_PT_COUNT
} ObjPointType;

typedef struct {
    StrokePoint *pts;
    size_t       n_pts, cap;
    ObjZoneType  type;
    int          view;
    int          wide_mode;
} ObjZone;

typedef struct {
    ObjZone **zones;
    int       n, cap;
} ObjZoneList;

#define MAX_OBJ_POINTS 100

typedef struct {
    ObjPointType type;
    int          view;
    double       bx, by;
    float        value;
    char         unit[8];   /* "kPa", "kg", "NRS" */
    char         label[32]; /* rendered near point, e.g. "PPT 250kPa" */
} ObjPoint;

// AppState additions:
//   AppMode      current_mode;
//   ObjZoneList *obj_zones;
//   ObjPoint     obj_points[MAX_OBJ_POINTS];
//   int          obj_point_count;
//   ActiveTool   obj_tool;     /* draw / erase / point-measure */
//   ObjZoneType  obj_zone_type;
//   ObjPointType obj_point_type;
//   Stroke      *obj_active_zone;  /* in-progress draw */
```

### ObjZoneDef colour table (analogous to SYMPTOM_DEFS)

| Type | Colour | Pattern | Opacity |
|------|--------|---------|---------|
| Allodynia | Yellow `#F5D100` | Dots spaced | 60% |
| Hyperalgesia | Orange `#F07820` | X marks | 60% |
| Erythema | Pink `#E8607A` | Solid fill | 45% |
| Temp cool | Cyan-blue `#40A0E0` | H-strokes | 60% |
| Temp warm | Deep red `#C03030` | H-strokes | 60% |

### UI changes
- **Mode tab strip** (top of main area): `[ Subjective ]  [ Objective ]  [ Report ]`
- **Objective sidebar:** Zone type buttons (5 types, same 2-col grid pattern as symptom buttons), Point tool button, Erase button, Wide-mode toggle
- **Point entry popover:** On point-tool tap, a small GTK popover appears at screen position with: label showing type + unit, spin button for value, Confirm / Cancel buttons. Works with keyboard (Tab to confirm) and stylus (tap Confirm).
- **Point rendering:** Small coloured dot at body position + `label` text in a small box (same screen-space rendering as note labels, but smaller — ~11px)
- **Overlay:** Dermatome overlay available on objective chart (needed for region-anchored neuro in 2C)

### Confirmed decisions for 2B
1. ✓ Zone colours/patterns confirmed as specified in table above
2. ✓ Separate undo stack per mode — Subjective, Objective, and Report each have independent undo
3. Point labels: TBD before starting 2B
4. PPT unit: TBD before starting 2B

---

## Phase 2C — Neurological testing module

### Goal
Structured neuro assessment linked to the objective body chart. Standalone form covers sensation/power/reflexes per spinal level with MRC/standard grading. Region-anchored: tap a dermatome region on the objective chart to jump to that level in the form.

### New files
- `src/neuro.c` — NeuroData management, form widget, dermatome centroid table
- `src/neuro.h`

### Existing files changed
| File | Change |
|------|--------|
| `src/canvas.h` | Add `NeuroData neuro` to AppState |
| `src/window.c` | Neuro button in objective sidebar; panel/window creation |
| `src/canvas.c` | On tap in objective chart with neuro-link mode active: call `neuro_focus_level(level_name)` |
| `src/overlay_data/dermatomes.c` | Add centroid table (bx, by per level per view) for tap-to-level mapping |
| `src/persistence.c` | Serialise/deserialise NeuroData |

### Key new structs/enums

```c
// neuro.h

typedef enum { SENS_NORMAL=0, SENS_REDUCED, SENS_ABSENT, SENS_HYPERAESTH, SENS_COUNT } SensGrade;
typedef enum { PWR_0=0, PWR_1, PWR_2, PWR_3, PWR_4, PWR_5, PWR_COUNT } PowerGrade;
typedef enum { REF_ABSENT=0, REF_REDUCED, REF_NORMAL, REF_BRISK, REF_CLONUS, REF_COUNT } ReflexGrade;

typedef struct {
    char        level[6];      /* "C5", "L4", etc. */
    SensGrade   sens_l, sens_r;
    PowerGrade  pwr_l,  pwr_r;
    ReflexGrade ref_l,  ref_r;
    char        notes[64];
    gboolean    tested;        /* row is populated */
} NeuroLevel;

#define NEURO_LEVELS_MAX 30

typedef struct {
    NeuroLevel levels[NEURO_LEVELS_MAX];
    int        n_levels;
    /* UMN signs */
    gboolean   babinski_l, babinski_r;
    gboolean   hyperreflexia, spasticity, clonus;
    char       umn_notes[128];
    /* LMN signs */
    gboolean   fasciculations, wasting, hypotonia;
    char       lmn_notes[128];
} NeuroData;

/* Centroid entry for tap-to-level mapping */
typedef struct {
    const char *level;   /* "L4" */
    int         view;    /* BodyView */
    float       bx, by;  /* body-space centroid */
} DermCentroid;

extern const DermCentroid DERM_CENTROIDS[];
extern const int          DERM_CENTROID_COUNT;

/* Find nearest level to a tap point; returns level name or NULL */
const char *neuro_level_from_tap(int view, double bx, double by);
```

### Default levels (curated shortlist)
`C5, C6, C7, C8, T1, L2, L3, L4, L5, S1` — 10 rows pre-populated. User can add any C2–S4 level.

### Grade grids (shown as clickable button rows, not combo boxes)

**Sensation:** `Norm | ↓ | Absent | ↑ (hyperaesth.)`  
**Power (MRC):** `0 | 1 | 2 | 3 | 4 | 5`  
**Reflex:** `0 | + | ++ | +++ | Clonus`

Each cell is a toggle button; tapping cycles or directly selects. Works well with stylus.

### Test hints
Column header for each test type has a small `?` button that opens a `GtkPopover` with:
- **Sensation:** "Light touch (cotton), pinprick, vibration (128Hz). Grade: Normal / Reduced / Absent / Hyperaesthetic"
- **Power (MRC):** "0=No contraction. 1=Flicker. 2=Active movement, gravity eliminated. 3=Against gravity. 4=Against resistance. 5=Normal."
- **Reflex:** "Use tendon hammer. 0=Absent. +=Reduced. ++=Normal. +++=Brisk. Clonus=≥3 beats."

### UI layout (neuro panel)

```
┌─────────────────────────────────────────────────────────────────┐
│ NEUROLOGICAL ASSESSMENT                          [+Add Level]   │
├──────┬───────────────────┬───────────────────┬────────────────-─┤
│Level │ Sensation L / R   │ Power L / R       │ Reflex L/R Notes │
├──────┼───────────────────┼───────────────────┼──────────────────┤
│  C5  │ [N][↓][Ab][↑] ... │ [0][1][2][3][4][5]│ ...              │
│  L4  │ ...               │ ...               │ ...              │
├──────┴───────────────────┴───────────────────┴──────────────────┤
│ UMN SIGNS                                                        │
│ [Babinski L] [Babinski R] [Hyperreflexia] [Spasticity] [Clonus] │
│ Notes: ___________                                               │
│ LMN SIGNS                                                        │
│ [Fasciculations] [Wasting] [Hypotonia]                          │
│ Notes: ___________                                               │
└─────────────────────────────────────────────────────────────────┘
```

### ⚠ Decisions needed before starting
1. Panel location: floating window, or a docked panel below the objective canvas? (Floating is simpler; docked is more integrated but constrains screen space on 11e.)
2. Which views show dermatome centroids (anterior and posterior, or all four)?
3. Tap-to-level only activates when dermatome overlay is visible, or always on objective chart?
4. Should UMN/LMN section be in the same panel or a second tab within the neuro panel?

---

## Phase 2D — Report/summary editor

### Goal
A TUI-aesthetic text editor (monospace, dark) with auto-generated sections from all chart data. Sections can be regenerated; manual additions are preserved. Some structured quick-entry widgets above the text view.

### New files
- `src/report.c` — auto-generation logic, GtkTextView setup
- `src/report.h`

### Existing files changed
| File | Change |
|------|--------|
| `src/canvas.h` | Add `ReportData report` to AppState |
| `src/window.c` | Report tab content construction |
| `src/persistence.c` | Save/load `report.text` in JSON |

### Key new structs

```c
// report.h
#define REPORT_TEXT_MAX (64 * 1024)

typedef struct {
    char text[REPORT_TEXT_MAX];
} ReportData;

void report_generate(AppState *app);  /* writes auto-sections into report.text */
```

### Auto-generated section format

```
SUBJECTIVE CHART
════════════════
Symptom types drawn: Constant pain (anterior, posterior), Paraesthesia (anterior)
Annotations: 2 notes
  (1) Con Sup Pain 3/7
  (2) Int Deep Ache 5/8
Arrows: 1

OBJECTIVE CHART
════════════════
Zones: Allodynia (anterior medial knee), Hyperalgesia (posterior L4 region)
Point measurements:
  PPT 220kPa @ anterior medial knee
  PPT 180kPa @ posterior L4 region
  Temporal summation NRS 6 @ anterior medial knee

NEUROLOGICAL ASSESSMENT
════════════════════════
Level  Sens L/R   Power L/R  Reflex L/R
C6     N / ↓      5 / 4      ++ / ++
L4     N / N      5 / 5      ++ / +
L5     N / ↓      5 / 3      - / -
UMN signs: None
LMN signs: None

CLINICAL NOTES
════════════════
[cursor here — free text]
```

### CSS (TUI aesthetic)

```css
.report-view {
    font-family: "Monospace", "Courier New", monospace;
    font-size: 13px;
    background-color: #12121e;
    color: #d0d0e8;
    padding: 16px;
    caret-color: #ffcc44;
}
.report-header {
    color: #ffcc44;
    font-weight: bold;
}
.report-auto {
    color: #7070a0;   /* muted — auto-generated text */
}
.report-divider {
    color: #404060;
}
```

### Header bar widgets
```
[ ↺ Regenerate Summary ]  [ ☐ Subjective ] [ ☐ Objective ] [ ☐ Neuro ]  [ ⎘ Copy All ]
```
Toggles control which sections appear in the auto-generated block.

### ⚠ Decisions needed before starting
1. Should "Regenerate" replace only auto-tagged ranges (preserving manual text between them) or replace the whole buffer?
2. Should the text be saved in the JSON session file, or as a separate `{session_name}_report.txt`? (Recommendation: both — in JSON for reload, as .txt for human readability.)
3. Should the report section have its own sidebar, or is the header bar sufficient?

---

## Phase 2E — Export bundle refactor

### Goal
Named export bundle: all components saved together under a shared patient-derived base name. `session_save` is now the JSON; render exports are "Export Bundle".

### Existing files changed
| File | Change |
|------|--------|
| `src/session.c` | Full refactor: rename `session_save` → `session_save_json`; add `session_load_json`; add `session_export_bundle`; keep existing PNG/PDF/SVG render helpers |
| `src/session.h` | Updated declarations |
| `src/window.c` | File tab: "Save Session" (JSON), "Export Bundle" (all formats) |
| `src/persistence.c` | `persistence_save` / `persistence_load` called by session.c |

### Bundle output (patient "JB", 01 May 2026 14:30)

```
~/PhysioChart/JB_01_05_2026_1430/
    JB_01_05_2026_1430_session.json   ← native save (editable)
    JB_01_05_2026_1430_subj.png       ← subjective chart render
    JB_01_05_2026_1430_obj.png        ← objective chart render
    JB_01_05_2026_1430_report.txt     ← report text (plain)
    JB_01_05_2026_1430.pdf            ← multi-page: p1=subj, p2=obj, p3=report
```

### session_export_bundle logic

```c
gboolean session_export_bundle(AppState *app) {
    // 1. Ensure session folder exists
    // 2. session_save_json(app, path_json)
    // 3. session_export_png_subj(app, path_subj_png)   — subjective only
    // 4. session_export_png_obj(app, path_obj_png)     — objective only
    // 5. write report text to path_report_txt
    // 6. session_export_pdf_bundle(app, path_pdf)       — multi-page
}
```

### Confirmed decisions for 2E
1. ✓ Folder per session — `~/PhysioChart/JB_01_05_2026_1430/`
2. ✓ Auto-save writes JSON + all PNGs. PDF bundle only on explicit Export button.
3. ✓ PDF page order: subjective → objective → report (fixed)
4. ✓ PNG exports must include 5% margin on all sides to prevent edge content clipping

---

## Implementation sequence recommendation

```
2A → 2B → 2C → 2D → 2E
```

But within each phase, build in this sub-order:
1. Data structs + JSON schema first (so persistence works from day one)
2. Rendering / canvas integration second
3. UI (toolbar, wizards, panels) third
4. Polish (CSS, keyboard shortcuts, edge cases) last

---

## Files to be created (summary)

| File | Phase | Purpose |
|------|-------|---------|
| `src/persistence.c/.h` | 2A | JSON save/load for all AppState data |
| `src/obj_chart.c/.h` | 2B | Objective chart drawing, point entry |
| `src/neuro.c/.h` | 2C | Neuro form, grading, centroid table |
| `src/report.c/.h` | 2D | Report auto-generation, text editor setup |

Existing source file change summary:

| File | Phases that touch it |
|------|----------------------|
| `src/canvas.h` | 2A, 2B, 2C, 2D |
| `src/canvas.c` | 2B, 2C |
| `src/window.c` | 2A, 2B, 2C, 2D, 2E |
| `src/session.c` | 2A, 2E |
| `src/session.h` | 2A, 2E |
| `src/main.c` | 2A |
| `src/overlay_data/dermatomes.c` | 2C |

---

## Open questions (not blocking but worth deciding)

- **Barrel button on objective chart:** should it cycle ObjZoneType (like it cycles SymptomType on subj chart)?
- **Overlay on objective chart:** show dermatome overlay by default when opening objective tab?
- **Wide mode for objective zones:** same toggle as subjective, or separate setting?
- **Temporal summation protocol hint:** show number of stimuli / interval as a test hint?
- **Report font size:** 13px is comfortable on a laptop; on the 11e Thinkpad screen it may need to be larger.
