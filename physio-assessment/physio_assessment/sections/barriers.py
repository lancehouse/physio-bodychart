"""Barriers to Recovery & Treatment Plan section (core/07).

Note: the spec calls for tick-driven auto-population of the treatment plan and
output table (ui-hint: auto-generated). That is deferred to a future phase;
all treatment plan fields are free-text editable for now.
"""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import ScrollableContainer
from textual.widgets import Label, Input, TextArea, Static
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton
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
        height: auto;
        padding: 0 1;
    }

    .section_title     { text-style: bold; margin-bottom: 0; }
    .subsection_header {
        text-style: bold; color: $primary;
        padding-top: 1; margin-bottom: 0;
    }
    .group_header {
        color: $text-muted; padding-top: 0; margin-bottom: 0;
    }
    .reference_note { color: $text-muted; margin-bottom: 0; }

    Label  { margin-bottom: 0; }
    Input  { height: auto; min-height: 1; margin-bottom: 0; }
    TextArea { height: auto; min-height: 2; margin-bottom: 0; }

    CheckButton { width: 100%; height: auto; margin-bottom: 0; }
    CheckButton.sub_item { margin-left: 2; width: auto; }

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
        yield Label("Barriers to Recovery & Treatment Plan", classes="section_title")

        # ── Physical / Nociceptive ─────────────────────────────
        yield Label("— Physical / Nociceptive Barriers —", classes="subsection_header", id="br_physical")
        yield Static("", id="xref_br_noci", classes="xref_badge")

        yield CheckButton("Significant disease / pathology / physical factors — nociceptive", id="b_noci_disease")
        yield CheckButton("Significant pacing issues — boom-bust pattern", id="b_noci_pacing")
        yield CheckButton("Moderate severity inflammatory features", id="b_noci_inflammatory")
        yield CheckButton("Deconditioning (>50% activity reduction >3 months)", id="b_noci_deconditioning")

        yield CheckButton("Significant regional reduction in passive movement / resistance", id="b_noci_movement")
        yield Label("  Region / level:")
        yield Input(id="bi_movement_region", placeholder="region or level")

        yield CheckButton("Asymmetrical gait — moderate severity", id="b_noci_gait")

        yield CheckButton("Significant regional strength deficits", id="b_noci_strength")
        yield Label("  Specific muscles:")
        yield CheckButton("Gluteus maximus", id="bx_strength_glute_max", classes="sub_item")
        yield CheckButton("Gluteus medius / minimus", id="bx_strength_glute_med", classes="sub_item")
        yield CheckButton("Iliopsoas", id="bx_strength_iliopsoas", classes="sub_item")
        yield CheckButton("Quadriceps", id="bx_strength_quads", classes="sub_item")
        yield Label("  Other:")
        yield Input(id="bi_strength_other", placeholder="other muscle(s)")

        yield CheckButton("Reduced functional activation — deep / local / postural muscles", id="b_noci_deep_muscle")
        yield Label("  Specific muscles:")
        yield CheckButton("Lumbar multifidus", id="bx_deep_multifidus", classes="sub_item")
        yield CheckButton("Transversus abdominis", id="bx_deep_ta", classes="sub_item")
        yield CheckButton("Thoracic erector spinae", id="bx_deep_erector", classes="sub_item")
        yield Label("  Other:")
        yield Input(id="bi_deep_other", placeholder="other muscle(s)")

        yield CheckButton("Significant overactivity of muscles", id="b_noci_overactivity")
        yield Label("  Specific muscles:")
        yield CheckButton("Erector spinae", id="bx_over_erector", classes="sub_item")
        yield CheckButton("Quadratus lumborum", id="bx_over_ql", classes="sub_item")
        yield CheckButton("Rectus abdominis", id="bx_over_ra", classes="sub_item")
        yield CheckButton("External obliques", id="bx_over_obliques", classes="sub_item")
        yield CheckButton("Piriformis", id="bx_over_piriformis", classes="sub_item")
        yield CheckButton("Iliopsoas", id="bx_over_iliopsoas", classes="sub_item")
        yield CheckButton("Hamstrings", id="bx_over_hamstrings", classes="sub_item")
        yield CheckButton("Short hip adductors", id="bx_over_adductors", classes="sub_item")
        yield Label("  Other:")
        yield Input(id="bi_over_other", placeholder="other muscle(s)")

        yield CheckButton("Moderately increased nerve mechanosensitivity", id="b_noci_nerve_mech")
        yield Label("  Region:")
        yield Input(id="bi_nerve_region", placeholder="nerve / region")

        yield CheckButton("Relevant diet and / or weight issues", id="b_noci_diet")

        # ── Neuropathic ────────────────────────────────────────
        yield Label("— Neuropathic Barriers —", classes="subsection_header", id="br_neuro")
        yield Static("", id="xref_br_neuro", classes="xref_badge")

        yield CheckButton("Moderate neuropathic pain — confirmed nerve injury on investigations", id="b_neuro_confirmed")
        yield CheckButton("Moderate neuropathic pain — without confirmed nerve injury", id="b_neuro_unconfirmed")

        # ── Nociplastic ────────────────────────────────────────
        yield Label("— Nociplastic / Central Sensitisation Barriers —", classes="subsection_header", id="br_nocip")
        yield Static("", id="xref_br_nocip", classes="xref_badge")

        yield CheckButton("Moderate nociplastic pain including central sensitisation", id="b_nocip_moderate")
        yield CheckButton("Confirmed CRPS (Budapest criteria)", id="b_nocip_crps")
        yield CheckButton("Functional neurological disorder", id="b_nocip_fnd")

        # ── Psychological ──────────────────────────────────────
        yield Label("— Psychological Barriers —", classes="subsection_header", id="br_psych")

        yield CheckButton("Depression (DASS-21)", id="b_psych_depression")
        yield Static("", id="xref_br_depression", classes="xref_badge")
        yield Label("  Severity:")
        yield CycleField("bx_dep_severity", _DASS_SEVERITY_OPTIONS)
        yield CheckButton("Psychiatry referral", id="bx_dep_psychiatry", classes="sub_item")

        yield CheckButton("Anxiety (DASS-21)", id="b_psych_anxiety")
        yield Static("", id="xref_br_anxiety", classes="xref_badge")
        yield Label("  Severity:")
        yield CycleField("bx_anx_severity", _DASS_SEVERITY_OPTIONS)
        yield CheckButton("Psychiatry referral", id="bx_anx_psychiatry", classes="sub_item")

        yield CheckButton("Stress (DASS-21)", id="b_psych_stress")
        yield Static("", id="xref_br_stress", classes="xref_badge")
        yield Label("  Severity:")
        yield CycleField("bx_stress_severity", _DASS_SEVERITY_OPTIONS)
        yield CheckButton("Psychiatry referral", id="bx_stress_psychiatry", classes="sub_item")

        yield CheckButton("Moderate pain catastrophising (PCS)", id="b_psych_catastrophising")
        yield Static("", id="xref_br_catastrophising", classes="xref_badge")

        yield CheckButton("Reduced pain self-efficacy (PSEQ)", id="b_psych_self_efficacy")
        yield Static("", id="xref_br_self_efficacy", classes="xref_badge")

        yield CheckButton("Moderate unhelpful beliefs impacting pain management", id="b_psych_unhelpful_beliefs")
        yield Label("  Beliefs present:")
        yield CheckButton("Unrealistic recovery expectations", id="bx_belief_expectations", classes="sub_item")
        yield CheckButton("Strong symptom focus", id="bx_belief_symptom_focus", classes="sub_item")
        yield CheckButton("Strong cure focus", id="bx_belief_cure_focus", classes="sub_item")
        yield CheckButton("Desire for further treatment / investigations", id="bx_belief_further_tx", classes="sub_item")

        yield CheckButton("PTSD-type symptoms (PCL-5)", id="b_psych_ptsd")
        yield Static("", id="xref_br_ptsd", classes="xref_badge_urgent")
        yield Label("  Mechanism:")
        yield CycleField("bx_ptsd_mechanism", _PTSD_MECHANISM_OPTIONS)
        yield CheckButton("Psychiatry referral", id="bx_ptsd_psychiatry", classes="sub_item")

        yield CheckButton("Unclear readiness for change", id="b_psych_readiness")

        # ── Sleep ──────────────────────────────────────────────
        yield Label("— Sleep & Social / Contextual Barriers —", classes="subsection_header", id="br_sleep")

        yield CheckButton("Moderately disturbed sleep due to pain and / or rumination", id="b_sleep_disturbed")
        yield Static("", id="xref_br_sleep", classes="xref_badge")

        yield CheckButton("Moderate home / social barriers", id="b_social_home")
        yield Label("  Issues present:")
        yield CheckButton("Reduced family support", id="bx_soc_family_support", classes="sub_item")
        yield CheckButton("Reduced social support", id="bx_soc_social_support", classes="sub_item")
        yield CheckButton("Relationship issues (immediate family)", id="bx_soc_relationship", classes="sub_item")
        yield CheckButton("Personal relationship issues", id="bx_soc_personal_rel", classes="sub_item")
        yield CheckButton("Financial difficulties", id="bx_soc_financial", classes="sub_item")
        yield CheckButton("Residential instability", id="bx_soc_residential", classes="sub_item")
        yield CheckButton("Distance from program location", id="bx_soc_distance", classes="sub_item")

        yield CheckButton("Moderate return-to-work barriers — physical and psychosocial", id="b_social_rtw")

        # ── Medical ────────────────────────────────────────────
        yield Label("— Medical / Systemic Barriers —", classes="subsection_header", id="br_medical")
        yield Static("", id="xref_br_red_flag", classes="xref_badge")

        yield CheckButton("Red flag — requires further investigation", id="b_med_red_flag")
        yield Label("  Flag:")
        yield Input(id="bi_red_flag_detail", placeholder="specify flag")

        yield CheckButton("Significant maladaptive use of prescription / non-prescription drugs / alcohol", id="b_med_substance")
        yield Static("", id="xref_br_substance", classes="xref_badge")
        yield Label("  Substance:")
        yield Input(id="bi_substance_detail", placeholder="substance")

        yield CheckButton("Possible ankylosing spondylitis", id="b_med_as")
        yield CheckButton("Possible lumbar symptoms due to AAA", id="b_med_aaa")
        yield CheckButton("Possible vascular claudication", id="b_med_vascular")
        yield CheckButton("Moderate severity cervical headache", id="b_med_cervical_ha")
        yield CheckButton("Medico-legal / claim issues", id="b_med_medico_legal")

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
        yield CheckButton("Consent to discuss explanation", id="tx_consent_explanation")
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
        yield CheckButton("Consent to discuss content", id="s1_consent_content")

        yield Label("Confidence / understanding NRS (0–10):")
        yield Input(id="s1_confidence_nrs", placeholder="0–10")

        yield Label("Homework set:")
        yield CheckButton("Online module — questions / reflections for next session", id="hw_online_module")
        yield CheckButton("Mindfulness / experiential practice", id="hw_mindfulness")
        yield CheckButton("Goal sheet", id="hw_goal_sheet")
        yield CheckButton("Activity diary", id="hw_activity_diary")
        yield CheckButton("Sleep diary", id="hw_sleep_diary")
        yield Label("Other homework:")
        yield TextArea(id="s1_hw_other", language="plain")

        yield CheckButton("Email obtained for resources", id="tx_email_obtained")
        yield CheckButton("Patient display book provided", id="tx_display_book")

        # ── Day 1 Checklist ────────────────────────────────────
        yield Label("— Day 1 Checklist —", classes="subsection_header", id="br_day1")

        yield CheckButton("Clear and simple explanation delivered", id="d1_explanation")
        yield CheckButton("Importance of Session 2 communicated", id="d1_session2")
        yield CheckButton("Complexity and hypothesis testing articulated", id="d1_hypothesis")
        yield CheckButton("Diagnosis and formulation provided (implies pain type)", id="d1_diagnosis")
        yield CheckButton("Patient values / preferences / goals articulated", id="d1_values")
        yield CheckButton("Evidence discussed (ePPOC and RCTs referenced)", id="d1_evidence")
        yield CheckButton("Short and long term plan provided", id="d1_plan")
        yield CheckButton("Prognosis and prevention discussed", id="d1_prognosis")
        yield CheckButton("Other stakeholders identified (work, family, health practitioners)", id="d1_stakeholders")
        yield CheckButton("Confidence / understanding tested", id="d1_confidence_tested")
        yield CheckButton("Questionnaires administered (individualised set)", id="d1_questionnaires")

        # ── Follow-Up Plan ─────────────────────────────────────
        yield Label("— Follow-Up Plan —", classes="subsection_header", id="br_followup")

        yield Label("Next session focus:")
        yield TextArea(id="fu_next_focus", language="plain")
        yield Label("Monitoring:")
        yield TextArea(id="fu_monitoring", language="plain")
        yield Label("Outcome measure re-testing schedule:")
        yield Input(id="fu_om_schedule", placeholder="schedule")

        yield Label("Post-Session Admin:")
        yield CheckButton("Questionnaires scored", id="ps_questionnaires")
        yield CheckButton("ePPOC components completed", id="ps_eppoc")
        yield CheckButton("PTSD screen scored (if administered)", id="ps_ptsd_scored")
        yield CheckButton("ISI and PBAS scored (if sleep is primary problem)", id="ps_isi_pbas")
        yield CheckButton("CSI scored", id="ps_csi")
        yield CheckButton("AUDIT / DUDIT scored (if administered)", id="ps_audit_dudit")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(target, top=True)
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
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
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
                        self.query_one(f"#{fid}", CheckButton).set_value(br[fid])
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
                if self.query_one(f"#{fid}", CheckButton).value is not None:
                    return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(CheckButton.Changed)
    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
