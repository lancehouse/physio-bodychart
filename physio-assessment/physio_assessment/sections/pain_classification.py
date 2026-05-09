"""Pain Type Classification section (core/04)."""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from .consent import YesNoField
from .medical import LikelihoodField


class PainTypeSelector(Static):
    """Cycling selector for dominant pain type."""

    DEFAULT_CSS = """
    PainTypeSelector {
        height: auto;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    PainTypeSelector > Label {
        width: 1fr;
        margin-bottom: 0;
        padding-right: 1;
    }
    PainTypeSelector Button {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 2;
    }
    """

    _CYCLE = [None, "Nociceptive", "Neuropathic", "Nociplastic", "Mixed — unable to determine"]
    _VARIANTS = {
        None: "primary",
        "Nociceptive": "success",
        "Neuropathic": "warning",
        "Nociplastic": "error",
        "Mixed — unable to determine": "default",
    }

    def __init__(self, label: str, field_id: str, **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._label = label
        self._field_id = field_id
        self._value = None

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Button("?", id=f"{self._field_id}_btn", variant="primary")

    def get_value(self) -> str | None:
        return self._value

    def set_value(self, value: str | None) -> None:
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_btn", Button)
            btn.label = value if value else "?"
            btn.variant = self._VARIANTS.get(value, "primary")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_btn":
            idx = self._CYCLE.index(self._value)
            self.set_value(self._CYCLE[(idx + 1) % len(self._CYCLE)])
            self.post_message(PainTypeSelector.Changed())
            event.stop()

    class Changed(Message):
        pass


class PCNavBar(Static):
    """Fixed navigation bar for Pain Classification section."""

    SUBSECTIONS = [
        ("Inflamm",      "pc_inflammatory"),
        ("Nociceptive",  "pc_nociceptive"),
        ("Neuropathic",  "pc_neuropathic"),
        ("Nociplastic",  "pc_nociplastic"),
        ("Central Sens", "pc_central"),
        ("Summary",      "pc_summary"),
    ]

    DEFAULT_CSS = """
    PCNavBar {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    PCNavBar Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    PCNavBar Button:hover {
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


class PainClassificationSection(BaseSection):
    """Pain Type Classification section (core/04)."""

    DEFAULT_CSS = """
    PainClassificationSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #pc_nav {
        height: auto;
    }

    #pc_scroll {
        width: 100%;
        height: 1fr;
    }

    #pc_content {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title {
        text-style: bold;
        margin-bottom: 0;
    }

    .subsection_header {
        text-style: bold;
        color: $primary;
        padding-top: 1;
        margin-bottom: 0;
    }

    .subgroup_header {
        color: $text-muted;
        padding-top: 1;
        margin-bottom: 0;
        text-style: italic;
    }

    .reference_note {
        color: $text-muted;
        margin-bottom: 0;
    }

    TextArea, Input {
        height: auto;
        min-height: 1;
        margin-bottom: 0;
    }

    Label {
        margin-bottom: 0;
    }

    #pc_infl_score {
        color: $primary;
        text-style: bold;
        margin-bottom: 0;
        padding-top: 0;
    }

    #pc_infl_alert {
        width: 100%;
        padding: 0 1;
        text-style: bold;
        color: $warning;
        background: $warning 20%;
        margin-bottom: 0;
    }

    #pc_csi_alert {
        width: 100%;
        padding: 0 1;
        text-style: bold;
        color: $warning;
        background: $warning 20%;
        margin-bottom: 0;
    }

    #pc_mixed_reminder {
        width: 100%;
        padding: 0 1;
        color: $warning;
        margin-bottom: 0;
    }

    .xref_badge {
        width: 100%;
        height: auto;
        padding: 0 1;
        margin-bottom: 0;
        color: $accent;
        background: $accent 12%;
    }
    """

    _INFL_FIELDS = ["infl_constant", "infl_morning", "infl_sleep", "infl_activity"]

    _TOGGLE_FIELDS = [
        # Inflammatory
        "infl_constant", "infl_morning", "infl_sleep", "infl_activity",
        # Nociceptive subjective
        "noci_subj_mechanical", "noci_subj_trauma", "noci_subj_localised",
        "noci_subj_resolving", "noci_subj_analgesia", "noci_subj_no_constant",
        "noci_subj_inflammation", "noci_subj_recent",
        # Nociceptive examination
        "noci_exam_mechanical", "noci_exam_palpation",
        "noci_exam_hyperalgesia", "noci_exam_antalgic",
        # Neuropathic subjective
        "neuro_subj_quality", "neuro_subj_nerve_injury", "neuro_subj_neurological",
        "neuro_subj_dermatomal", "neuro_subj_medication", "neuro_subj_severity",
        "neuro_subj_neural_loading", "neuro_subj_dysaesthesia", "neuro_subj_spontaneous",
        # Neuropathic examination
        "neuro_exam_neurodynamic", "neuro_exam_neural_palpation",
        "neuro_exam_neurology", "neuro_exam_antalgic", "neuro_exam_hyperalgesia",
        # Nociplastic subjective
        "nocip_subj_disproportionate", "nocip_subj_persistent",
        "nocip_subj_disproportionate2", "nocip_subj_widespread",
        "nocip_subj_failed", "nocip_subj_psychosocial", "nocip_subj_medication",
        "nocip_subj_spontaneous", "nocip_subj_disability", "nocip_subj_constant",
        "nocip_subj_night_pain", "nocip_subj_dysaesthesia", "nocip_subj_severity",
        # Nociplastic examination
        "nocip_exam_disproportionate", "nocip_exam_hyperalgesia",
        "nocip_exam_diffuse", "nocip_exam_psychosocial",
        # Central sensitisation features
        "cs_light", "cs_touch", "cs_noise", "cs_pesticides", "cs_temperature",
        "cs_fatigue", "cs_sleep", "cs_concentration", "cs_swelling", "cs_tingling",
    ]

    _LIKELIHOOD_FIELDS = [
        "infl_likelihood",
        "noci_likelihood",
        "neuro_likelihood",
        "nocip_likelihood",
    ]

    _TEXT_FIELDS = [
        "noci_interpretation",
        "neuro_interpretation",
        "nocip_interpretation",
        "summary_contributing",
        "summary_reasoning",
    ]

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield PCNavBar(on_jump_to=self._jump_to, id="pc_nav")

        with ScrollableContainer(id="pc_scroll"):
            with Vertical(id="pc_content"):
                yield Label("Pain Type Classification", classes="section_title")

                # ── Inflammatory Pain ────────────────────────────────────
                yield Label("— Inflammatory Pain Features —", classes="subsection_header", id="pc_inflammatory")
                yield Label("(Walker & Williamson 2008)", classes="reference_note")
                yield YesNoField("Constant symptoms",                                       field_id="infl_constant")
                yield YesNoField("Increased morning pain and/or stiffness lasting >30 min", field_id="infl_morning")
                yield Static("", id="xref_infl_morning", classes="xref_badge")
                yield YesNoField("At least moderate sleep disturbance due to pain",         field_id="infl_sleep")
                yield Static("", id="xref_infl_sleep", classes="xref_badge")
                yield YesNoField("Symptoms improved with activity compared to rest",        field_id="infl_activity")
                yield Static("Score: 0/4", id="pc_infl_score")
                yield Static("", id="pc_infl_alert")
                yield LikelihoodField("Likelihood of inflammatory pain:", field_id="infl_likelihood")
                yield Static("", id="xref_infl_dx", classes="xref_badge")

                # ── Nociceptive Pain ────────────────────────────────────
                yield Label("— Nociceptive Pain —", classes="subsection_header", id="pc_nociceptive")
                yield Label("(Smart et al 2010) — pain arising from actual or threatened damage to non-neural tissue", classes="reference_note")
                yield Label("Subjective features:", classes="subgroup_header")
                yield YesNoField("Clear, proportionate mechanical/anatomical aggravating and easing factors",            field_id="noci_subj_mechanical")
                yield YesNoField("Pain associated with and proportionate to trauma, pathology, or movement dysfunction", field_id="noci_subj_trauma")
                yield YesNoField("Pain localised to area of injury/dysfunction (with/without somatic referral)",         field_id="noci_subj_localised")
                yield YesNoField("Usually resolving in accordance with expected tissue healing times",                   field_id="noci_subj_resolving")
                yield Static("", id="xref_noci_resolving", classes="xref_badge")
                yield YesNoField("Responsive to simple analgesia / NSAIDs",                                              field_id="noci_subj_analgesia")
                yield YesNoField("Absence of constant/unremitting pain",                                                 field_id="noci_subj_no_constant")
                yield YesNoField("Pain in association with other symptoms of inflammation",                              field_id="noci_subj_inflammation")
                yield YesNoField("Pain of recent onset",                                                                 field_id="noci_subj_recent")
                yield Label("Examination features:", classes="subgroup_header")
                yield YesNoField("Clear, consistent, proportionate mechanical/anatomical pattern on movement/testing",   field_id="noci_exam_mechanical")
                yield YesNoField("Localised pain on palpation",                                                          field_id="noci_exam_palpation")
                yield YesNoField("Absent or proportionate findings of hyperalgesia and/or allodynia",                    field_id="noci_exam_hyperalgesia")
                yield YesNoField("Presence of antalgic postures/movement patterns",                                      field_id="noci_exam_antalgic")
                yield LikelihoodField("Likelihood of nociceptive pain:", field_id="noci_likelihood")
                yield Label("Interpretation:")
                yield TextArea(id="noci_interpretation", language="plain")

                # ── Neuropathic Pain ────────────────────────────────────
                yield Label("— Neuropathic Pain —", classes="subsection_header", id="pc_neuropathic")
                yield Label("(Smart et al 2010) — pain caused by a lesion or disease of the somatosensory nervous system", classes="reference_note")
                yield Label("Subjective features:", classes="subgroup_header")
                yield YesNoField("Burning, shooting, sharp, aching or electric shock-like quality",                      field_id="neuro_subj_quality")
                yield YesNoField("History of nerve injury",                                                              field_id="neuro_subj_nerve_injury")
                yield YesNoField("Neurological symptoms including paraesthesia",                                         field_id="neuro_subj_neurological")
                yield Static("", id="xref_neuro_neurological", classes="xref_badge")
                yield YesNoField("Pain referred in dermatomal or cutaneous distribution",                                field_id="neuro_subj_dermatomal")
                yield YesNoField("Less responsive to NSAIDs; more responsive to anti-epileptic/antidepressant",         field_id="neuro_subj_medication")
                yield YesNoField("High severity and irritability",                                                       field_id="neuro_subj_severity")
                yield YesNoField("Mechanical pattern involving activities/postures loading or compressing neural tissue", field_id="neuro_subj_neural_loading")
                yield YesNoField("Other dysaesthesias (burning, coldness, crawling)",                                    field_id="neuro_subj_dysaesthesia")
                yield YesNoField("Spontaneous (stimulus-independent) pain and/or paroxysmal pain",                      field_id="neuro_subj_spontaneous")
                yield Label("Examination features:", classes="subgroup_header")
                yield YesNoField("Symptom provocation with provocative neurodynamic tests",                              field_id="neuro_exam_neurodynamic")
                yield YesNoField("Pain/symptom provocation on palpation of relevant neural tissues",                    field_id="neuro_exam_neural_palpation")
                yield YesNoField("Positive neurological findings",                                                       field_id="neuro_exam_neurology")
                yield YesNoField("Antalgic posturing of affected limb/body part",                                       field_id="neuro_exam_antalgic")
                yield YesNoField("Positive hyperalgesia/allodynia within distribution of pain",                         field_id="neuro_exam_hyperalgesia")
                yield LikelihoodField("Likelihood of neuropathic pain:", field_id="neuro_likelihood")
                yield Label("Interpretation:")
                yield TextArea(id="neuro_interpretation", language="plain")

                # ── Nociplastic Pain ────────────────────────────────────
                yield Label("— Nociplastic Pain —", classes="subsection_header", id="pc_nociplastic")
                yield Label("(IASP) — pain arising from altered nociception despite no clear nociceptive or neuropathic pain", classes="reference_note")
                yield Label("Subjective features:", classes="subgroup_header")
                yield YesNoField("Disproportionate, non-mechanical, unpredictable pattern of provocation",               field_id="nocip_subj_disproportionate")
                yield YesNoField("Pain persisting beyond expected tissue healing/pathology recovery times",               field_id="nocip_subj_persistent")
                yield YesNoField("Pain disproportionate to nature and extent of injury or pathology",                    field_id="nocip_subj_disproportionate2")
                yield YesNoField("Widespread, non-anatomical distribution of pain",                                      field_id="nocip_subj_widespread")
                yield YesNoField("History of failed interventions",                                                      field_id="nocip_subj_failed")
                yield Static("", id="xref_nocip_failed", classes="xref_badge")
                yield YesNoField("Strong association with unhelpful psychosocial factors",                               field_id="nocip_subj_psychosocial")
                yield Static("", id="xref_nocip_psych", classes="xref_badge")
                yield YesNoField("Unresponsive to NSAIDs; more responsive to anti-epileptic/antidepressant",            field_id="nocip_subj_medication")
                yield YesNoField("Spontaneous (stimulus-independent) pain and/or paroxysmal pain",                      field_id="nocip_subj_spontaneous")
                yield YesNoField("High levels of functional disability",                                                 field_id="nocip_subj_disability")
                yield YesNoField("More constant/unremitting pain",                                                       field_id="nocip_subj_constant")
                yield YesNoField("At least moderate night pain/disturbed sleep",                                         field_id="nocip_subj_night_pain")
                yield Static("", id="xref_nocip_night", classes="xref_badge")
                yield YesNoField("Other dysaesthesias (burning, coldness, crawling)",                                    field_id="nocip_subj_dysaesthesia")
                yield YesNoField("High severity and irritability",                                                       field_id="nocip_subj_severity")
                yield Label("Examination features:", classes="subgroup_header")
                yield YesNoField("Disproportionate, inconsistent, non-mechanical/non-anatomical pain provocation",      field_id="nocip_exam_disproportionate")
                yield YesNoField("Positive secondary hyperalgesia/allodynia within distribution of pain",               field_id="nocip_exam_hyperalgesia")
                yield YesNoField("Diffuse/non-anatomic areas of pain/tenderness on palpation",                         field_id="nocip_exam_diffuse")
                yield YesNoField("Positive psychosocial factors (catastrophisation, fear-avoidance, distress)",         field_id="nocip_exam_psychosocial")
                yield LikelihoodField("Likelihood of nociplastic pain:", field_id="nocip_likelihood")
                yield Static("", id="xref_nocip_dx", classes="xref_badge")
                yield Label("Interpretation:")
                yield TextArea(id="nocip_interpretation", language="plain")

                # ── Central Sensitisation ───────────────────────────────
                yield Label("— Central Sensitisation —", classes="subsection_header", id="pc_central")
                yield Label("(Nijs et al 2010, Neblett et al 2013)", classes="reference_note")
                yield Label("Central Sensitisation Inventory (CSI) score (0–100):")
                yield Input(id="csi_score", placeholder="0–100")
                yield Static("", id="pc_csi_alert")
                yield Label("Additional CS features (Nijs et al 2010):", classes="subgroup_header")
                yield YesNoField("Hypersensitivity to bright light",             field_id="cs_light")
                yield YesNoField("Hypersensitivity to touch",                    field_id="cs_touch")
                yield YesNoField("Hypersensitivity to noise",                    field_id="cs_noise")
                yield YesNoField("Hypersensitivity to pesticides/medication",    field_id="cs_pesticides")
                yield YesNoField("Hypersensitivity to high/low temperature",     field_id="cs_temperature")
                yield YesNoField("Fatigue",                                      field_id="cs_fatigue")
                yield Static("", id="xref_cs_fatigue", classes="xref_badge")
                yield YesNoField("Sleep disturbance",                            field_id="cs_sleep")
                yield Static("", id="xref_cs_sleep", classes="xref_badge")
                yield YesNoField("Concentration difficulty",                     field_id="cs_concentration")
                yield Static("", id="xref_cs_concentration", classes="xref_badge")
                yield YesNoField("Feelings of swelling in limbs",                field_id="cs_swelling")
                yield YesNoField("Tingling and/or numbness",                     field_id="cs_tingling")
                yield Static("", id="xref_cs_tingling", classes="xref_badge")

                # ── Summary ─────────────────────────────────────────────
                yield Label("— Pain Type Summary —", classes="subsection_header", id="pc_summary")
                yield PainTypeSelector("Dominant pain type:", field_id="summary_dominant")
                yield Static("", id="pc_mixed_reminder")
                yield Label("Contributing pain type(s):")
                yield TextArea(id="summary_contributing", language="plain")
                yield Label("Clinical reasoning for dominant classification:")
                yield TextArea(id="summary_reasoning", language="plain")

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#pc_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
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

        med = data.get("assessment", {}).get("medical", {})
        subj_assessment = data.get("assessment", {}).get("subjective", {})

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

        # infl_morning — morning stiffness text from Subjective
        lines = []
        if subj_assessment.get("morning_stiffness", "").strip():
            lines.append("Subj: morning stiffness recorded")
        _set("xref_infl_morning", lines)

        # infl_sleep — sleep trouble from Subjective
        lines = []
        if subj_assessment.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj_assessment.get("night_waking") is True:
            lines.append("Subj: night waking")
        _set("xref_infl_sleep", lines)

        # infl_dx — inflammatory comorbidity / diff AS from Medical
        lines = []
        if med.get("comorbid_inflammatory") is True:
            lines.append("Med: systemic inflammatory condition")
        if med.get("diff_as_inflammatory") is True:
            lines.append("Med: inflammatory pattern (diff. AS)")
        _set("xref_infl_dx", lines)

        # noci_resolving — course from Subjective
        lines = []
        if subj_assessment.get("course_improving") is True:
            lines.append("Subj: course improving")
        if subj_assessment.get("course_worsening") is True:
            lines.append("Subj: course worsening")
        _set("xref_noci_resolving", lines)

        # neuro_neurological — neurological red flags from Medical
        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        if med.get("rf_saddle_anaesthesia") is True:
            lines.append("Med: saddle anaesthesia (red flag +ve)")
        _set("xref_neuro_neurological", lines)

        # nocip_failed — previous treatment from Subjective
        lines = []
        if subj_assessment.get("previous_treatment", "").strip():
            lines.append("Subj: previous treatment recorded")
        _set("xref_nocip_failed", lines)

        # nocip_psych — mood from Subjective
        lines = []
        if subj_assessment.get("mood_influences") is True:
            lines.append("Subj: mood influences pain")
        _set("xref_nocip_psych", lines)

        # nocip_night — night waking from Subjective
        lines = []
        if subj_assessment.get("night_waking") is True:
            lines.append("Subj: night waking")
        _set("xref_nocip_night", lines)

        # nocip_dx — fibromyalgia / whiplash from Medical
        lines = []
        if med.get("comorbid_fibromyalgia") is True:
            lines.append("Med: fibromyalgia")
        if med.get("comorbid_whiplash") is True:
            lines.append("Med: chronic whiplash")
        _set("xref_nocip_dx", lines)

        # cs_fatigue — CFS / fatigue-memory from Medical
        lines = []
        if med.get("comorbid_cfs") is True:
            lines.append("Med: chronic fatigue syndrome")
        if med.get("comorbid_fatigue_memory") is True:
            lines.append("Med: fatigue/concentration/memory issues")
        _set("xref_cs_fatigue", lines)

        # cs_sleep — sleep from Subjective + CFS from Medical
        lines = []
        if subj_assessment.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj_assessment.get("night_waking") is True:
            lines.append("Subj: night waking")
        if med.get("comorbid_cfs") is True:
            lines.append("Med: CFS")
        _set("xref_cs_sleep", lines)

        # cs_concentration — fatigue/memory from Medical
        lines = []
        if med.get("comorbid_fatigue_memory") is True:
            lines.append("Med: fatigue/concentration/memory issues")
        if med.get("comorbid_cfs") is True:
            lines.append("Med: CFS")
        _set("xref_cs_concentration", lines)

        # cs_tingling — bilateral paraesthesia from Medical
        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        _set("xref_cs_tingling", lines)

    # ------------------------------------------------------------------
    # Auto-update display widgets
    # ------------------------------------------------------------------

    def _update_infl_score(self) -> None:
        try:
            score = sum(
                1 for fid in self._INFL_FIELDS
                if self.query_one(f"#{fid}", YesNoField).get_value() is True
            )
            self.query_one("#pc_infl_score", Static).update(f"Score: {score}/4")
            alert = self.query_one("#pc_infl_alert", Static)
            if score >= 2:
                alert.update(
                    "⚠ Score ≥2 — moderate likelihood of inflammatory processes "
                    "as significant barrier to recovery"
                )
                alert.display = True
            else:
                alert.display = False
        except Exception:
            pass

    def _update_csi_alert(self) -> None:
        try:
            score_str = self.query_one("#csi_score", Input).value.strip()
            alert = self.query_one("#pc_csi_alert", Static)
            if score_str.isdigit() and int(score_str) >= 40:
                alert.update(f"⚠ CSI score {score_str} ≥ 40 — suggestive of central sensitisation")
                alert.display = True
            else:
                alert.display = False
        except Exception:
            pass

    def _update_mixed_reminder(self) -> None:
        try:
            val = self.query_one("#summary_dominant", PainTypeSelector).get_value()
            reminder = self.query_one("#pc_mixed_reminder", Static)
            if val == "Mixed — unable to determine":
                reminder.update(
                    "Reminder: document plan to determine dominant pain type "
                    "during the preparation phase"
                )
                reminder.display = True
            else:
                reminder.display = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Data — independent of UI structure
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in self._TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", YesNoField).get_value()
            except Exception:
                data[fid] = None
        for fid in self._LIKELIHOOD_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", LikelihoodField).get_value()
            except Exception:
                data[fid] = None
        for fid in self._TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        try:
            data["csi_score"] = self.query_one("#csi_score", Input).value
        except Exception:
            data["csi_score"] = ""
        try:
            data["summary_dominant"] = self.query_one("#summary_dominant", PainTypeSelector).get_value()
        except Exception:
            data["summary_dominant"] = None
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            pain = data if isinstance(data, dict) else {}
            for fid in self._TOGGLE_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", YesNoField).set_value(pain[fid])
                    except Exception:
                        pass
            for fid in self._LIKELIHOOD_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", LikelihoodField).set_value(pain[fid])
                    except Exception:
                        pass
            for fid in self._TEXT_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = pain[fid]
                    except Exception:
                        pass
            if "csi_score" in pain:
                try:
                    self.query_one("#csi_score", Input).value = pain["csi_score"]
                except Exception:
                    pass
            if "summary_dominant" in pain:
                try:
                    self.query_one("#summary_dominant", PainTypeSelector).set_value(pain["summary_dominant"])
                except Exception:
                    pass
        finally:
            self._loading = False
            self._update_infl_score()
            self._update_csi_alert()
            self._update_mixed_reminder()
            self.update_cross_refs()

    def is_complete(self) -> bool:
        return self.collect().get("summary_dominant") is not None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(YesNoField.Changed)
    @on(LikelihoodField.Changed)
    @on(PainTypeSelector.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._update_infl_score()
        self._update_csi_alert()
        self._update_mixed_reminder()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
