"""Barriers to Recovery & Treatment Plan section (core/07).

Note: the spec calls for tick-driven auto-population of the treatment plan and
output table (ui-hint: auto-generated). That is deferred to a future phase;
all treatment plan fields are free-text editable for now.
"""

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

_DASS_SEVERITY_OPTIONS = [
    ("Mild",             "success"),
    ("Moderate",         "warning"),
    ("Severe",           "error"),
    ("Extremely severe", "error"),
]

_PAIN_TYPE_OPTIONS = [
    ("1 — Nociceptive / Neuropathic", "primary"),
    ("2 — Nociplastic",               "warning"),
]

_PTSD_MECHANISM_OPTIONS = [
    ("Motor vehicle accident",  "default"),
    ("Traumatic work accident", "default"),
    ("Other",                   "default"),
]

_DEBUNK_OPTIONS = [
    ("Yes", "success"),
    ("No",  "error"),
    ("N/A", "default"),
]


# ---------------------------------------------------------------------------
# Nav bar
# ---------------------------------------------------------------------------

class BrNavBar(Static):
    """Fixed navigation bar for Barriers & Treatment section."""

    SUBSECTIONS = [
        ("Physical",   "br_physical"),
        ("Neuro",      "br_neuro"),
        ("Nocip",      "br_nocip"),
        ("Psych",      "br_psych"),
        ("Sleep/Soc",  "br_sleep"),
        ("Medical",    "br_medical"),
        ("Custom",     "br_custom"),
        ("Treatment",  "br_treatment"),
        ("Session 1",  "br_session1"),
        ("Day 1",      "br_day1"),
        ("Follow-Up",  "br_followup"),
    ]

    DEFAULT_CSS = """
    BrNavBar {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    BrNavBar Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    BrNavBar Button:hover { background: $accent; }
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
# Field lists for collect / load
# ---------------------------------------------------------------------------

_TOGGLE_FIELDS = [
    # Physical / Nociceptive barriers
    "b_noci_disease", "b_noci_pacing", "b_noci_inflammatory", "b_noci_deconditioning",
    "b_noci_movement", "b_noci_gait", "b_noci_strength", "b_noci_deep_muscle",
    "b_noci_overactivity", "b_noci_nerve_mech", "b_noci_diet",
    # Strength sub-items
    "bx_strength_glute_max", "bx_strength_glute_med", "bx_strength_iliopsoas", "bx_strength_quads",
    # Deep muscle sub-items
    "bx_deep_multifidus", "bx_deep_ta", "bx_deep_erector",
    # Overactivity sub-items
    "bx_over_erector", "bx_over_ql", "bx_over_ra", "bx_over_obliques",
    "bx_over_piriformis", "bx_over_iliopsoas", "bx_over_hamstrings", "bx_over_adductors",
    # Neuropathic barriers
    "b_neuro_confirmed", "b_neuro_unconfirmed",
    # Nociplastic barriers
    "b_nocip_moderate", "b_nocip_crps", "b_nocip_fnd",
    # Psychological barriers
    "b_psych_depression", "b_psych_anxiety", "b_psych_stress",
    "b_psych_catastrophising", "b_psych_self_efficacy", "b_psych_unhelpful_beliefs",
    "b_psych_ptsd", "b_psych_readiness",
    # Psych sub-items
    "bx_dep_psychiatry", "bx_anx_psychiatry", "bx_stress_psychiatry", "bx_ptsd_psychiatry",
    # Unhelpful beliefs sub-items
    "bx_belief_expectations", "bx_belief_symptom_focus", "bx_belief_cure_focus", "bx_belief_further_tx",
    # Sleep
    "b_sleep_disturbed",
    # Social
    "b_social_home", "b_social_rtw",
    # Social sub-items
    "bx_soc_family_support", "bx_soc_social_support", "bx_soc_relationship",
    "bx_soc_personal_rel", "bx_soc_financial", "bx_soc_residential", "bx_soc_distance",
    # Medical barriers
    "b_med_red_flag", "b_med_substance", "b_med_as", "b_med_aaa",
    "b_med_vascular", "b_med_cervical_ha", "b_med_medico_legal",
    # Treatment Plan
    "tx_consent_explanation", "s1_consent_content", "tx_email_obtained", "tx_display_book",
    # Homework
    "hw_online_module", "hw_mindfulness", "hw_goal_sheet", "hw_activity_diary", "hw_sleep_diary",
    # Day 1 checklist
    "d1_explanation", "d1_session2", "d1_hypothesis", "d1_diagnosis", "d1_values",
    "d1_evidence", "d1_plan", "d1_prognosis", "d1_stakeholders", "d1_confidence_tested",
    "d1_questionnaires",
    # Post-session admin
    "ps_questionnaires", "ps_eppoc", "ps_ptsd_scored", "ps_isi_pbas", "ps_csi", "ps_audit_dudit",
]

_CYCLE_FIELDS = [
    "bx_dep_severity", "bx_anx_severity", "bx_stress_severity",
    "bx_ptsd_mechanism", "tx_pain_type", "tx_debunk_radiology",
]

_INPUT_FIELDS = [
    "bi_movement_region", "bi_strength_other", "bi_deep_other", "bi_over_other",
    "bi_nerve_region", "bi_red_flag_detail", "bi_substance_detail",
    "custom_1_barrier", "custom_1_strategy",
    "custom_2_barrier", "custom_2_strategy",
    "s1_confidence_nrs", "fu_om_schedule",
]

_TEXT_FIELDS = [
    "tx_goal_orientation", "tx_formulation",
    "tx_program", "tx_home_program",
    "tx_psychosocial", "tx_medical", "tx_rtw",
    "s1_education", "s1_experiential", "s1_hw_other",
    "fu_next_focus", "fu_monitoring",
]

# Barriers used for is_complete (any reviewed = section is started)
_MAIN_BARRIERS = [
    "b_noci_disease", "b_noci_pacing", "b_noci_inflammatory", "b_noci_deconditioning",
    "b_noci_movement", "b_noci_gait", "b_noci_strength", "b_noci_deep_muscle",
    "b_noci_overactivity", "b_noci_nerve_mech", "b_noci_diet",
    "b_neuro_confirmed", "b_neuro_unconfirmed",
    "b_nocip_moderate", "b_nocip_crps", "b_nocip_fnd",
    "b_psych_depression", "b_psych_anxiety", "b_psych_stress",
    "b_psych_catastrophising", "b_psych_self_efficacy", "b_psych_unhelpful_beliefs",
    "b_psych_ptsd", "b_psych_readiness",
    "b_sleep_disturbed",
    "b_social_home", "b_social_rtw",
    "b_med_red_flag", "b_med_substance", "b_med_as", "b_med_aaa",
    "b_med_vascular", "b_med_cervical_ha", "b_med_medico_legal",
]


# ---------------------------------------------------------------------------
# BarriersSection
# ---------------------------------------------------------------------------

class BarriersSection(BaseSection):
    """Barriers to Recovery & Treatment Plan section (core/07)."""

    DEFAULT_CSS = """
    BarriersSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #br_nav    { height: auto; }
    #br_scroll { width: 100%; height: 1fr; }
    #br_content { width: 100%; height: auto; padding: 0 1; }

    .section_title     { text-style: bold; margin-bottom: 0; }
    .subsection_header {
        text-style: bold; color: $primary;
        padding-top: 1; margin-bottom: 0;
    }
    .group_header {
        color: $text-muted; padding-top: 0; margin-bottom: 0;
    }
    .sub_item { padding-left: 2; }
    .reference_note { color: $text-muted; margin-bottom: 0; }

    Label  { margin-bottom: 0; }
    Input  { height: auto; min-height: 1; margin-bottom: 0; }
    TextArea { height: auto; min-height: 2; margin-bottom: 0; }

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

    def compose(self) -> ComposeResult:  # noqa: C901
        yield BrNavBar(on_jump_to=self._jump_to, id="br_nav")

        with ScrollableContainer(id="br_scroll"):
            with Vertical(id="br_content"):
                yield Label("Barriers to Recovery & Treatment Plan", classes="section_title")

                # ── Physical / Nociceptive ─────────────────────────────
                yield Label("— Physical / Nociceptive Barriers —", classes="subsection_header", id="br_physical")
                yield Static("", id="xref_br_noci", classes="xref_badge")

                yield YesNoField("Significant disease / pathology / physical factors — nociceptive", field_id="b_noci_disease")
                yield YesNoField("Significant pacing issues — boom-bust pattern", field_id="b_noci_pacing")
                yield YesNoField("Moderate severity inflammatory features", field_id="b_noci_inflammatory")
                yield YesNoField("Deconditioning (>50% activity reduction >3 months)", field_id="b_noci_deconditioning")

                yield YesNoField("Significant regional reduction in passive movement / resistance", field_id="b_noci_movement")
                yield Label("  Region / level:", classes="sub_item")
                yield Input(id="bi_movement_region", placeholder="region or level")

                yield YesNoField("Asymmetrical gait — moderate severity", field_id="b_noci_gait")

                yield YesNoField("Significant regional strength deficits", field_id="b_noci_strength")
                yield Label("  Specific muscles:", classes="sub_item")
                yield YesNoField("Gluteus maximus", field_id="bx_strength_glute_max", classes="sub_item")
                yield YesNoField("Gluteus medius / minimus", field_id="bx_strength_glute_med", classes="sub_item")
                yield YesNoField("Iliopsoas", field_id="bx_strength_iliopsoas", classes="sub_item")
                yield YesNoField("Quadriceps", field_id="bx_strength_quads", classes="sub_item")
                yield Label("  Other:", classes="sub_item")
                yield Input(id="bi_strength_other", placeholder="other muscle(s)")

                yield YesNoField("Reduced functional activation — deep / local / postural muscles", field_id="b_noci_deep_muscle")
                yield Label("  Specific muscles:", classes="sub_item")
                yield YesNoField("Lumbar multifidus", field_id="bx_deep_multifidus", classes="sub_item")
                yield YesNoField("Transversus abdominis", field_id="bx_deep_ta", classes="sub_item")
                yield YesNoField("Thoracic erector spinae", field_id="bx_deep_erector", classes="sub_item")
                yield Label("  Other:", classes="sub_item")
                yield Input(id="bi_deep_other", placeholder="other muscle(s)")

                yield YesNoField("Significant overactivity of muscles", field_id="b_noci_overactivity")
                yield Label("  Specific muscles:", classes="sub_item")
                yield YesNoField("Erector spinae", field_id="bx_over_erector", classes="sub_item")
                yield YesNoField("Quadratus lumborum", field_id="bx_over_ql", classes="sub_item")
                yield YesNoField("Rectus abdominis", field_id="bx_over_ra", classes="sub_item")
                yield YesNoField("External obliques", field_id="bx_over_obliques", classes="sub_item")
                yield YesNoField("Piriformis", field_id="bx_over_piriformis", classes="sub_item")
                yield YesNoField("Iliopsoas", field_id="bx_over_iliopsoas", classes="sub_item")
                yield YesNoField("Hamstrings", field_id="bx_over_hamstrings", classes="sub_item")
                yield YesNoField("Short hip adductors", field_id="bx_over_adductors", classes="sub_item")
                yield Label("  Other:", classes="sub_item")
                yield Input(id="bi_over_other", placeholder="other muscle(s)")

                yield YesNoField("Moderately increased nerve mechanosensitivity", field_id="b_noci_nerve_mech")
                yield Label("  Region:", classes="sub_item")
                yield Input(id="bi_nerve_region", placeholder="nerve / region")

                yield YesNoField("Relevant diet and / or weight issues", field_id="b_noci_diet")

                # ── Neuropathic ────────────────────────────────────────
                yield Label("— Neuropathic Barriers —", classes="subsection_header", id="br_neuro")
                yield Static("", id="xref_br_neuro", classes="xref_badge")

                yield YesNoField("Moderate neuropathic pain — confirmed nerve injury on investigations", field_id="b_neuro_confirmed")
                yield YesNoField("Moderate neuropathic pain — without confirmed nerve injury", field_id="b_neuro_unconfirmed")

                # ── Nociplastic ────────────────────────────────────────
                yield Label("— Nociplastic / Central Sensitisation Barriers —", classes="subsection_header", id="br_nocip")
                yield Static("", id="xref_br_nocip", classes="xref_badge")

                yield YesNoField("Moderate nociplastic pain including central sensitisation", field_id="b_nocip_moderate")
                yield YesNoField("Confirmed CRPS (Budapest criteria)", field_id="b_nocip_crps")
                yield YesNoField("Functional neurological disorder", field_id="b_nocip_fnd")

                # ── Psychological ──────────────────────────────────────
                yield Label("— Psychological Barriers —", classes="subsection_header", id="br_psych")

                yield YesNoField("Depression (DASS-21)", field_id="b_psych_depression")
                yield Static("", id="xref_br_depression", classes="xref_badge")
                yield Label("  Severity:", classes="sub_item")
                yield CycleField("bx_dep_severity", _DASS_SEVERITY_OPTIONS)
                yield YesNoField("Psychiatry referral", field_id="bx_dep_psychiatry", classes="sub_item")

                yield YesNoField("Anxiety (DASS-21)", field_id="b_psych_anxiety")
                yield Static("", id="xref_br_anxiety", classes="xref_badge")
                yield Label("  Severity:", classes="sub_item")
                yield CycleField("bx_anx_severity", _DASS_SEVERITY_OPTIONS)
                yield YesNoField("Psychiatry referral", field_id="bx_anx_psychiatry", classes="sub_item")

                yield YesNoField("Stress (DASS-21)", field_id="b_psych_stress")
                yield Static("", id="xref_br_stress", classes="xref_badge")
                yield Label("  Severity:", classes="sub_item")
                yield CycleField("bx_stress_severity", _DASS_SEVERITY_OPTIONS)
                yield YesNoField("Psychiatry referral", field_id="bx_stress_psychiatry", classes="sub_item")

                yield YesNoField("Moderate pain catastrophising (PCS)", field_id="b_psych_catastrophising")
                yield Static("", id="xref_br_catastrophising", classes="xref_badge")

                yield YesNoField("Reduced pain self-efficacy (PSEQ)", field_id="b_psych_self_efficacy")
                yield Static("", id="xref_br_self_efficacy", classes="xref_badge")

                yield YesNoField("Moderate unhelpful beliefs impacting pain management", field_id="b_psych_unhelpful_beliefs")
                yield Label("  Beliefs present:", classes="sub_item")
                yield YesNoField("Unrealistic recovery expectations", field_id="bx_belief_expectations", classes="sub_item")
                yield YesNoField("Strong symptom focus", field_id="bx_belief_symptom_focus", classes="sub_item")
                yield YesNoField("Strong cure focus", field_id="bx_belief_cure_focus", classes="sub_item")
                yield YesNoField("Desire for further treatment / investigations", field_id="bx_belief_further_tx", classes="sub_item")

                yield YesNoField("PTSD-type symptoms (PCL-5)", field_id="b_psych_ptsd")
                yield Static("", id="xref_br_ptsd", classes="xref_badge_urgent")
                yield Label("  Mechanism:", classes="sub_item")
                yield CycleField("bx_ptsd_mechanism", _PTSD_MECHANISM_OPTIONS)
                yield YesNoField("Psychiatry referral", field_id="bx_ptsd_psychiatry", classes="sub_item")

                yield YesNoField("Unclear readiness for change", field_id="b_psych_readiness")

                # ── Sleep ──────────────────────────────────────────────
                yield Label("— Sleep & Social / Contextual Barriers —", classes="subsection_header", id="br_sleep")

                yield YesNoField("Moderately disturbed sleep due to pain and / or rumination", field_id="b_sleep_disturbed")
                yield Static("", id="xref_br_sleep", classes="xref_badge")

                yield YesNoField("Moderate home / social barriers", field_id="b_social_home")
                yield Label("  Issues present:", classes="sub_item")
                yield YesNoField("Reduced family support",    field_id="bx_soc_family_support",  classes="sub_item")
                yield YesNoField("Reduced social support",    field_id="bx_soc_social_support",  classes="sub_item")
                yield YesNoField("Relationship issues (immediate family)", field_id="bx_soc_relationship", classes="sub_item")
                yield YesNoField("Personal relationship issues", field_id="bx_soc_personal_rel", classes="sub_item")
                yield YesNoField("Financial difficulties",    field_id="bx_soc_financial",       classes="sub_item")
                yield YesNoField("Residential instability",   field_id="bx_soc_residential",     classes="sub_item")
                yield YesNoField("Distance from program location", field_id="bx_soc_distance",   classes="sub_item")

                yield YesNoField("Moderate return-to-work barriers — physical and psychosocial", field_id="b_social_rtw")

                # ── Medical ────────────────────────────────────────────
                yield Label("— Medical / Systemic Barriers —", classes="subsection_header", id="br_medical")
                yield Static("", id="xref_br_red_flag", classes="xref_badge")

                yield YesNoField("Red flag — requires further investigation", field_id="b_med_red_flag")
                yield Label("  Flag:", classes="sub_item")
                yield Input(id="bi_red_flag_detail", placeholder="specify flag")

                yield YesNoField("Significant maladaptive use of prescription / non-prescription drugs / alcohol", field_id="b_med_substance")
                yield Static("", id="xref_br_substance", classes="xref_badge")
                yield Label("  Substance:", classes="sub_item")
                yield Input(id="bi_substance_detail", placeholder="substance")

                yield YesNoField("Possible ankylosing spondylitis", field_id="b_med_as")
                yield YesNoField("Possible lumbar symptoms due to AAA", field_id="b_med_aaa")
                yield YesNoField("Possible vascular claudication", field_id="b_med_vascular")
                yield YesNoField("Moderate severity cervical headache", field_id="b_med_cervical_ha")
                yield YesNoField("Medico-legal / claim issues", field_id="b_med_medico_legal")

                # ── Custom Barriers ────────────────────────────────────
                yield Label("— Custom Barriers —", classes="subsection_header", id="br_custom")
                yield Label("1. Barrier:")
                yield Input(id="custom_1_barrier", placeholder="barrier description")
                yield Label("   Strategy:")
                yield Input(id="custom_1_strategy", placeholder="treatment strategy")
                yield Label("2. Barrier:")
                yield Input(id="custom_2_barrier", placeholder="barrier description")
                yield Label("   Strategy:")
                yield Input(id="custom_2_strategy", placeholder="treatment strategy")

                # ── Treatment Plan Summary ─────────────────────────────
                yield Label("— Treatment Plan Summary —", classes="subsection_header", id="br_treatment")

                yield Label("Education — pain type explanation:")
                yield CycleField("tx_pain_type", _PAIN_TYPE_OPTIONS)
                yield YesNoField("Consent to discuss explanation", field_id="tx_consent_explanation")
                yield Label("Debunk radiology (if nociplastic):")
                yield CycleField("tx_debunk_radiology", _DEBUNK_OPTIONS)
                yield Label("Goal orientation:")
                yield TextArea(id="tx_goal_orientation", language="plain")
                yield Label("Formulation (why treatment will be effective):")
                yield TextArea(id="tx_formulation", language="plain")

                yield Label("Exercise / Rehabilitation — program:")
                yield TextArea(id="tx_program", language="plain")
                yield Label("Home program:")
                yield TextArea(id="tx_home_program", language="plain")

                yield Label("Psychosocial strategies:")
                yield TextArea(id="tx_psychosocial", language="plain")
                yield Label("Medical / Referral:")
                yield TextArea(id="tx_medical", language="plain")
                yield Label("RTW plan:")
                yield TextArea(id="tx_rtw", language="plain")

                # ── Session 1 Treatment ────────────────────────────────
                yield Label("— Session 1 Treatment —", classes="subsection_header", id="br_session1")
                yield Label("(Consider: (1) Specialist treatment; (2) Monitor treatment by others; (3) Referral)", classes="reference_note")

                yield Label("Education provided:")
                yield TextArea(id="s1_education", language="plain")
                yield Label("Experiential treatment (motor control / box breathing / other):")
                yield TextArea(id="s1_experiential", language="plain")
                yield YesNoField("Consent to discuss content", field_id="s1_consent_content")

                yield Label("Confidence / understanding NRS (0–10):")
                yield Input(id="s1_confidence_nrs", placeholder="0–10")

                yield Label("Homework set:")
                yield YesNoField("Online module — questions / reflections for next session", field_id="hw_online_module")
                yield YesNoField("Mindfulness / experiential practice", field_id="hw_mindfulness")
                yield YesNoField("Goal sheet", field_id="hw_goal_sheet")
                yield YesNoField("Activity diary", field_id="hw_activity_diary")
                yield YesNoField("Sleep diary", field_id="hw_sleep_diary")
                yield Label("Other homework:")
                yield TextArea(id="s1_hw_other", language="plain")

                yield YesNoField("Email obtained for resources", field_id="tx_email_obtained")
                yield YesNoField("Patient display book provided", field_id="tx_display_book")

                # ── Day 1 Checklist ────────────────────────────────────
                yield Label("— Day 1 Checklist —", classes="subsection_header", id="br_day1")

                yield YesNoField("Clear and simple explanation delivered", field_id="d1_explanation")
                yield YesNoField("Importance of Session 2 communicated", field_id="d1_session2")
                yield YesNoField("Complexity and hypothesis testing articulated", field_id="d1_hypothesis")
                yield YesNoField("Diagnosis and formulation provided (implies pain type)", field_id="d1_diagnosis")
                yield YesNoField("Patient values / preferences / goals articulated", field_id="d1_values")
                yield YesNoField("Evidence discussed (ePPOC and RCTs referenced)", field_id="d1_evidence")
                yield YesNoField("Short and long term plan provided", field_id="d1_plan")
                yield YesNoField("Prognosis and prevention discussed", field_id="d1_prognosis")
                yield YesNoField("Other stakeholders identified (work, family, health practitioners)", field_id="d1_stakeholders")
                yield YesNoField("Confidence / understanding tested", field_id="d1_confidence_tested")
                yield YesNoField("Questionnaires administered (individualised set)", field_id="d1_questionnaires")

                # ── Follow-Up Plan ─────────────────────────────────────
                yield Label("— Follow-Up Plan —", classes="subsection_header", id="br_followup")

                yield Label("Next session focus:")
                yield TextArea(id="fu_next_focus", language="plain")
                yield Label("Monitoring:")
                yield TextArea(id="fu_monitoring", language="plain")
                yield Label("Outcome measure re-testing schedule:")
                yield Input(id="fu_om_schedule", placeholder="schedule")

                yield Label("Post-Session Admin:")
                yield YesNoField("Questionnaires scored", field_id="ps_questionnaires")
                yield YesNoField("ePPOC components completed", field_id="ps_eppoc")
                yield YesNoField("PTSD screen scored (if administered)", field_id="ps_ptsd_scored")
                yield YesNoField("ISI and PBAS scored (if sleep is primary problem)", field_id="ps_isi_pbas")
                yield YesNoField("CSI scored", field_id="ps_csi")
                yield YesNoField("AUDIT / DUDIT scored (if administered)", field_id="ps_audit_dudit")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#br_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
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
        pc   = _sec("pain_classification")
        om   = _sec("outcome_measures")
        dx   = _sec("diagnosis")

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

        # Nociceptive — dominant pain type
        lines = []
        dominant = pc.get("summary_dominant")
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        mech = dx.get("mechanism")
        if mech:
            lines.append(f"Dx: mechanism = {mech}")
        _set("xref_br_noci", lines)

        # Neuropathic
        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        if med.get("rf_saddle_anaesthesia") is True:
            lines.append("Med: saddle anaesthesia (red flag +ve)")
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        _set("xref_br_neuro", lines)

        # Nociplastic
        lines = []
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        if dx.get("primary_subtype") == "CRPS type I":
            lines.append("Dx: CRPS type I selected")
        _set("xref_br_nocip", lines)

        # Depression
        lines = []
        score = om.get("dass_dep_score", "").strip()
        interp = om.get("dass_dep_interp")
        if score:
            lines.append(f"OM: DASS depression score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_depression", lines)

        # Anxiety
        lines = []
        score = om.get("dass_anx_score", "").strip()
        interp = om.get("dass_anx_interp")
        if score:
            lines.append(f"OM: DASS anxiety score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_anxiety", lines)

        # Stress
        lines = []
        score = om.get("dass_str_score", "").strip()
        interp = om.get("dass_str_interp")
        if score:
            lines.append(f"OM: DASS stress score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_stress", lines)

        # Catastrophising
        lines = []
        score = om.get("pcs_total_score", "").strip()
        risk = om.get("pcs_total_risk")
        if score:
            lines.append(f"OM: PCS total = {score}" + (f" ({risk})" if risk else ""))
        _set("xref_br_catastrophising", lines)

        # Self-efficacy
        lines = []
        score = om.get("pseq_score", "").strip()
        if score:
            lines.append(f"OM: PSEQ score = {score}")
        _set("xref_br_self_efficacy", lines)

        # PTSD (urgent)
        lines = []
        score = om.get("pcl5_score", "").strip()
        interp = om.get("pcl5_interp")
        if score:
            lines.append(f"OM: PCL-5 score = {score}" + (f" ({interp})" if interp else ""))
        if subj.get("self_harm_risk") is True:
            lines.append("Subj: self-harm risk flagged")
        _set("xref_br_ptsd", lines, urgent=True)

        # Sleep
        lines = []
        score = om.get("isi_score", "").strip()
        interp = om.get("isi_interp")
        if score:
            lines.append(f"OM: ISI score = {score}" + (f" ({interp})" if interp else ""))
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty reported")
        _set("xref_br_sleep", lines)

        # Red flag
        rf_fields = [
            ("rf_saddle_anaesthesia",    "saddle anaesthesia"),
            ("rf_bladder_disturbance",   "bladder disturbance"),
            ("rf_bowel_disturbance",     "bowel disturbance"),
            ("rf_bilateral_paraesthesia","bilateral paraesthesia"),
            ("rf_gait_disturbance",      "gait disturbance"),
        ]
        lines = [f"Med: {label} +ve" for fid, label in rf_fields if med.get(fid) is True]
        _set("xref_br_red_flag", lines)

        # Substance
        lines = []
        if med.get("comorbid_drug_alcohol") is True:
            lines.append("Med: drug / alcohol comorbidity flagged")
        _set("xref_br_substance", lines)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in _TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", YesNoField).get_value()
            except Exception:
                data[fid] = None
        for fid in _CYCLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CycleField).get_value()
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
            br = data if isinstance(data, dict) else {}
            for fid in _TOGGLE_FIELDS:
                if fid in br:
                    try:
                        self.query_one(f"#{fid}", YesNoField).set_value(br[fid])
                    except Exception:
                        pass
            for fid in _CYCLE_FIELDS:
                if fid in br:
                    try:
                        self.query_one(f"#{fid}", CycleField).set_value(br[fid])
                    except Exception:
                        pass
            for fid in _INPUT_FIELDS:
                if fid in br:
                    try:
                        self.query_one(f"#{fid}", Input).value = br[fid]
                    except Exception:
                        pass
            for fid in _TEXT_FIELDS:
                if fid in br:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = br[fid]
                    except Exception:
                        pass
        finally:
            self._loading = False
            self.update_cross_refs()

    def is_complete(self) -> bool:
        """Complete when at least one main barrier has been explicitly reviewed (True or False)."""
        for fid in _MAIN_BARRIERS:
            try:
                if self.query_one(f"#{fid}", YesNoField).get_value() is not None:
                    return True
            except Exception:
                pass
        return False

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
