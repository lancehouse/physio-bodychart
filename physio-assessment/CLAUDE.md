# PhysioAssessment — Textual TUI

See `../CLAUDE.md` for the full two-app architecture and shared file format.

## Environment

```bash
cd physio-assessment
source .venv/bin/activate      # Python 3.12 venv — always activate before running
python -m physio_assessment    # launch TUI
```

Never use system Python. The venv must be Python 3.12.

## Source layout

```
physio_assessment/
  main.py                  Entry point — Textual App, session list screen
  tui.py                   Session list screen widget
  assessment_view.py       Main assessment container: section nav, autosave, load/save orchestration
  storage.py               All JSON I/O, report generation — no Textual imports
  watcher.py               File watcher for _session.json (GTK live updates)
  widgets.py               Shared clinical widgets (see Widget catalogue below)
  models.py                Lightweight dataclasses for session/patient identity (not Pydantic)
  logic.py                 Clinical calculations (BMI, score tallies) — no UI imports

  sections/                Assessment sections 01–07 + scratchpad
    base.py                BaseSection — _loading flag, session_file attr
    consent.py             01 Consent & ICE+
    subjective.py          02 Subjective Examination
    medical.py             03 Medical Screening (red flags, comorbidities)
    pain_classification.py 04 Pain Classification
    outcome_measures.py    05 Outcome Measures
    diagnosis.py           06 Diagnosis & Goals
    barriers.py            07 Barriers & Treatment Plan
    scratchpad.py          Free-text working area
    objective.py           Stub / bridge to objective mode

  objective/
    objective_view.py      Objective sidebar nav (replaces section_nav in obj mode)
    sections/
      base.py              Same BaseSection as assessment sections
      general.py           01 General Observation
      active_movement.py   02 Active Movement (ROM — ROMRow, RangeCell)
      passive_movement.py  03 Passive Movement & Overpressure (OP + PAIVM grid)
      neurological.py      04 Neurological (reflexes, myotomes, neurodynamics, UMN)
      sensory.py           05 Sensory (dermatomes, hypo/hypersensitivity)
      muscle.py            06 Muscle Testing (length, activation, strength, SIJ)
      functional.py        07 Functional (movement obs, balance, timed capability)
```

## Data files (per session)

All in `~/Physio-Bodychart/<session-name>/`:

| File | Owner | Contains |
|---|---|---|
| `*_session.json` | GTK | Patient identity, body chart strokes, regions |
| `*_assessment.json` | TUI | Sections 01–07 assessment data + `sections_complete` |
| `*_objective.json` | TUI | Objective sections 01–07 data + `sections_complete` |
| `*_report.md` | TUI | Compact Markdown clinical report (regenerated on save) |
| `*_raw.txt` | TUI | Full plain-text export of every field (regenerated on save) |

**Human-readable format is permanent.** Do not introduce binary formats or databases.

## Widget catalogue (`widgets.py`)

| Widget | Base | Behaviour |
|---|---|---|
| `CheckButton` | `Button` | 3-state: blank/orange → Yes/green → No/red. Y/N keys set state + advance focus. Use for positive-good questions. |
| `FlagButton` | `CheckButton` | Same cycle, reversed colours: Yes=red (danger), No=green (safe). Use for red-flag screening. |
| `CycleButton` | `Static` | Click cycles through `(label, variant)` state pairs. Inner Button gets `id=f"{self.id}_btn"`. Default `width: 25%`. States prepend `(None, "default")` as blank. |
| `GridInput` | `Input` | Posts `GridInput.Navigate(direction)` at cursor boundaries (up/down always; left at pos 0; right at end of value) for arrow-key grid navigation. |
| `YesNoField` | `Container` | Legacy label + toggle button. New sections use `CheckButton` directly. |
| `RadioGroup` | `Static` | **Single-select gang.** Compact row of mutually-exclusive buttons, each exactly 6 cells wide × 3 rows tall, `padding: 0; border: none` (all 6 chars for label). `can_focus=True` on the group; inner `_RadioButton`s have `can_focus=False` — whole gang is one tab stop. Left/Right selects within. Enter/Space/Y advances to next field. Click/tap selects; re-click deselects. options: `list[tuple[label, variant]]`. |

### CycleButton rules
- Outer `Static` carries the data key via its `id=`. Use `cb.id` in `collect()` / `load()`.
- Inner button ID is `f"{self.id}_btn"` — used by grid-nav code to track focus.
- `collect()`: `for cb in self.query(CycleButton): data[cb.id] = cb.value`
- `load()`: `for cb in self.query(CycleButton): cb.set_value(data.get(cb.id))`

### RadioGroup — "gang" rules

A **gang** is a compact row of mutually-exclusive option buttons treated as one integrated widget.

**Two types:**
- **Single-select gang** = `RadioGroup` (built). One option active at a time.
- **Multiselect gang** = not yet built. Same layout; multiple options active; Enter/Space/Y does NOT auto-advance.

**Sizing — non-negotiable:**
- Each button: exactly `width: 6; padding: 0; border: none` — all 6 chars are content, no border buffer.
- Height: 3 rows. Total gang width = N × 6 columns (e.g. 4-button gang = 24 cols, 5-button = 30 cols).
- Labels must be ≤ 6 chars. Abbreviate as needed. The stored value IS the label string — keep abbreviations stable across sessions.
- Labels do not need a full surrounding border. One visual edge from adjacent colour contrast is sufficient.

**Keyboard / interaction:**
- The outer `RadioGroup` has `can_focus = True`; inner `_RadioButton`s have `can_focus = False`.
- The whole gang is **one tab stop** — Tab enters the gang, Tab again leaves it.
- Left / Right arrows move selection within the gang.
- Enter / Space / Y → advance focus to the next field (selection already set by arrows).
- Click / tap → select that button; focus returns to the gang.
- Click an already-selected button → **deselects** it (clears to no selection).

**collect / load pattern:**
```python
for rg in self.query(RadioGroup): data[rg.id] = rg.value   # collect
for rg in self.query(RadioGroup): rg.set_value(data.get(rg.id))  # load
```
- Also add `@on(RadioGroup.Changed)` to the section's `_on_field_changed` handler.
- Import: `from ...widgets import RadioGroup`

**Standard abbreviated option sets (general.py reference):**
```python
_SEV4  = [("Norm","success"),("Mild","warning"),("Mod","error"),("Sev","error")]
_FUNC3 = [("Norm","success"),("Reduc","warning"),("Unable","error")]
_GAIT3 = [("Norm","success"),("Antlgc","warning"),("Anlgsc","default")]
_LORD4 = [("Norm","success"),("↑Inc","warning"),("↓Dec","warning"),("Absnt","error")]
_KYPH3 = [("Norm","success"),("↑Inc","warning"),("↓Dec","warning")]
_LEAN4 = [("None","success"),("Left","warning"),("Right","warning"),("Fwd","default")]
_BRTH3 = [("Norm","success"),("Apical","warning"),("Paradx","error")]
```

## Section pattern (BaseSection subclass)

Every section follows this exact pattern:

```python
class MySection(BaseSection):
    class FieldChanged(Message): pass

    def compose(self) -> ComposeResult: ...        # yield widgets

    def on_mount(self) -> None: ...                # build grid if needed

    @on(CycleButton.Changed)
    @on(CheckButton.Changed)
    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if not self._loading:                      # ALWAYS guard with _loading
            self.post_message(self.FieldChanged())

    def collect(self) -> dict: ...                 # return all field values as dict
    def load(self, data: dict) -> None: ...        # set widgets from dict
    def is_complete(self) -> bool: ...             # True if key field(s) filled
```

### Save/load integrity rules — critical

- **`load()` MUST set `self._loading = True` before touching any widget, and restore it in
  `finally`.** Without this, every widget assignment triggers autosave.
- **Never extract data from `data` inside `load()` using the wrong key.** The bug pattern is
  iterating `(label, id)` tuples as `for id, label in` — swapped unpacking silently stores
  data under label strings, causing silent data loss. Always verify tuple order.
- **`collect()` must be the mirror of `load()`.** Same fields, same keys, no omissions.
- After any new field is added to `compose()`, add it to both `collect()` and `load()`.

## Autosave flow

```
Field widget changed
  → section posts FieldChanged message
    → assessment_view.py on_{section}_field_changed() → _schedule_save()
      → 1.5s debounce → _do_save()
        → each section.collect() → save_all_sections() → _assessment.json
        → each objective section.collect() → save_objective() → _objective.json
        → save_raw_report() → _raw.txt
```

Report handlers in `assessment_view.py` follow naming convention:
`on_{SectionClassName snake_case}_field_changed`

## Grid navigation pattern (bilateral table sections)

Sections with L/R table grids (active movement, neurological, sensory, muscle, functional):

```python
self._grid: list[list[str | None]]    # 2D list of widget IDs (None = empty cell)
self._grid_pos: dict[str, tuple[int, int]]  # widget ID → (row, col)
```

Built in `on_mount()`. `GridInput` posts `Navigate` at boundaries; `Button`/`CycleButton`
buttons use `on_key()` to catch arrow keys. Handler calls `_nav(direction, focused_id)`.

For `CycleButton` in grids: track the **inner button ID** (`f"{cb.id}_btn"`) in `_grid_pos`,
not the outer Static ID.

## Assessment sections — key field IDs

| Section | Key IDs (examples) |
|---|---|
| 01 Consent | `consent_to_proceed`, `preferred_name`, `reason_for_attending` |
| 02 Subjective | `history`, `nrs_current/best/worst`, `duration`, `onset` |
| 03 Medical | `rf_saddle_anaesthesia`, `rf_bladder_disturbance`, `comorbid_*` |
| 04 Pain Classification | `pain_type_*`, inflammatory/nociceptive/nociplastic feature flags |
| 05 Outcome Measures | Scored tables: PSEQ, CSI, PCL-5, DASS-21, PCS, ISI |
| 06 Diagnosis | `icd11_pathway`, `clinical_impression`, goal fields |
| 07 Barriers | `barrier_*` checkboxes, `tx_formulation`, `tx_program` |

## Objective sections — key field IDs

| Section | Key IDs (examples) |
|---|---|
| 01 General | `go_height`, `go_weight`, `go_bmi`, `go_lx_lord`, `go_gait` |
| 02 Active Movement | `lx_flex_ax_l_range`, `lx_flex_ax_l_ps`, `lx_lf_ax_r_range` … |
| 03 Passive/OP | `op_lx_flex_ef`, `op_lx_flex_resp`, `pm_L5_c`, `pm_L5_ul_l/r` |
| 04 Neurological | `nr_knee_l/r`, `nr_l2_l/r` … `nr_slr_l_deg`, `nr_umn_hyper` |
| 05 Sensory | `sn_l2_l/r` … `sn_sharp_blunt`, `sn_static_allodynia_detail` |
| 06 Muscle | `ml_ql_l/r`, `ma_tva`, `sh_hip_flex_l/r`, `sij_sacral` |
| 07 Functional | `ft_gait`, `ft_tug`, `ft_sls_eo_l/r`, `ft_bal_both` |

Active movement Pain/Stiff suffix: `_ps` field holds `None | "Pain" | "Stiff"`.
Bilateral ROM rows (Flexion, Extension): only `_l` variants exist — `_r` columns are empty.

## Report generation (`storage.py`)

- `export_session_report(session_file)` → writes `*_report.md` (compact Markdown)
- `save_raw_report(session_file)` → writes `*_raw.txt` (full plain-text, all fields)
- Both load `_session.json` + `_assessment.json` + `_objective.json` before rendering
- `_render_objective_md(obj)` / `_render_objective_raw(obj, lines, SEP, SEP2)` render
  bilateral data as aligned tables (L/R columns), not repeated label-per-side lines
- Called automatically from `_do_save()` — never call manually unless testing

## Planned — Phase 3 (not yet built)

Right-panel clinical knowledge base:
- `clinical_kb.db` — SQLite reference DB (read-only during sessions, clinician-editable)
- Tables: Region, ClinicalPattern, PatternFeature, SpecialTest, BodyChartTrigger
- Context engine in `logic.py`: `query_patterns()`, `query_tests()`, `score_pattern()`
- Special test widgets with Sn/Sp, collapsible how-to, result checkboxes
- Right panel updates when: region changes, body chart JSON changes, features ticked

Do not implement Phase 3 until explicitly requested. Current single-panel layout should
not be designed in a way that makes adding a right panel structurally difficult.
