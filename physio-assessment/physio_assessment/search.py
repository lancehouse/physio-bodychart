"""Search index builder and fuzzy scorer for the jump-search (ctrl+.) feature."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from textual.app import App

# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class SearchEntry:
    display: str         # shown in the dropdown row
    match_text: str      # text fuzzy-matched against the query
    section_id: str      # section to navigate to
    anchor_id: str | None   # subsection anchor ID (or None)
    widget_id: str | None   # specific widget to focus (or None)
    kind: Literal["section", "subsection", "field", "content"]


# ---------------------------------------------------------------------------
# Static tables
# ---------------------------------------------------------------------------

_SECTION_SHORT: dict[str, str] = {
    "01_consent":             "Consent",
    "02_subjective":          "Subj",
    "03_medical":             "Medical",
    "04_pain_classification": "Pain",
    "05_outcome_measures":    "Outcomes",
    "06_diagnosis":           "Diagnosis",
    "07_barriers":            "Barriers",
    "08_rx_plan":             "Rx Plan",
    "scratchpad":             "Notes",
    "01_general":             "Obj:General",
    "02_active":              "Obj:Active",
    "03_passive":             "Obj:Passive",
    "04_neurological":        "Obj:Neuro",
    "05_sensory":             "Obj:Sensory",
    "06_muscle":              "Obj:Muscle",
    "07_functional":          "Obj:Functional",
}

_SECTION_LABELS: dict[str, str] = {
    "01_consent":             "01 Consent",
    "02_subjective":          "02 Subjective",
    "03_medical":             "03 Medical",
    "04_pain_classification": "04 Pain Classification",
    "05_outcome_measures":    "05 Outcome Measures",
    "06_diagnosis":           "06 Diagnosis",
    "07_barriers":            "07 Barriers",
    "08_rx_plan":             "08 Rx & Plan",
    "scratchpad":             "Notes / Scratchpad",
    "01_general":             "Obj 01 General",
    "02_active":              "Obj 02 Active Movement",
    "03_passive":             "Obj 03 Passive Movement",
    "04_neurological":        "Obj 04 Neurological",
    "05_sensory":             "Obj 05 Sensory",
    "06_muscle":              "Obj 06 Muscle Testing",
    "07_functional":          "Obj 07 Functional",
}

# (section_id, anchor_id, display_label)
_SUBSECTIONS: list[tuple[str, str, str]] = [
    # 02 Subjective
    ("02_subjective", "subj_symptoms",     "Body Chart Symptoms"),
    ("02_subjective", "subj_history",      "History"),
    ("02_subjective", "subj_flareups",     "Flare-ups"),
    ("02_subjective", "subj_management",   "Self-Management"),
    ("02_subjective", "subj_activity",     "Activity & Exercise"),
    ("02_subjective", "subj_work",         "Work"),
    ("02_subjective", "subj_sleep",        "Sleep"),
    ("02_subjective", "subj_24hr",         "24Hr Pattern"),
    ("02_subjective", "subj_psychosocial", "Psychosocial"),
    ("02_subjective", "subj_suicide",      "Suicide / Self-Harm Risk"),
    # 03 Medical
    ("03_medical", "med_comorbidities",    "Comorbidities / PMH"),
    ("03_medical", "med_cardiovascular",   "Cardiovascular Risk"),
    ("03_medical", "med_red_flags",        "Red Flags"),
    ("03_medical", "rf_malignancy",        "Red Flag: Malignancy"),
    ("03_medical", "rf_fracture",          "Red Flag: Fracture"),
    ("03_medical", "rf_infection",         "Red Flag: Infection"),
    ("03_medical", "rf_cauda_equina",      "Red Flag: Cauda Equina Compression"),
    ("03_medical", "rf_spinal_cord",       "Red Flag: Spinal Cord Compression"),
    ("03_medical", "rf_umn_signs",         "Red Flag: Upper Motor Neurone Signs"),
    ("03_medical", "med_differential",     "Differential Diagnosis"),
    ("03_medical", "diff_as",              "Differential: Ankylosing Spondylitis"),
    ("03_medical", "diff_aaa",             "Differential: Aortic Aneurysm"),
    ("03_medical", "diff_vc",              "Differential: Vascular Claudication"),
    ("03_medical", "med_medications",      "Medications"),
    # 04 Pain Classification
    ("04_pain_classification", "pc_inflammatory", "Inflammatory"),
    ("04_pain_classification", "pc_nociceptive",  "Nociceptive"),
    ("04_pain_classification", "pc_neuropathic",  "Neuropathic"),
    ("04_pain_classification", "pc_nociplastic",  "Nociplastic"),
    ("04_pain_classification", "pc_central",      "Central Sensitisation"),
    ("04_pain_classification", "pc_summary",      "Pain Classification Summary"),
    # 05 Outcome Measures
    ("05_outcome_measures", "om_psfs",       "PSFS"),
    ("05_outcome_measures", "om_bpi",        "BPI"),
    ("05_outcome_measures", "om_dass",       "DASS"),
    ("05_outcome_measures", "om_pcs",        "PCS"),
    ("05_outcome_measures", "om_pseq",       "PSEQ / PCL-5"),
    ("05_outcome_measures", "om_sleep",      "ISI / Sleep"),
    ("05_outcome_measures", "om_additional", "Additional Measures"),
    ("05_outcome_measures", "om_hypothesis", "Outcome Hypothesis"),
    # 06 Diagnosis
    ("06_diagnosis", "dx_overview",    "Overview"),
    ("06_diagnosis", "dx_primary",     "Primary Diagnosis"),
    ("06_diagnosis", "dx_surgical",    "Post-Surgical"),
    ("06_diagnosis", "dx_traumatic",   "Post-Traumatic"),
    ("06_diagnosis", "dx_msk",         "MSK"),
    ("06_diagnosis", "dx_neuropathic", "Neuropathic Diagnosis"),
    ("06_diagnosis", "dx_mixed",       "Mixed"),
    ("06_diagnosis", "dx_goals",       "Goals"),
    # 07 Barriers
    ("07_barriers", "br_physical",     "Physical Barriers"),
    ("07_barriers", "br_neuro",        "Neurological Barriers"),
    ("07_barriers", "br_nocip",        "Nociplastic Barriers"),
    ("07_barriers", "br_psych",        "Psychological Barriers"),
    ("07_barriers", "br_sleep",        "Sleep & Social Barriers"),
    ("07_barriers", "br_medical",      "Medical Barriers"),
    ("07_barriers", "br_custom",       "Custom Barriers"),
    # 08 Rx Plan
    ("08_rx_plan", "rp_treatment",     "Treatment Plan"),
    ("08_rx_plan", "rp_session1",      "Session 1"),
    ("08_rx_plan", "rp_day1",          "Day 1 Programme"),
    ("08_rx_plan", "rp_followup",      "Follow-Up"),
    # Objective subsections (IDs added to objective section files)
    ("01_general", "go_physical",            "General: Physical"),
    ("01_general", "go_posture",             "General: Posture"),
    ("01_general", "go_functional_movement", "General: Functional Movement"),
    ("02_active",  "am_lumbar",              "Active: Lumbar ROM"),
    ("02_active",  "am_thoracic",            "Active: Thoracic ROM"),
    ("03_passive", "pm_overpressure",        "Passive: Overpressure"),
    ("03_passive", "pm_paivms",              "Passive: PAIVMs"),
    ("04_neurological", "nr_reflexes",       "Neuro: Reflexes"),
    ("04_neurological", "nr_myotomes",       "Neuro: Myotomes"),
    ("04_neurological", "nr_dermatomes",     "Neuro: Dermatomes"),
    ("04_neurological", "nr_neurodynamics",  "Neuro: Neurodynamics"),
    ("04_neurological", "nr_umn",            "Neuro: UMN Signs"),
    ("05_sensory",  "sn_hyposensitivity",    "Sensory: Hyposensitivity"),
    ("05_sensory",  "sn_hypersensitivity",   "Sensory: Hypersensitivity"),
    ("06_muscle",   "ml_length",             "Muscle: Length"),
    ("06_muscle",   "ml_activation",         "Muscle: Activation"),
    ("06_muscle",   "ml_strength_trunk",     "Muscle: Strength (Trunk)"),
    ("06_muscle",   "ml_strength_hip",       "Muscle: Strength (Hip)"),
    ("06_muscle",   "ml_sij",               "Muscle: SIJ Provocation"),
    ("07_functional", "fn_movement",         "Functional: Movement"),
    ("07_functional", "fn_balance",          "Functional: Balance"),
    ("07_functional", "fn_timed",            "Functional: Timed Capability"),
]

# Pre-built lookup: (section_id, anchor_id) -> subsection label
_SUBSECTION_LABEL: dict[tuple[str, str], str] = {
    (s, a): lbl for s, a, lbl in _SUBSECTIONS
}

# widget_id -> (section_id, anchor_id_or_None, human_name)
_FIELD_LABELS: dict[str, tuple[str, str | None, str]] = {
    # 01 Consent
    "preferred_name_input":       ("01_consent", None, "Preferred name"),
    "patient_expectations":       ("01_consent", None, "Patient expectations"),
    "reason_for_attending":       ("01_consent", None, "Reason for attending"),
    "cause_understanding_detail": ("01_consent", None, "Cause understanding"),
    "prognosis_expectations":     ("01_consent", None, "Prognosis expectations"),
    "treatment_preference":       ("01_consent", None, "Treatment preference"),
    # 02 Subjective — History
    "onset":              ("02_subjective", "subj_history",    "Onset"),
    "duration":           ("02_subjective", "subj_history",    "Duration"),
    "context_at_onset":   ("02_subjective", "subj_history",    "Context at onset"),
    "previous_episodes":  ("02_subjective", "subj_history",    "Previous episodes"),
    "previous_treatment": ("02_subjective", "subj_history",    "Previous treatment"),
    # 02 Subjective — Flare-ups
    "flareup_triggers":       ("02_subjective", "subj_flareups", "Flare-up triggers"),
    "flareup_predictability": ("02_subjective", "subj_flareups", "Flare-up predictability"),
    "flareup_duration":       ("02_subjective", "subj_flareups", "Flare-up duration"),
    # 02 Subjective — Management
    "pain_control_score":    ("02_subjective", "subj_management", "Pain control score"),
    "flareup_prevention":    ("02_subjective", "subj_management", "Flare-up prevention"),
    "management_strategies": ("02_subjective", "subj_management", "Management strategies"),
    "confidence_score":      ("02_subjective", "subj_management", "Confidence score"),
    # 02 Subjective — Activity
    "pre_activity_level":     ("02_subjective", "subj_activity", "Pre-injury activity"),
    "current_activity_level": ("02_subjective", "subj_activity", "Current activity"),
    "exercise_type":          ("02_subjective", "subj_activity", "Exercise type"),
    "exercise_dose":          ("02_subjective", "subj_activity", "Exercise dose"),
    "exercise_response":      ("02_subjective", "subj_activity", "Exercise response"),
    # 02 Subjective — Work
    "pre_injury_role":    ("02_subjective", "subj_work", "Pre-injury role"),
    "pre_injury_hours":   ("02_subjective", "subj_work", "Pre-injury hours"),
    "pre_injury_duties":  ("02_subjective", "subj_work", "Pre-injury duties"),
    "current_work_status":("02_subjective", "subj_work", "Current work status"),
    "current_hours":      ("02_subjective", "subj_work", "Current hours"),
    "current_duties":     ("02_subjective", "subj_work", "Current duties"),
    # 02 Subjective — Sleep
    "bed_description":           ("02_subjective", "subj_sleep", "Bed/pillow description"),
    "sleep_difficulty_severity": ("02_subjective", "subj_sleep", "Sleep difficulty severity"),
    "sleep_onset_time":          ("02_subjective", "subj_sleep", "Time to fall asleep"),
    "sleep_position":            ("02_subjective", "subj_sleep", "Sleep position"),
    "total_sleep_hours":         ("02_subjective", "subj_sleep", "Total sleep hours"),
    "night_waking_frequency":    ("02_subjective", "subj_sleep", "Night waking frequency"),
    "night_waking_reason":       ("02_subjective", "subj_sleep", "Night waking reason"),
    "bed_exits_count":           ("02_subjective", "subj_sleep", "Bed exits count"),
    "night_waking_severity":     ("02_subjective", "subj_sleep", "Night waking severity"),
    "morning_stiffness":         ("02_subjective", "subj_sleep", "Morning pain & stiffness"),
    "nap_frequency":             ("02_subjective", "subj_sleep", "Nap frequency"),
    "nap_duration":              ("02_subjective", "subj_sleep", "Nap duration"),
    # 02 Subjective — 24hr
    "hr24_am":               ("02_subjective", "subj_24hr", "AM pattern"),
    "hr24_day":              ("02_subjective", "subj_24hr", "Daytime pattern"),
    "hr24_pm":               ("02_subjective", "subj_24hr", "PM pattern"),
    "hr24_nocte":            ("02_subjective", "subj_24hr", "Night (nocte) pattern"),
    "energy_levels":         ("02_subjective", "subj_24hr", "Energy levels"),
    "daily_pattern_comments":("02_subjective", "subj_24hr", "Daily pattern comments"),
    # 02 Subjective — Psychosocial
    "mood_text":               ("02_subjective", "subj_psychosocial", "Mood (text)"),
    "social_situation":        ("02_subjective", "subj_psychosocial", "Social situation"),
    "financial_status":        ("02_subjective", "subj_psychosocial", "Financial status"),
    "cultural_considerations": ("02_subjective", "subj_psychosocial", "Cultural considerations"),
    "psychological_distress":  ("02_subjective", "subj_psychosocial", "Psychological distress"),
    "screening_tool":          ("02_subjective", "subj_psychosocial", "Screening tool"),
    # 02 Subjective — Suicide risk
    "harm_plan":   ("02_subjective", "subj_suicide", "Self-harm plan"),
    "harm_means":  ("02_subjective", "subj_suicide", "Self-harm means"),
    "harm_intent": ("02_subjective", "subj_suicide", "Self-harm intent"),
    "harm_action": ("02_subjective", "subj_suicide", "Self-harm action taken"),
    # 03 Medical
    "previous_injuries":     ("03_medical", "med_comorbidities",  "Previous injuries"),
    "comorbid_other":        ("03_medical", "med_comorbidities",  "Other comorbidities"),
    "rf_malignancy_comment": ("03_medical", "med_red_flags",      "Malignancy comment"),
    "rf_fracture_comment":   ("03_medical", "med_red_flags",      "Fracture comment"),
    "rf_infection_comment":  ("03_medical", "med_red_flags",      "Infection comment"),
    "cauda_equina_action":   ("03_medical", "med_red_flags",      "Cauda equina action"),
    "spinal_cord_action":    ("03_medical", "med_red_flags",      "Spinal cord action"),
    "umn_interpretation":    ("03_medical", "med_red_flags",      "UMN interpretation"),
    "diff_as_action":        ("03_medical", "med_differential",   "Ankylosing spondylitis action"),
    "diff_aaa_action":       ("03_medical", "med_differential",   "AAA action"),
    "diff_vc_action":        ("03_medical", "med_differential",   "Vascular claudication action"),
    # 04 Pain Classification
    "noci_interpretation":  ("04_pain_classification", "pc_nociceptive", "Nociceptive interpretation"),
    "neuro_interpretation": ("04_pain_classification", "pc_neuropathic", "Neuropathic interpretation"),
    "nocip_interpretation": ("04_pain_classification", "pc_nociplastic", "Nociplastic interpretation"),
    "csi_score":            ("04_pain_classification", "pc_nociplastic", "CSI score"),
    "summary_contributing": ("04_pain_classification", "pc_summary",     "Contributing factors"),
    "summary_reasoning":    ("04_pain_classification", "pc_summary",     "Classification reasoning"),
    # 05 Outcome Measures
    "psfs_score":    ("05_outcome_measures", "om_psfs",       "PSFS total score"),
    "psfs_act_1":    ("05_outcome_measures", "om_psfs",       "PSFS activity 1"),
    "psfs_act_2":    ("05_outcome_measures", "om_psfs",       "PSFS activity 2"),
    "psfs_act_3":    ("05_outcome_measures", "om_psfs",       "PSFS activity 3"),
    "psfs_act_4":    ("05_outcome_measures", "om_psfs",       "PSFS activity 4"),
    "psfs_act_5":    ("05_outcome_measures", "om_psfs",       "PSFS activity 5"),
    "bpi_activity":  ("05_outcome_measures", "om_bpi",        "BPI: Activity"),
    "bpi_mood":      ("05_outcome_measures", "om_bpi",        "BPI: Mood"),
    "bpi_walking":   ("05_outcome_measures", "om_bpi",        "BPI: Walking"),
    "bpi_work":      ("05_outcome_measures", "om_bpi",        "BPI: Work"),
    "bpi_relations": ("05_outcome_measures", "om_bpi",        "BPI: Relations"),
    "bpi_sleep":     ("05_outcome_measures", "om_bpi",        "BPI: Sleep"),
    "bpi_enjoyment": ("05_outcome_measures", "om_bpi",        "BPI: Enjoyment"),
    "dass_dep_score": ("05_outcome_measures", "om_dass",      "DASS: Depression"),
    "dass_anx_score": ("05_outcome_measures", "om_dass",      "DASS: Anxiety"),
    "dass_str_score": ("05_outcome_measures", "om_dass",      "DASS: Stress"),
    "pcs_rum_score":  ("05_outcome_measures", "om_pcs",       "PCS: Rumination"),
    "pcs_mag_score":  ("05_outcome_measures", "om_pcs",       "PCS: Magnification"),
    "pcs_help_score": ("05_outcome_measures", "om_pcs",       "PCS: Helplessness"),
    "pcs_total_score":("05_outcome_measures", "om_pcs",       "PCS: Total"),
    "pseq_score":    ("05_outcome_measures", "om_pseq",       "PSEQ score"),
    "pcl5_score":    ("05_outcome_measures", "om_pseq",       "PCL-5 score"),
    "pcl5_action":   ("05_outcome_measures", "om_pseq",       "PCL-5 action"),
    "isi_score":     ("05_outcome_measures", "om_sleep",      "ISI score"),
    "pbas_score":    ("05_outcome_measures", "om_sleep",      "PBAS score"),
    "add_epoc":      ("05_outcome_measures", "om_additional", "EPOC notes"),
    # 06 Diagnosis
    "surgical_procedure": ("06_diagnosis", "dx_surgical",    "Surgical procedure"),
    "surgical_source":    ("06_diagnosis", "dx_surgical",    "Surgical source"),
    "traumatic_event":    ("06_diagnosis", "dx_traumatic",   "Traumatic event"),
    "traumatic_source":   ("06_diagnosis", "dx_traumatic",   "Traumatic source"),
    "msk_pathology":      ("06_diagnosis", "dx_msk",         "MSK pathology"),
    "msk_source":         ("06_diagnosis", "dx_msk",         "MSK source"),
    "neuro_lesion":       ("06_diagnosis", "dx_neuropathic", "Neurological lesion"),
    "mixed_reasoning":    ("06_diagnosis", "dx_mixed",       "Mixed reasoning"),
    "goal_1":             ("06_diagnosis", "dx_goals",       "Goal 1"),
    "goal_2":             ("06_diagnosis", "dx_goals",       "Goal 2"),
    "goal_3":             ("06_diagnosis", "dx_goals",       "Goal 3"),
    "goal_4":             ("06_diagnosis", "dx_goals",       "Goal 4"),
    # 07 Barriers
    "bi_movement_region": ("07_barriers", "br_physical",  "Movement region"),
    "bi_strength_other":  ("07_barriers", "br_physical",  "Other strength deficit"),
    "bi_deep_other":      ("07_barriers", "br_physical",  "Other deep stability deficit"),
    "bi_over_other":      ("07_barriers", "br_physical",  "Other overactivity"),
    "bi_nerve_region":    ("07_barriers", "br_neuro",     "Nerve region"),
    "bi_red_flag_detail": ("07_barriers", "br_medical",   "Red flag detail"),
    "bi_substance_detail":("07_barriers", "br_medical",   "Substance detail"),
    "custom_1_barrier":   ("07_barriers", "br_custom",    "Custom barrier 1"),
    "custom_1_strategy":  ("07_barriers", "br_custom",    "Custom strategy 1"),
    "custom_2_barrier":   ("07_barriers", "br_custom",    "Custom barrier 2"),
    "custom_2_strategy":  ("07_barriers", "br_custom",    "Custom strategy 2"),
    # 08 Rx Plan
    "tx_goal_orientation":("08_rx_plan", "rp_treatment",  "Goal orientation"),
    "tx_formulation":     ("08_rx_plan", "rp_treatment",  "Treatment formulation"),
    "tx_program":         ("08_rx_plan", "rp_treatment",  "Treatment program"),
    "tx_home_program":    ("08_rx_plan", "rp_treatment",  "Home program"),
    "tx_psychosocial":    ("08_rx_plan", "rp_treatment",  "Psychosocial treatment"),
    "tx_medical":         ("08_rx_plan", "rp_treatment",  "Medical treatment"),
    "tx_rtw":             ("08_rx_plan", "rp_treatment",  "Return to work plan"),
    "s1_education":       ("08_rx_plan", "rp_session1",   "Session 1: Education"),
    "s1_experiential":    ("08_rx_plan", "rp_session1",   "Session 1: Experiential"),
    "s1_confidence_nrs":  ("08_rx_plan", "rp_session1",   "Session 1: Confidence NRS"),
    "s1_hw_other":        ("08_rx_plan", "rp_session1",   "Session 1: HW other"),
    "fu_next_focus":      ("08_rx_plan", "rp_followup",   "Follow-up: Next focus"),
    "fu_monitoring":      ("08_rx_plan", "rp_followup",   "Follow-up: Monitoring"),
    "fu_om_schedule":     ("08_rx_plan", "rp_followup",   "Follow-up: OM schedule"),
    # Scratchpad
    "scratchpad_text": ("scratchpad", None, "Scratchpad notes"),
}

# Assessment sections to harvest button widgets from (objective excluded)
_ASSESSMENT_SECTION_IDS = [
    "01_consent", "02_subjective", "03_medical", "04_pain_classification",
    "05_outcome_measures", "06_diagnosis", "07_barriers", "08_rx_plan", "scratchpad",
]


# ---------------------------------------------------------------------------
# Fuzzy scoring
# ---------------------------------------------------------------------------

def fuzzy_score(query: str, target: str) -> int:
    """Return match score > 0 if query fuzzy-matches target. Higher = better."""
    if not query:
        return 0
    q, t = query.lower(), target.lower()
    if q == t:
        return 1000
    if t.startswith(q):
        return 900
    if q in t:
        return 800 - t.index(q)
    # Character subsequence
    idx = 0
    gaps = 0
    for ch in q:
        pos = t.find(ch, idx)
        if pos == -1:
            return 0
        gaps += pos - idx
        idx = pos + 1
    return max(1, 200 - gaps)


def _snippet(text: str, max_len: int = 48) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:max_len] + ("…" if len(line) > max_len else "")
    return ""


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def build_index(app: "App") -> list[SearchEntry]:
    """Build a fresh search index from live app state."""
    from .assessment_view import AssessmentView
    from .widgets import CheckButton
    from textual.widgets import TextArea, Input as TInput

    entries: list[SearchEntry] = []

    # 1 — Sections
    for sec_id, label in _SECTION_LABELS.items():
        entries.append(SearchEntry(
            display=label,
            match_text=label,
            section_id=sec_id,
            anchor_id=None,
            widget_id=None,
            kind="section",
        ))

    # 2 — Subsections
    for sec_id, anchor_id, label in _SUBSECTIONS:
        short = _SECTION_SHORT.get(sec_id, sec_id)
        entries.append(SearchEntry(
            display=f"{short} › {label}",
            match_text=f"{label} {short}",
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=None,
            kind="subsection",
        ))

    try:
        av = app.query_one("#assessment_view", AssessmentView)
    except Exception:
        return entries

    # 3 — CheckButton / FlagButton labels (assessment sections only)
    for sec_id in _ASSESSMENT_SECTION_IDS:
        section = av.sections.get(sec_id)
        if section is None:
            continue
        short = _SECTION_SHORT.get(sec_id, sec_id)
        try:
            for btn in section.query(CheckButton):
                if not btn.id:
                    continue
                name = getattr(btn, "base_name", None) or str(btn.label)
                entries.append(SearchEntry(
                    display=f"{short} › {name}",
                    match_text=f"{name} {short}",
                    section_id=sec_id,
                    anchor_id=None,
                    widget_id=btn.id,
                    kind="field",
                ))
        except Exception:
            pass

    # 4 — Named text field entries (from _FIELD_LABELS)
    for widget_id, (sec_id, anchor_id, human_name) in _FIELD_LABELS.items():
        short = _SECTION_SHORT.get(sec_id, sec_id)
        subsec = _SUBSECTION_LABEL.get((sec_id, anchor_id), "") if anchor_id else ""
        if subsec:
            display = f"{short} › {subsec} › {human_name}"
        else:
            display = f"{short} › {human_name}"
        entries.append(SearchEntry(
            display=display,
            match_text=f"{human_name} {short}",
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=widget_id,
            kind="field",
        ))

    # 5 — Content entries (non-empty TextArea / Input values)
    for widget_id, (sec_id, anchor_id, human_name) in _FIELD_LABELS.items():
        section = av.sections.get(sec_id)
        if section is None:
            continue
        short = _SECTION_SHORT.get(sec_id, sec_id)
        try:
            widget = section.query_one(f"#{widget_id}")
        except Exception:
            continue
        if isinstance(widget, TextArea):
            text = widget.text
        elif isinstance(widget, TInput):
            text = widget.value
        else:
            continue
        if not text.strip():
            continue
        snip = _snippet(text)
        entries.append(SearchEntry(
            display=f"{short} › {human_name}: '{snip}'",
            match_text=text,
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=widget_id,
            kind="content",
        ))

    return entries


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_entries(
    query: str,
    index: list[SearchEntry],
    max_results: int = 10,
) -> list[SearchEntry]:
    """Return up to max_results best-scoring entries for query."""
    if not query.strip():
        return []
    scored: list[tuple[int, int, SearchEntry]] = []
    for i, entry in enumerate(index):
        score = fuzzy_score(query, entry.match_text)
        if score > 0:
            scored.append((score, -i, entry))
    scored.sort(reverse=True)
    return [e for _, _, e in scored[:max_results]]
