"""Clinical Impression & ICD-11 Diagnosis section (core/06)."""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from .consent import YesNoField
from .outcome_measures import CycleField


# ---------------------------------------------------------------------------
# Option lists
# ---------------------------------------------------------------------------

_MECHANISM_OPTIONS = [
    ("No clear tissue cause",                     "warning"),
    ("After surgical procedure",                  "primary"),
    ("After traumatic tissue injury",             "primary"),
    ("Underlying disease / pathology",            "success"),
    ("Somatosensory nervous system lesion",       "warning"),
    ("Mixed / unable to determine",               "default"),
]

_SEVERITY_OPTIONS = [
    ("Mild",     "success"),
    ("Moderate", "warning"),
    ("Marked",   "error"),
]

_PRIMARY_SUBTYPE_OPTIONS = [
    ("Widespread pain / fibromyalgia",         "default"),
    ("CRPS type I",                            "default"),
    ("Chronic primary headache — migraine",    "default"),
    ("Chronic primary headache — tension type","default"),
    ("Chronic primary MSK — cervical",         "default"),
    ("Chronic primary MSK — thoracic",         "default"),
    ("Chronic primary MSK — lumbar",           "default"),
    ("Chronic primary MSK — limb",             "default"),
]

_SURGICAL_SUBTYPE_OPTIONS = [
    ("After amputation",      "default"),
    ("After spinal surgery",  "default"),
    ("After thoracotomy",     "default"),
    ("After breast surgery",  "default"),
    ("After herniotomy",      "default"),
    ("After hysterectomy",    "default"),
    ("After arthroplasty",    "default"),
]

_TRAUMATIC_SUBTYPE_OPTIONS = [
    ("After burns injury",            "default"),
    ("After peripheral nerve injury", "default"),
    ("After spinal cord injury",      "default"),
    ("After brain injury",            "default"),
    ("After whiplash injury",         "default"),
    ("After musculoskeletal injury",  "default"),
]

_MSK_SUBTYPE_OPTIONS = [
    ("Osteoarthritis",         "default"),
    ("Spondylosis",            "default"),
    ("Musculoskeletal injury", "default"),
]

_NEURO_SUBTYPE_OPTIONS = [
    ("Peripheral nerve injury", "default"),
    ("Painful radiculopathy",   "default"),
]

_MIXED_DOMINANT_OPTIONS = [
    ("Nociceptive",   "success"),
    ("Neuropathic",   "warning"),
    ("Nociplastic",   "error"),
    ("Indeterminate", "default"),
]


# ---------------------------------------------------------------------------
# Nav bar
# ---------------------------------------------------------------------------

class DxNavBar(Static):
    """Fixed navigation bar for Diagnosis section."""

    SUBSECTIONS = [
        ("Overview",    "dx_overview"),
        ("Primary",     "dx_primary"),
        ("Post-Surg",   "dx_surgical"),
        ("Post-Trauma", "dx_traumatic"),
        ("MSK",         "dx_msk"),
        ("Neuro",       "dx_neuropathic"),
        ("Mixed",       "dx_mixed"),
        ("Goals",       "dx_goals"),
    ]

    DEFAULT_CSS = """
    DxNavBar {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    DxNavBar Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    DxNavBar Button:hover { background: $accent; }
    """

    def __init__(self, on_jump_to: callable, **kwargs):
        super().__init__(**kwargs)
        self._on_jump_to = on_jump_to

    def compose(self) -> ComposeResult:
        for label, anchor_id in self.SUBSECTIONS:
            yield Button(label, id=f"nav_{anchor_id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid and bid.startswith("nav_"):
            self._on_jump_to(bid[4:])
        event.stop()


# ---------------------------------------------------------------------------
# DiagnosisSection
# ---------------------------------------------------------------------------

_CYCLE_FIELDS = [
    "mechanism",
    "primary_subtype", "primary_severity",
    "surgical_subtype", "surgical_severity",
    "traumatic_subtype", "traumatic_severity",
    "msk_subtype", "msk_severity",
    "neuro_subtype", "neuro_severity",
    "mixed_dominant",
]

_TOGGLE_FIELDS = [
    "duration_over_3_months",
    "primary_distress",
    "primary_not_other_dx",
]

_INPUT_FIELDS = [
    "surgical_procedure", "surgical_source",
    "traumatic_event", "traumatic_source",
    "msk_pathology", "msk_source",
    "neuro_lesion",
    "goal_1", "goal_2", "goal_3", "goal_4",
]

_TEXT_FIELDS = ["mixed_reasoning"]


class DiagnosisSection(BaseSection):
    """Clinical Impression & ICD-11 Diagnosis section (core/06)."""

    DEFAULT_CSS = """
    DiagnosisSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #dx_nav  { height: auto; }
    #dx_scroll { width: 100%; height: 1fr; }
    #dx_content { width: 100%; height: auto; padding: 0 1; }

    .section_title     { text-style: bold; margin-bottom: 0; }
    .subsection_header {
        text-style: bold; color: $primary;
        padding-top: 1; margin-bottom: 0;
    }
    .reference_note    { color: $text-muted; margin-bottom: 0; }

    Label  { margin-bottom: 0; }
    Input  { height: auto; min-height: 1; margin-bottom: 0; }
    TextArea { height: auto; min-height: 2; margin-bottom: 0; }

    .xref_badge {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $accent; background: $accent 12%;
    }
    """

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield DxNavBar(on_jump_to=self._jump_to, id="dx_nav")

        with ScrollableContainer(id="dx_scroll"):
            with Vertical(id="dx_content"):
                yield Label("Clinical Impression & ICD-11 Diagnosis", classes="section_title")

                # ── Pathway selection ──────────────────────────────────
                yield Label("— ICD-11 Pathway Selection —", classes="subsection_header", id="dx_overview")
                yield Label("(Nicholas et al 2019, Schug et al 2019, Perrot et al 2019, Scholz et al 2019)", classes="reference_note")

                yield YesNoField("Duration >3 months", field_id="duration_over_3_months")
                yield Static("", id="xref_dx_duration", classes="xref_badge")

                yield Label("Mechanism:")
                yield CycleField("mechanism", _MECHANISM_OPTIONS)
                yield Static("", id="xref_dx_mechanism", classes="xref_badge")

                # ── Chronic Primary Pain ───────────────────────────────
                yield Label("— Chronic Primary Pain —", classes="subsection_header", id="dx_primary")
                yield Label("(Nicholas et al 2019)", classes="reference_note")
                yield Static("", id="xref_dx_primary", classes="xref_badge")
                yield YesNoField("Significant emotional distress or functional limitation", field_id="primary_distress")
                yield YesNoField("Not better accounted for by another diagnosis",          field_id="primary_not_other_dx")
                yield Label("Subtype:")
                yield CycleField("primary_subtype", _PRIMARY_SUBTYPE_OPTIONS)
                yield Label("Severity:")
                yield CycleField("primary_severity", _SEVERITY_OPTIONS)
                yield Static("", id="xref_dx_primary_severity", classes="xref_badge")

                # ── Chronic Post-Surgical Pain ─────────────────────────
                yield Label("— Chronic Post-Surgical Pain —", classes="subsection_header", id="dx_surgical")
                yield Label("(Schug et al 2019)", classes="reference_note")
                yield Label("Surgical procedure:")
                yield Input(id="surgical_procedure", placeholder="procedure name")
                yield Label("Subtype:")
                yield CycleField("surgical_subtype", _SURGICAL_SUBTYPE_OPTIONS)
                yield Label("Most likely specific source:")
                yield Input(id="surgical_source", placeholder="source")
                yield Label("Severity:")
                yield CycleField("surgical_severity", _SEVERITY_OPTIONS)
                yield Static("", id="xref_dx_surgical_severity", classes="xref_badge")

                # ── Chronic Post-Traumatic Pain ────────────────────────
                yield Label("— Chronic Post-Traumatic Pain —", classes="subsection_header", id="dx_traumatic")
                yield Label("(Schug et al 2019)", classes="reference_note")
                yield Static("", id="xref_dx_traumatic", classes="xref_badge")
                yield Label("Traumatic event:")
                yield Input(id="traumatic_event", placeholder="describe event")
                yield Label("Subtype:")
                yield CycleField("traumatic_subtype", _TRAUMATIC_SUBTYPE_OPTIONS)
                yield Label("Most likely specific source:")
                yield Input(id="traumatic_source", placeholder="source")
                yield Label("Severity:")
                yield CycleField("traumatic_severity", _SEVERITY_OPTIONS)
                yield Static("", id="xref_dx_traumatic_severity", classes="xref_badge")

                # ── Chronic Secondary MSK Pain ─────────────────────────
                yield Label("— Chronic Secondary MSK Pain —", classes="subsection_header", id="dx_msk")
                yield Label("(Perrot et al 2019)", classes="reference_note")
                yield Label("Underlying disease / pathology:")
                yield Input(id="msk_pathology", placeholder="pathology")
                yield Label("Subtype:")
                yield CycleField("msk_subtype", _MSK_SUBTYPE_OPTIONS)
                yield Label("Most likely specific source:")
                yield Input(id="msk_source", placeholder="source")
                yield Label("Severity:")
                yield CycleField("msk_severity", _SEVERITY_OPTIONS)
                yield Static("", id="xref_dx_msk_severity", classes="xref_badge")

                # ── Chronic Neuropathic Pain ───────────────────────────
                yield Label("— Chronic Neuropathic Pain —", classes="subsection_header", id="dx_neuropathic")
                yield Label("(Scholz et al 2019)", classes="reference_note")
                yield Static("", id="xref_dx_neuropathic", classes="xref_badge")
                yield Label("Causative lesion / disease:")
                yield Input(id="neuro_lesion", placeholder="lesion or disease")
                yield Label("Subtype:")
                yield CycleField("neuro_subtype", _NEURO_SUBTYPE_OPTIONS)
                yield Label("Severity:")
                yield CycleField("neuro_severity", _SEVERITY_OPTIONS)
                yield Static("", id="xref_dx_neuro_severity", classes="xref_badge")

                # ── Mixed / Indeterminate ──────────────────────────────
                yield Label("— Mixed / Indeterminate —", classes="subsection_header", id="dx_mixed")
                yield Label("Dominant type if determinable:")
                yield CycleField("mixed_dominant", _MIXED_DOMINANT_OPTIONS)
                yield Label("Reasoning:")
                yield TextArea(id="mixed_reasoning", language="plain")

                # ── SMART Goals ────────────────────────────────────────
                yield Label("— SMART Goals —", classes="subsection_header", id="dx_goals")
                yield Label("Following completion of the assessment, the following potentially meaningful goals were confirmed:", classes="reference_note")
                yield Label("1.")
                yield Input(id="goal_1", placeholder="Goal 1")
                yield Label("2.")
                yield Input(id="goal_2", placeholder="Goal 2")
                yield Label("3.")
                yield Input(id="goal_3", placeholder="Goal 3")
                yield Label("4.")
                yield Input(id="goal_4", placeholder="Goal 4")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#dx_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Cross-reference badges
    # ------------------------------------------------------------------

    def update_cross_refs(self) -> None:
        """Read sibling section data from session JSON and update inline badges."""
        if not self.session_file:
            return
        try:
            data = json.loads(Path(self.session_file).read_text())
        except Exception:
            return

        med   = data.get("assessment", {}).get("medical", {})
        subj  = data.get("assessment", {}).get("subjective", {})
        pc    = data.get("assessment", {}).get("pain_classification", {})
        om    = data.get("assessment", {}).get("outcome_measures", {})

        def _set(badge_id: str, lines: list[str]) -> None:
            try:
                w = self.query_one(f"#{badge_id}", Static)
                if lines:
                    w.update("  ".join(f"◀ {l}" for l in lines))
                    w.display = True
                else:
                    w.display = False
            except Exception:
                pass

        # Duration — subjective duration text
        lines = []
        if subj.get("duration", "").strip():
            lines.append(f"Subj: duration — \"{subj['duration'].strip()[:80]}\"")
        _set("xref_dx_duration", lines)

        # Mechanism — dominant pain type from pain classification
        lines = []
        dominant = pc.get("summary_dominant")
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        _set("xref_dx_mechanism", lines)

        # Primary — fibromyalgia comorbidity
        lines = []
        if med.get("comorbid_fibromyalgia") is True:
            lines.append("Med: fibromyalgia (comorbidity) — consider Widespread pain subtype")
        _set("xref_dx_primary", lines)

        # Severity hint from PSFS interpretation (same Mild/Moderate/Marked scale)
        severity_badge_ids = [
            "xref_dx_primary_severity",
            "xref_dx_surgical_severity",
            "xref_dx_traumatic_severity",
            "xref_dx_msk_severity",
            "xref_dx_neuro_severity",
        ]
        psfs_interp = om.get("psfs_interp")
        severity_lines = [f"OM: PSFS interpretation = {psfs_interp}"] if psfs_interp else []
        for bid in severity_badge_ids:
            _set(bid, severity_lines)

        # Traumatic — context at onset from subjective
        lines = []
        if subj.get("context_at_onset", "").strip():
            lines.append("Subj: context at onset recorded")
        _set("xref_dx_traumatic", lines)

        # Neuropathic — red flags from medical
        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        if med.get("rf_saddle_anaesthesia") is True:
            lines.append("Med: saddle anaesthesia (red flag +ve)")
        _set("xref_dx_neuropathic", lines)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in _CYCLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CycleField).get_value()
            except Exception:
                data[fid] = None
        for fid in _TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", YesNoField).get_value()
            except Exception:
                data[fid] = None
        for fid in _INPUT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", Input).value
            except Exception:
                data[fid] = ""
        for fid in _TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            dx = data if isinstance(data, dict) else {}
            for fid in _CYCLE_FIELDS:
                if fid in dx:
                    try:
                        self.query_one(f"#{fid}", CycleField).set_value(dx[fid])
                    except Exception:
                        pass
            for fid in _TOGGLE_FIELDS:
                if fid in dx:
                    try:
                        self.query_one(f"#{fid}", YesNoField).set_value(dx[fid])
                    except Exception:
                        pass
            for fid in _INPUT_FIELDS:
                if fid in dx:
                    try:
                        self.query_one(f"#{fid}", Input).value = dx[fid]
                    except Exception:
                        pass
            for fid in _TEXT_FIELDS:
                if fid in dx:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = dx[fid]
                    except Exception:
                        pass
        finally:
            self._loading = False
            self.update_cross_refs()

    def is_complete(self) -> bool:
        return self.collect().get("mechanism") is not None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(YesNoField.Changed)
    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
