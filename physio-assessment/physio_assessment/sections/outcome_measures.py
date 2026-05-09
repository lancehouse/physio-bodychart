"""Outcome Measures section (core/05)."""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from .consent import YesNoField


# ---------------------------------------------------------------------------
# Shared option lists
# ---------------------------------------------------------------------------

_DASS_OPTIONS = [
    ("Normal",           "success"),
    ("Mild",             "primary"),
    ("Moderate",         "warning"),
    ("Severe",           "error"),
    ("Extremely severe", "error"),
]

_PCS_RISK_OPTIONS = [
    ("Low",       "success"),
    ("Moderate",  "warning"),
    ("High risk", "error"),
]

_PCL5_OPTIONS = [
    ("Negative (<33)",        "success"),
    ("Positive — PTSD likely","error"),
]

_ISI_OPTIONS = [
    ("No insomnia (<10)",             "success"),
    ("Clinically significant (≥10)",  "error"),
]

_PBAS_OPTIONS = [
    ("Normal",   "success"),
    ("Moderate", "warning"),
    ("Severe",   "error"),
]

_PSFS_INTERP_OPTIONS = [
    ("Mild",     "success"),
    ("Moderate", "warning"),
    ("Marked",   "error"),
]


# ---------------------------------------------------------------------------
# Auto-interpretation functions
# ---------------------------------------------------------------------------

def _interp_dass_dep(score: int) -> str:
    if score < 10: return "Normal"
    if score < 14: return "Mild"
    if score < 21: return "Moderate"
    if score < 28: return "Severe"
    return "Extremely severe"


def _interp_dass_anx(score: int) -> str:
    if score < 8:  return "Normal"
    if score < 10: return "Mild"
    if score < 15: return "Moderate"
    if score < 20: return "Severe"
    return "Extremely severe"


def _interp_dass_str(score: int) -> str:
    if score < 15: return "Normal"
    if score < 19: return "Mild"
    if score < 26: return "Moderate"
    if score < 34: return "Severe"
    return "Extremely severe"


def _interp_pcs_total(score: int) -> str:
    if score < 20: return "Low"
    if score < 30: return "Moderate"
    return "High risk"


def _interp_pcl5(score: int) -> str:
    return "Positive — PTSD likely" if score >= 33 else "Negative (<33)"


def _interp_isi(score: int) -> str:
    return "Clinically significant (≥10)" if score >= 10 else "No insomnia (<10)"


# ---------------------------------------------------------------------------
# CycleField widget
# ---------------------------------------------------------------------------

class CycleField(Static):
    """Button that cycles through a fixed list of labelled options."""

    DEFAULT_CSS = """
    CycleField {
        height: auto;
        width: auto;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    CycleField Button {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 1;
    }
    """

    def __init__(self, field_id: str, options: list[tuple[str, str]], **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._field_id = field_id
        self._options = [(None, "default")] + list(options)
        self._idx = 0

    def compose(self) -> ComposeResult:
        yield Button("?", id=f"{self._field_id}_btn", variant="default")

    def get_value(self) -> str | None:
        return self._options[self._idx][0]

    def set_value(self, value: str | None) -> None:
        for i, (opt, _) in enumerate(self._options):
            if opt == value:
                self._idx = i
                self._refresh()
                return
        self._idx = 0
        self._refresh()

    def _refresh(self) -> None:
        label, variant = self._options[self._idx]
        try:
            btn = self.query_one(Button)
            btn.label = label if label else "?"
            btn.variant = variant
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_btn":
            self._idx = (self._idx + 1) % len(self._options)
            self._refresh()
            self.post_message(CycleField.Changed())
            event.stop()

    class Changed(Message):
        pass


# ---------------------------------------------------------------------------
# HypRow — one row in the hypothesis testing table
# ---------------------------------------------------------------------------

_HYP_COLS = ["measure", "baseline", "interval", "rationale"]


class HypRow(Horizontal):
    """One row in the hypothesis testing table."""

    def __init__(self, row_idx: int, **kwargs):
        super().__init__(**kwargs)
        self._row_idx = row_idx

    def compose(self) -> ComposeResult:
        yield Input(id=f"hyp_{self._row_idx}_measure",  classes="hyp_measure",  placeholder="Measure")
        yield Input(id=f"hyp_{self._row_idx}_baseline", classes="hyp_baseline", placeholder="Baseline")
        yield Input(id=f"hyp_{self._row_idx}_interval", classes="hyp_interval", placeholder="Interval")
        yield Input(id=f"hyp_{self._row_idx}_rationale",classes="hyp_rationale",placeholder="Rationale")


# ---------------------------------------------------------------------------
# OMNavBar
# ---------------------------------------------------------------------------

class OMNavBar(Static):
    """Fixed navigation bar for Outcome Measures section."""

    SUBSECTIONS = [
        ("PSFS",       "om_psfs"),
        ("BPI",        "om_bpi"),
        ("DASS",       "om_dass"),
        ("PCS",        "om_pcs"),
        ("PSEQ/PCL",   "om_pseq"),
        ("Sleep",      "om_sleep"),
        ("Additional", "om_additional"),
        ("Hypothesis", "om_hypothesis"),
    ]

    DEFAULT_CSS = """
    OMNavBar {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    OMNavBar Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    OMNavBar Button:hover {
        background: $accent;
    }
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
# OutcomeMeasuresSection
# ---------------------------------------------------------------------------

_HYP_ROWS = 3

_SCORE_FIELDS = [
    "psfs_score",
    "psfs_act_1", "psfs_act_2", "psfs_act_3", "psfs_act_4", "psfs_act_5",
    "bpi_activity", "bpi_mood", "bpi_walking", "bpi_work",
    "bpi_relations", "bpi_sleep", "bpi_enjoyment",
    "dass_dep_score", "dass_anx_score", "dass_str_score",
    "pcs_rum_score", "pcs_mag_score", "pcs_help_score", "pcs_total_score",
    "pseq_score", "pcl5_score", "isi_score", "pbas_score",
]

_CYCLE_FIELDS = [
    "psfs_interp",
    "dass_dep_interp", "dass_anx_interp", "dass_str_interp",
    "pcs_rum_risk", "pcs_mag_risk", "pcs_help_risk", "pcs_total_risk",
    "pcl5_interp", "isi_interp", "pbas_interp",
]

_TOGGLE_FIELDS = ["add_audit", "add_dudit"]

_TEXT_FIELDS = ["pcl5_action", "add_epoc", "add_other"]


class OutcomeMeasuresSection(BaseSection):
    """Outcome Measures section (core/05)."""

    DEFAULT_CSS = """
    OutcomeMeasuresSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #om_nav { height: auto; }

    #om_scroll { width: 100%; height: 1fr; }

    #om_content { width: 100%; height: auto; padding: 0 1; }

    .section_title  { text-style: bold; margin-bottom: 0; }
    .subsection_header {
        text-style: bold; color: $primary;
        padding-top: 1; margin-bottom: 0;
    }
    .reference_note { color: $text-muted; margin-bottom: 0; }

    Label { margin-bottom: 0; }

    TextArea, Input { height: auto; min-height: 1; margin-bottom: 0; }

    /* Compact table rows */
    .om_row     { height: auto; margin-bottom: 0; }
    .om_label   { width: 1fr; margin-bottom: 0; }
    .om_score   { width: 10; margin-bottom: 0; }

    /* DASS */
    .dass_row   { height: auto; margin-bottom: 0; }
    .dass_label { width: 1fr; margin-bottom: 0; }
    .dass_score { width: 8; margin-bottom: 0; }

    /* PCS */
    .pcs_row    { height: auto; margin-bottom: 0; }
    .pcs_label  { width: 1fr; margin-bottom: 0; }
    .pcs_max    { width: 5; color: $text-muted; margin-bottom: 0; }
    .pcs_score  { width: 8; margin-bottom: 0; }

    /* BPI */
    .bpi_row    { height: auto; margin-bottom: 0; }
    .bpi_label  { width: 1fr; margin-bottom: 0; }
    .bpi_score  { width: 8; margin-bottom: 0; }

    /* Hypothesis testing table */
    .hyp_header_row  { height: auto; margin-bottom: 0; }
    .hyp_header      { text-style: bold; color: $text-muted; margin-bottom: 0; }
    .hyp_measure     { width: 2fr; }
    .hyp_baseline    { width: 2fr; }
    .hyp_interval    { width: 2fr; }
    .hyp_rationale   { width: 3fr; }
    HypRow           { height: auto; margin-bottom: 0; }

    /* Alert banners */
    .om_alert {
        width: 100%; padding: 0 1; text-style: bold;
        color: $warning; background: $warning 20%;
        margin-bottom: 0;
    }

    /* Cross-ref badges */
    .xref_badge {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $accent; background: $accent 12%;
    }
    .xref_badge_urgent {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $warning; background: $warning 20%;
        text-style: bold;
    }
    """

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield OMNavBar(on_jump_to=self._jump_to, id="om_nav")

        with ScrollableContainer(id="om_scroll"):
            with Vertical(id="om_content"):
                yield Label("Outcome Measures", classes="section_title")

                # ── PSFS ──────────────────────────────────────────────
                yield Label("— Patient Specific Functional Scale (PSFS) —", classes="subsection_header", id="om_psfs")
                yield Label("Score /80:")
                with Horizontal(classes="om_row"):
                    yield Input(id="psfs_score", placeholder="/80", classes="om_score")
                    yield CycleField("psfs_interp", _PSFS_INTERP_OPTIONS)
                yield Label("Activities listed:")
                yield Input(id="psfs_act_1", placeholder="1.")
                yield Input(id="psfs_act_2", placeholder="2.")
                yield Input(id="psfs_act_3", placeholder="3.")
                yield Input(id="psfs_act_4", placeholder="4.")
                yield Input(id="psfs_act_5", placeholder="5.")

                # ── BPI ───────────────────────────────────────────────
                yield Label("— Brief Pain Inventory (BPI) —", classes="subsection_header", id="om_bpi")
                yield Label("Scores /10 — higher = greater impairment due to pain", classes="reference_note")
                with Horizontal(classes="bpi_row"):
                    yield Label("General activity:", classes="bpi_label")
                    yield Input(id="bpi_activity", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Mood:", classes="bpi_label")
                    yield Input(id="bpi_mood", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Walking ability:", classes="bpi_label")
                    yield Input(id="bpi_walking", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Normal work:", classes="bpi_label")
                    yield Input(id="bpi_work", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Relations with other people:", classes="bpi_label")
                    yield Input(id="bpi_relations", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Sleep:", classes="bpi_label")
                    yield Input(id="bpi_sleep", placeholder="/10", classes="bpi_score")
                with Horizontal(classes="bpi_row"):
                    yield Label("Enjoyment of life:", classes="bpi_label")
                    yield Input(id="bpi_enjoyment", placeholder="/10", classes="bpi_score")

                # ── DASS-21 ───────────────────────────────────────────
                yield Label("— DASS-21 —", classes="subsection_header", id="om_dass")
                yield Static("", id="xref_om_dass", classes="xref_badge")
                with Horizontal(classes="dass_row"):
                    yield Label("Depression:",   classes="dass_label")
                    yield Input(id="dass_dep_score", placeholder="0–42", classes="dass_score")
                    yield CycleField("dass_dep_interp", _DASS_OPTIONS)
                with Horizontal(classes="dass_row"):
                    yield Label("Anxiety:",      classes="dass_label")
                    yield Input(id="dass_anx_score", placeholder="0–42", classes="dass_score")
                    yield CycleField("dass_anx_interp", _DASS_OPTIONS)
                with Horizontal(classes="dass_row"):
                    yield Label("Stress:",       classes="dass_label")
                    yield Input(id="dass_str_score", placeholder="0–42", classes="dass_score")
                    yield CycleField("dass_str_interp", _DASS_OPTIONS)

                # ── PCS ───────────────────────────────────────────────
                yield Label("— Pain Catastrophising Scale (PCS) —", classes="subsection_header", id="om_pcs")
                yield Static("", id="xref_om_pcs", classes="xref_badge")
                with Horizontal(classes="pcs_row"):
                    yield Label("Rumination:",   classes="pcs_label")
                    yield Label("/16", classes="pcs_max")
                    yield Input(id="pcs_rum_score",  placeholder="0–16",  classes="pcs_score")
                    yield CycleField("pcs_rum_risk",  _PCS_RISK_OPTIONS)
                with Horizontal(classes="pcs_row"):
                    yield Label("Magnification:", classes="pcs_label")
                    yield Label("/12", classes="pcs_max")
                    yield Input(id="pcs_mag_score",  placeholder="0–12",  classes="pcs_score")
                    yield CycleField("pcs_mag_risk",  _PCS_RISK_OPTIONS)
                with Horizontal(classes="pcs_row"):
                    yield Label("Helplessness:", classes="pcs_label")
                    yield Label("/24", classes="pcs_max")
                    yield Input(id="pcs_help_score", placeholder="0–24",  classes="pcs_score")
                    yield CycleField("pcs_help_risk", _PCS_RISK_OPTIONS)
                with Horizontal(classes="pcs_row"):
                    yield Label("Total:",        classes="pcs_label")
                    yield Label("/52", classes="pcs_max")
                    yield Input(id="pcs_total_score",placeholder="0–52",  classes="pcs_score")
                    yield CycleField("pcs_total_risk",_PCS_RISK_OPTIONS)
                yield Static("", id="om_pcs_alert", classes="om_alert")

                # ── PSEQ ──────────────────────────────────────────────
                yield Label("— Pain Self-Efficacy Questionnaire (PSEQ) —", classes="subsection_header", id="om_pseq")
                yield Label("Score /60 — higher = stronger self-efficacy", classes="reference_note")
                yield Input(id="pseq_score", placeholder="/60")
                yield Static("", id="xref_om_pseq", classes="xref_badge")

                # ── PCL-5 ─────────────────────────────────────────────
                yield Label("— Post-Traumatic Stress Disorder Checklist (PCL-5) —", classes="subsection_header")
                yield Label("Score /80:", )
                with Horizontal(classes="om_row"):
                    yield Input(id="pcl5_score", placeholder="/80", classes="om_score")
                    yield CycleField("pcl5_interp", _PCL5_OPTIONS)
                yield Static("", id="om_pcl5_alert", classes="om_alert")
                yield Static("", id="xref_om_pcl5", classes="xref_badge_urgent")
                yield Label("Action if positive:")
                yield TextArea(id="pcl5_action", language="plain")

                # ── Sleep ─────────────────────────────────────────────
                yield Label("— Sleep Outcome Measures —", classes="subsection_header", id="om_sleep")
                yield Static("", id="xref_om_sleep", classes="xref_badge")

                yield Label("Insomnia Severity Index (ISI) — score /28:")
                with Horizontal(classes="om_row"):
                    yield Input(id="isi_score", placeholder="/28", classes="om_score")
                    yield CycleField("isi_interp", _ISI_OPTIONS)
                yield Static("", id="om_isi_alert", classes="om_alert")

                yield Label("Pain-Related Beliefs and Attitudes About Sleep (PBAS) — score /10:")
                with Horizontal(classes="om_row"):
                    yield Input(id="pbas_score", placeholder="/10", classes="om_score")
                    yield CycleField("pbas_interp", _PBAS_OPTIONS)

                # ── Additional ────────────────────────────────────────
                yield Label("— Additional Measures —", classes="subsection_header", id="om_additional")
                yield YesNoField("AUDIT (alcohol use)",  field_id="add_audit")
                yield Static("", id="xref_om_audit", classes="xref_badge")
                yield YesNoField("DUDIT (drug use)",     field_id="add_dudit")
                yield Label("ePPOC components (specify):")
                yield TextArea(id="add_epoc", language="plain")
                yield Label("Other:")
                yield TextArea(id="add_other", language="plain")

                # ── Hypothesis testing ────────────────────────────────
                yield Label("— Measures Selected for Ongoing Hypothesis Testing —", classes="subsection_header", id="om_hypothesis")
                yield Label("Individualise questionnaire set to test your clinical hypothesis for this patient.", classes="reference_note")
                with Horizontal(classes="hyp_header_row"):
                    yield Label("Measure",   classes="hyp_measure hyp_header")
                    yield Label("Baseline",  classes="hyp_baseline hyp_header")
                    yield Label("Interval",  classes="hyp_interval hyp_header")
                    yield Label("Rationale", classes="hyp_rationale hyp_header")
                for i in range(_HYP_ROWS):
                    yield HypRow(i)

                yield Label("Administer questionnaires same day where possible. Score before next session.", classes="reference_note")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#om_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Auto-interpretation and alerts
    # ------------------------------------------------------------------

    def _update_auto_interp(self) -> None:
        """Set interpretation labels from score inputs using published thresholds."""
        _auto = [
            ("dass_dep_score", "dass_dep_interp", _interp_dass_dep),
            ("dass_anx_score", "dass_anx_interp", _interp_dass_anx),
            ("dass_str_score", "dass_str_interp", _interp_dass_str),
            ("pcs_total_score","pcs_total_risk",  _interp_pcs_total),
            ("pcl5_score",     "pcl5_interp",     _interp_pcl5),
            ("isi_score",      "isi_interp",      _interp_isi),
        ]
        for score_id, interp_id, fn in _auto:
            try:
                raw = self.query_one(f"#{score_id}", Input).value.strip()
                if raw.lstrip("-").isdigit():
                    self.query_one(f"#{interp_id}", CycleField).set_value(fn(int(raw)))
            except Exception:
                pass

    def _update_alerts(self) -> None:
        """Show/hide threshold alerts for PCS, PCL-5, ISI."""
        _checks = [
            ("pcs_total_score", 30, "om_pcs_alert",  "⚠ PCS total ≥30 — high catastrophising: consider psychology referral"),
            ("pcl5_score",      33, "om_pcl5_alert", "⚠ PCL-5 ≥33 — PTSD likely: document action above"),
            ("isi_score",       10, "om_isi_alert",  "⚠ ISI ≥10 — clinically significant insomnia"),
        ]
        for score_id, threshold, alert_id, msg in _checks:
            try:
                raw = self.query_one(f"#{score_id}", Input).value.strip()
                alert = self.query_one(f"#{alert_id}", Static)
                if raw.lstrip("-").isdigit() and int(raw) >= threshold:
                    alert.update(msg)
                    alert.display = True
                else:
                    alert.display = False
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

        def _sec(key):
            v = data.get("assessment", {}).get(key)
            return v if isinstance(v, dict) else {}

        med  = _sec("medical")
        subj = _sec("subjective")

        def _set(badge_id: str, lines: list[str], urgent: bool = False) -> None:
            try:
                w = self.query_one(f"#{badge_id}", Static)
                if lines:
                    w.update("  ".join(f"◀ {l}" for l in lines))
                    w.display = True
                else:
                    w.display = False
            except Exception:
                pass

        # DASS — mental health comorbidity + psychological distress
        lines = []
        if med.get("comorbid_mental_health") is True:
            lines.append("Med: mental health condition (comorbidity)")
        if subj.get("psychological_distress", "").strip():
            lines.append("Subj: psychological distress recorded")
        if subj.get("mood_influences") is True:
            lines.append("Subj: mood influences pain")
        if subj.get("screening_tool", "").strip():
            lines.append("Subj: screening tool recorded")
        _set("xref_om_dass", lines)

        # PCS — psychological distress from Subjective
        lines = []
        if subj.get("psychological_distress", "").strip():
            lines.append("Subj: psychological distress recorded")
        _set("xref_om_pcs", lines)

        # PSEQ — confidence score from Subjective (show numeric value)
        lines = []
        conf = subj.get("confidence_score", "").strip()
        if conf:
            lines.append(f"Subj: confidence score = {conf}/10")
        _set("xref_om_pseq", lines)

        # PCL-5 — self-harm risk from Subjective (urgent treatment)
        lines = []
        if subj.get("self_harm_risk") is True:
            lines.append("Subj: self-harm/suicide risk — POSITIVE")
        elif subj.get("self_harm_risk") is False:
            lines.append("Subj: self-harm/suicide risk — cleared")
        if subj.get("harm_plan", "").strip():
            lines.append("Subj: harm plan documented")
        _set("xref_om_pcl5", lines, urgent=True)

        # Sleep — sleep fields from Subjective
        lines = []
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj.get("night_waking") is True:
            lines.append("Subj: night waking")
        total_sleep = subj.get("total_sleep_hours", "").strip()
        if total_sleep:
            lines.append(f"Subj: {total_sleep} hrs/night")
        _set("xref_om_sleep", lines)

        # AUDIT/DUDIT — drug/alcohol comorbidity from Medical
        lines = []
        if med.get("comorbid_drug_alcohol") is True:
            lines.append("Med: drug/alcohol issues (comorbidity)")
        _set("xref_om_audit", lines)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in _SCORE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", Input).value
            except Exception:
                data[fid] = ""
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
        for fid in _TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        for i in range(_HYP_ROWS):
            for col in _HYP_COLS:
                fid = f"hyp_{i}_{col}"
                try:
                    data[fid] = self.query_one(f"#{fid}", Input).value
                except Exception:
                    data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            om = data if isinstance(data, dict) else {}
            for fid in _SCORE_FIELDS:
                if fid in om:
                    try:
                        self.query_one(f"#{fid}", Input).value = om[fid]
                    except Exception:
                        pass
            for fid in _CYCLE_FIELDS:
                if fid in om:
                    try:
                        self.query_one(f"#{fid}", CycleField).set_value(om[fid])
                    except Exception:
                        pass
            for fid in _TOGGLE_FIELDS:
                if fid in om:
                    try:
                        self.query_one(f"#{fid}", YesNoField).set_value(om[fid])
                    except Exception:
                        pass
            for fid in _TEXT_FIELDS:
                if fid in om:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = om[fid]
                    except Exception:
                        pass
            for i in range(_HYP_ROWS):
                for col in _HYP_COLS:
                    fid = f"hyp_{i}_{col}"
                    if fid in om:
                        try:
                            self.query_one(f"#{fid}", Input).value = om[fid]
                        except Exception:
                            pass
        finally:
            self._loading = False
            self._update_auto_interp()
            self._update_alerts()
            self.update_cross_refs()

    def is_complete(self) -> bool:
        d = self.collect()
        main_scores = ["psfs_score", "bpi_activity", "dass_dep_score",
                       "pcs_total_score", "pseq_score", "pcl5_score", "isi_score"]
        return any(d.get(f, "").strip() for f in main_scores)

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._update_auto_interp()
        self._update_alerts()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
