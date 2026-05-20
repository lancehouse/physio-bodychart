"""YamlSubsection — a subsection widget built dynamically from a SubsectionDef."""

from __future__ import annotations
from pathlib import Path
from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Label, Input, TextArea

from .form_schema import SubsectionDef, FieldDef, load_subsection_yaml
from .widgets import RadioGroup
from .logic import calc_sleep_efficiency

_FORMULA_REGISTRY: dict[str, Callable] = {
    "calc_sleep_efficiency": calc_sleep_efficiency,
}


class YamlSubsection(Container):
    """Renders one subsection (header + fields) from a SubsectionDef.

    All widget events (Input.Changed, TextArea.Changed, RadioGroup.Changed)
    bubble up naturally to the parent section's _on_field_changed handler.
    The parent must include RadioGroup.Changed in its @on decorators.

    collect() returns a flat dict of {field_id: value}.
    load(data) sets every widget from a flat dict.
    calculated fields are never persisted — always recomputed (TODO).
    """

    DEFAULT_CSS = """
    YamlSubsection {
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, defn: SubsectionDef, **kwargs) -> None:
        super().__init__(**kwargs)
        self._def = defn
        self._loading = False

        # value↔label translation for radio fields
        # RadioGroup stores/returns the label string; YAML gives a stable value token.
        self._v2l: dict[str, dict[str, str]] = {}   # field_id → {value: label}
        self._l2v: dict[str, dict[str, str]] = {}   # field_id → {label: value}
        for f in defn.fields:
            if f.type == "radio" and f.options:
                self._v2l[f.id] = {o.value: o.label for o in f.options}
                self._l2v[f.id] = {o.label: o.value for o in f.options}

    @classmethod
    def from_yaml(cls, path: Path | str, **kwargs) -> "YamlSubsection":
        return cls(load_subsection_yaml(path), **kwargs)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        f: FieldDef
        yield Label(
            f"— {self._def.label} —",
            classes="subsection_header",
            id=self._def.id,
        )
        for f in self._def.fields:
            if f.type == "text_area":
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield TextArea(id=f.id, language="plain")

            elif f.type == "input":
                lbl = f.label + ("\n(duration)" if f.time_kind == "duration" else "")
                with Horizontal(classes="field_row"):
                    yield Label(f"{lbl}:")
                    yield Input(id=f.id, placeholder=f.placeholder)

            elif f.type == "radio":
                opts = [(o.label, o.variant) for o in f.options]
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield RadioGroup(options=opts, id=f.id)

            elif f.type == "calculated":
                ph = f"— {f.unit}" if f.unit else "—"
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield Input(id=f.id, placeholder=ph, disabled=True)

    # ------------------------------------------------------------------
    # Calculated fields
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._loading:
            return
        # Ignore programmatic updates to calculated-field widgets
        fid = event.input.id
        if any(f.id == fid and f.type == "calculated" for f in self._def.fields):
            return
        self._recompute_calculated()

    def _recompute_calculated(self) -> None:
        for f in self._def.fields:
            if f.type != "calculated" or not f.formula_fn:
                continue
            fn = _FORMULA_REGISTRY.get(f.formula_fn)
            if fn is None:
                continue
            kwargs: dict[str, str] = {}
            for inp_id in f.inputs:
                inp_f = next((x for x in self._def.fields if x.id == inp_id), None)
                if inp_f is None:
                    continue
                try:
                    if inp_f.type == "input":
                        kwargs[inp_id] = self.query_one(f"#{inp_id}", Input).value
                    elif inp_f.type == "text_area":
                        kwargs[inp_id] = self.query_one(f"#{inp_id}", TextArea).text
                    elif inp_f.type == "radio":
                        lbl = self.query_one(f"#{inp_id}", RadioGroup).value
                        kwargs[inp_id] = self._l2v[inp_id].get(lbl, "") if lbl else ""
                except Exception:
                    kwargs[inp_id] = ""
            try:
                result = fn(**kwargs)
                self.query_one(f"#{f.id}", Input).value = result
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data: dict = {}
        for f in self._def.fields:
            try:
                if f.type == "text_area":
                    data[f.id] = self.query_one(f"#{f.id}", TextArea).text
                elif f.type in ("input", "calculated"):
                    data[f.id] = self.query_one(f"#{f.id}", Input).value
                elif f.type == "radio":
                    lbl = self.query_one(f"#{f.id}", RadioGroup).value
                    data[f.id] = self._l2v[f.id].get(lbl) if lbl else None
            except Exception:
                data[f.id] = None if f.type == "radio" else ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for f in self._def.fields:
                if f.type == "calculated":
                    continue  # recomputed live; don't load stale value
                val = data.get(f.id)
                try:
                    if f.type == "text_area":
                        self.query_one(f"#{f.id}", TextArea).text = val or ""
                    elif f.type == "input":
                        self.query_one(f"#{f.id}", Input).value = val or ""
                    elif f.type == "radio":
                        lbl = self._v2l[f.id].get(val) if val else None
                        self.query_one(f"#{f.id}", RadioGroup).set_value(lbl)
                except Exception:
                    pass
        finally:
            self._loading = False
            self._recompute_calculated()
