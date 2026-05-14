# Customising the Assessment Form

This guide explains how to add, remove, or modify fields in the TUI assessment form without AI assistance. It covers the full data flow from UI widget → JSON storage → session file.

---

## Overview: How a Field Works

```
compose()          → widget appears on screen
FieldChanged msg   → triggers auto-save (2s debounce in assessment_view.py)
collect()          → gathers all field values into a dict
save_all_sections()→ writes dict to _assessment.json
load()             → on session open, reads dict back and populates widgets
```

---

## Field Types

### CheckButton — toggle (blank → Yes/green → No/red)

Defined in `widgets.py`. Use for neutral yes/no questions:

```python
from ..widgets import CheckButton

yield CheckButton("Is this present?", id="my_field_id")
```

Reading in `collect()`:
```python
data["my_field_id"] = self.query_one("#my_field_id", CheckButton).value
# Returns: True, False, or None (not yet answered)
```

Loading in `load()`:
```python
self.query_one("#my_field_id", CheckButton).set_value(data.get("my_field_id"))
```

### FlagButton — toggle (blank → Yes/**red**/danger → No/green/safe)

Subclass of CheckButton. Use for clinically concerning findings where YES = bad:

```python
from ..widgets import FlagButton

yield FlagButton("Red flag present?", id="rf_my_flag")
```

`collect()` and `load()` are identical to CheckButton — `FlagButton` is a subclass so `query_one("#id", CheckButton)` finds it.

### LikelihoodField — None → Low → Moderate → High cycling

Defined in `sections/medical.py`. Import it:

```python
from .medical import LikelihoodField

yield LikelihoodField("Likelihood:", field_id="my_likelihood")
```

Reading: `self.query_one("#my_likelihood", LikelihoodField).get_value()` → str or None
Loading: `self.query_one("#my_likelihood", LikelihoodField).set_value(data.get("my_likelihood"))`

### CycleField — multi-option cycling button

Defined in `sections/outcome_measures.py`:

```python
from .outcome_measures import CycleField

yield CycleField(["Option A", "Option B", "Option C"], id="my_cycle_field")
```

Reading/loading: same pattern — `get_value()` / `set_value(val)`.

### Input — single line text

```python
yield Input(placeholder="Enter value...", id="my_input_id")
```

Collect: `self.query_one("#my_input_id", Input).value`
Load: `self.query_one("#my_input_id", Input).value = data.get("my_input_id", "")`

### TextArea — multi-line text (auto-expanding)

Always use this instead of Input for anything multi-sentence:

```python
yield TextArea(id="my_text_id", language="plain")
```

Collect: `self.query_one("#my_text_id", TextArea).text`
Load: `self.query_one("#my_text_id", TextArea).text = data.get("my_text_id", "")`

CSS:
```css
#my_text_id { height: auto; min-height: 2; padding: 0 1; }
```

---

## Standard Layout Patterns

### Label + field on one row (field_row)

```python
with Horizontal(classes="field_row"):
    yield Label("My label\n(second line):")
    yield TextArea(id="my_text", language="plain")
```

CSS required in section DEFAULT_CSS:
```css
.field_row { height: auto; width: 100%; margin: 0; padding: 0; }
.field_row Label { width: 28; height: auto; padding: 0 1 0 0; }
.field_row TextArea { width: 1fr; height: auto; min-height: 2; padding: 0 1; }
```

### Button groups (btn_row) — up to 5 across

```python
with Horizontal(classes="btn_row"):
    yield CheckButton("Option A", id="opt_a")
    yield CheckButton("Option B", id="opt_b")
    yield CheckButton("Option C", id="opt_c")
```

```css
.btn_row { height: auto; width: 100%; margin-bottom: 1; }
CheckButton { width: auto; height: 3; min-width: 16; margin: 0 1 0 0; }
```

### Standalone full-width button

```python
yield CheckButton("This statement is confirmed", id="confirmed_btn", classes="solo_btn")
```

```css
.solo_btn { margin-bottom: 0; }
```

---

## CSS Rules for Sections

Every rebuilt section must have these in DEFAULT_CSS:

```css
MySection {
    width: 100%;
    height: auto;       ← CRITICAL: never height: 100%
    padding: 0 1;
}

.section_title     { text-style: bold; color: $text; margin-bottom: 0; }
.subsection_header { text-style: bold; color: $primary; margin-top: 1; margin-bottom: 0; }
.subgroup_header   { color: $text-muted; margin-top: 1; margin-bottom: 0; text-style: italic; }
```

**⚠ Critical: any `Vertical` container needs `height: auto`**

`Vertical` defaults to `height: 1fr` which collapses to zero inside a `height: auto` parent.
Always add explicitly:
```css
#my_table { height: auto; width: 100%; }
```

---

## Registering Fields in collect() / load()

```python
_TOGGLE_FIELDS = ["field_a", "field_b"]
_TEXT_FIELDS   = ["text_a", "text_b"]

def collect(self) -> dict:
    data = {}
    for fid in self._TOGGLE_FIELDS:
        try:
            data[fid] = self.query_one(f"#{fid}", CheckButton).value
        except Exception:
            data[fid] = None
    for fid in self._TEXT_FIELDS:
        try:
            data[fid] = self.query_one(f"#{fid}", TextArea).text
        except Exception:
            data[fid] = ""
    return data

def load(self, data: dict) -> None:
    self._loading = True
    try:
        for fid in self._TOGGLE_FIELDS:
            if fid in data:
                try:
                    self.query_one(f"#{fid}", CheckButton).set_value(data[fid])
                except Exception:
                    pass
        for fid in self._TEXT_FIELDS:
            if fid in data:
                try:
                    self.query_one(f"#{fid}", TextArea).text = data[fid]
                except Exception:
                    pass
    finally:
        self._loading = False
```

**⚠ load() receives the pre-extracted section dict — never call `.get("section_key")` inside load().**

---

## Auto-Save Trigger

```python
from ..widgets import CheckButton, FlagButton
from textual.message import Message

@on(CheckButton.Changed)   # catches both CheckButton and FlagButton
@on(Input.Changed)
@on(TextArea.Changed)
def _on_field_changed(self) -> None:
    if self._loading:
        return
    self.post_message(self.FieldChanged())

class FieldChanged(Message):
    pass
```

---

## Jump-to-Subsection (_jump_to)

```python
from textual.containers import ScrollableContainer

def _jump_to(self, anchor_id: str) -> None:
    try:
        target = self.query_one(f"#{anchor_id}")
        self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(
            target, top=True
        )
    except Exception:
        pass
```

Subsection headers act as anchors:
```python
yield Label("— My Subsection —", classes="subsection_header", id="my_anchor")
```

To wire the top chrome nav bar for a new section, see `SubsectionNavBar.set_context()` in `tui.py`.

---

## Field ID Naming Conventions

| Prefix | Meaning |
|--------|---------|
| `rf_`  | Red flag |
| `umn_` | Upper motor neurone sign |
| `cvd_` | Cardiovascular risk factor |
| `comorbid_` | Comorbidity |
| `diff_` | Differential screening |
| `b_`   | Main barrier (boolean) |
| `bx_`  | Barrier sub-item |
| `bi_`  | Barrier input (text/NRS) |
| `tx_`  | Treatment plan item |
| `dx_`  | Diagnosis field |

IDs must be **unique across the entire mounted widget tree**. Duplicate IDs cause runtime errors.

---

## is_complete()

```python
def is_complete(self) -> bool:
    try:
        return self.query_one("#required_field", CheckButton).value is not None
    except Exception:
        return False
```

---

## Quick Reference: Test Before Launch

```bash
cd ~/Projects/physio-bodychart/physio-assessment
.venv/bin/python3 -c "from physio_assessment.sections.medical import MedicalSection; print('OK')"
```
