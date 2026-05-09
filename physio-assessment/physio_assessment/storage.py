"""
Session storage — read/write assessment data to session JSON files.

Handles atomic writes via temp file + rename to prevent JSON corruption.
Preserves GTK-owned sections (subjective, objective) while updating
Python-owned assessment block.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def load_assessment(session_file: str) -> dict:
    """
    Load assessment block from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_assessment(session_file: str, assessment: dict) -> bool:
    """
    Merge assessment block into session JSON, preserving all GTK sections.

    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Update assessment block with timestamp
        if "assessment" not in data:
            data["assessment"] = {}

        data["assessment"].update(assessment)
        data["assessment"]["modified"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)  # atomic on POSIX

        logger.debug(f"Saved assessment to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save assessment to {session_file}: {e}")
        return False


def load_session_current() -> Optional[dict]:
    """
    Load the active session pointer from session_current.json.

    Returns None if file doesn't exist or can't be parsed.
    """
    session_current = Path.home() / ".local/share/physio-bodychart/session_current.json"

    if not session_current.exists():
        return None

    try:
        return json.loads(session_current.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session_current.json: {e}")
        return None


def list_sessions() -> list[dict]:
    """
    List all assessment sessions from GTK storage directory.

    Returns list of session dicts with: path, patient_id, session_label,
    date, regions, body_chart_data, sections_complete
    """
    sessions = []
    physio_root = Path.home() / "Physio-Bodychart"

    if not physio_root.exists():
        return sessions

    # Scan all session directories
    for session_dir in sorted(physio_root.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue

        # Look for session.json in this directory
        session_file = session_dir / f"{session_dir.name}_session.json"
        if not session_file.exists():
            continue

        try:
            data = json.loads(session_file.read_text())

            # Extract session metadata
            session = {
                "path": str(session_file),
                "patient_id": data.get("patient_id", "XX"),
                "session_label": data.get("session_label", ""),
                "date": data.get("date") or data.get("created", 0),
                "regions": data.get("regions", []),
                "body_chart_data": bool(
                    data.get("subjective", {}).get("strokes") or
                    data.get("subjective", {}).get("notes") or
                    data.get("objective", {}).get("zones") or
                    data.get("objective", {}).get("points")
                ),
                "sections_complete": count_complete_sections(data),
            }
            sessions.append(session)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read session {session_file}: {e}")
            continue

    return sessions


def count_complete_sections(session_data: dict) -> int:
    """Count how many assessment sections have content."""
    sections = get_sections_complete(session_data)
    return sum(1 for v in sections.values() if v)


def get_sections_complete(session_data: dict) -> dict[str, bool]:
    """
    Check completion status of each core section.

    Returns dict mapping section_id to completion status.
    """
    assessment = session_data.get("assessment", {})
    complete_status = {}

    # Special handling for 01_consent (has its own sub-block)
    consent = assessment.get("consent", {})
    complete_status["01_consent"] = (
        consent.get("consent_to_proceed") is True
        and bool(consent.get("preferred_name", "").strip())
    )

    # Define remaining sections and their mandatory fields
    sections = {
        "02_subjective": {
            "assessment_fields": ["history"],
        },
        "03_medical": {
            "assessment_fields": [],  # completion driven by save_medical via sections_complete
        },
        "04_pain_classification": {
            "assessment_fields": [],
        },
        "05_outcome_measures": {
            "assessment_fields": [],
        },
        "06_diagnosis": {
            "assessment_fields": [],
        },
        "07_barriers": {
            "assessment_fields": [],
        },
    }

    # Check all other sections
    for section_id, section_def in sections.items():
        # Check if all mandatory assessment fields have content
        all_filled = True
        for field in section_def["assessment_fields"]:
            if not assessment.get(field, "").strip():
                all_filled = False
                break

        complete_status[section_id] = all_filled

    return complete_status


def is_section_complete(session_data: dict, section_id: str) -> bool:
    """Check if a specific section is complete."""
    sections = get_sections_complete(session_data)
    return sections.get(section_id, False)


def mark_section_complete(session_file: str, section_id: str) -> bool:
    """
    Mark a section as complete in the session.

    Returns True on success.
    """
    path = Path(session_file)
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text())

        # Initialize sections_complete if needed
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        # Mark this section complete
        data["sections_complete"][section_id] = True
        data["sections_last_modified"][section_id] = int(time.time())

        # Atomic write
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        return True
    except Exception as e:
        logger.error(f"Failed to mark section complete: {e}")
        return False


def get_resume_section(session_data: dict) -> str:
    """
    Find the first incomplete section to resume from.

    Returns section ID to open. If all complete, returns last section.
    """
    section_order = [
        "01_consent",
        "02_subjective",
        "03_medical",
        "04_pain_classification",
        "05_outcome_measures",
        "06_diagnosis",
        "07_barriers",
    ]

    # Check sections in order
    for section_id in section_order:
        if not is_section_complete(session_data, section_id):
            return section_id

    # All complete; return last section
    return section_order[-1]


def load_consent(session_file: str) -> dict:
    """
    Load consent data from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("consent", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_consent(session_file: str, consent: dict) -> bool:
    """
    Merge consent data into session JSON, preserving all other sections.

    Updates sections_complete["01_consent"] based on consent data.
    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Ensure assessment block exists
        if "assessment" not in data:
            data["assessment"] = {}

        # Merge consent into assessment.consent
        if "consent" not in data["assessment"]:
            data["assessment"]["consent"] = {}
        data["assessment"]["consent"].update(consent)

        # Calculate completion for 01_consent
        is_complete = (
            consent.get("consent_to_proceed") is True
            and bool(consent.get("preferred_name", "").strip())
        )

        # Update sections_complete
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        data["sections_complete"]["01_consent"] = is_complete
        data["sections_last_modified"]["01_consent"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved consent to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save consent to {session_file}: {e}")
        return False


def load_subjective(session_file: str) -> dict:
    """
    Load subjective assessment data from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("subjective", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_subjective(session_file: str, subjective: dict) -> bool:
    """
    Merge subjective assessment data into session JSON, preserving all other sections.

    Updates sections_complete["02_subjective"] based on subjective data.
    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Ensure assessment block exists
        if "assessment" not in data:
            data["assessment"] = {}

        # Merge subjective into assessment.subjective
        if "subjective" not in data["assessment"]:
            data["assessment"]["subjective"] = {}
        data["assessment"]["subjective"].update(subjective)

        # Calculate completion for 02_subjective (self-harm risk assessed)
        is_complete = subjective.get("self_harm_risk") is not None

        # Update sections_complete
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        data["sections_complete"]["02_subjective"] = is_complete
        data["sections_last_modified"]["02_subjective"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved subjective to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save subjective to {session_file}: {e}")
        return False


def load_medical(session_file: str) -> dict:
    """Load medical screening data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("medical", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_medical(session_file: str, medical: dict) -> bool:
    """Merge medical screening data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "medical" not in data["assessment"]:
            data["assessment"]["medical"] = {}
        data["assessment"]["medical"].update(medical)

        # Complete when all urgent red flag fields have been explicitly reviewed
        urgent = [
            "rf_saddle_anaesthesia", "rf_bladder_disturbance", "rf_bowel_disturbance",
            "rf_bilateral_paraesthesia", "rf_gait_disturbance",
        ]
        is_complete = all(medical.get(fid) is not None for fid in urgent)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["03_medical"] = is_complete
        data["sections_last_modified"]["03_medical"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved medical to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save medical to {session_file}: {e}")
        return False


def load_pain_classification(session_file: str) -> dict:
    """Load pain classification data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("pain_classification", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_pain_classification(session_file: str, pain: dict) -> bool:
    """Merge pain classification data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "pain_classification" not in data["assessment"]:
            data["assessment"]["pain_classification"] = {}
        data["assessment"]["pain_classification"].update(pain)

        is_complete = pain.get("summary_dominant") is not None

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["04_pain_classification"] = is_complete
        data["sections_last_modified"]["04_pain_classification"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved pain_classification to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save pain_classification to {session_file}: {e}")
        return False


def load_outcome_measures(session_file: str) -> dict:
    """Load outcome measures data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("outcome_measures", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_outcome_measures(session_file: str, om: dict) -> bool:
    """Merge outcome measures data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "outcome_measures" not in data["assessment"]:
            data["assessment"]["outcome_measures"] = {}
        data["assessment"]["outcome_measures"].update(om)

        main_scores = ["psfs_score", "bpi_activity", "dass_dep_score",
                       "pcs_total_score", "pseq_score", "pcl5_score", "isi_score"]
        is_complete = any(om.get(f, "").strip() for f in main_scores)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["05_outcome_measures"] = is_complete
        data["sections_last_modified"]["05_outcome_measures"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved outcome_measures to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save outcome_measures to {session_file}: {e}")
        return False


def load_diagnosis(session_file: str) -> dict:
    """Load diagnosis data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("diagnosis", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_diagnosis(session_file: str, dx: dict) -> bool:
    """Merge diagnosis data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        data["assessment"]["diagnosis"] = dx

        is_complete = dx.get("mechanism") is not None

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["06_diagnosis"] = is_complete
        data["sections_last_modified"]["06_diagnosis"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved diagnosis to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save diagnosis to {session_file}: {e}")
        return False


def load_barriers(session_file: str) -> dict:
    """Load barriers and treatment plan data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("barriers", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_barriers(session_file: str, barriers: dict) -> bool:
    """Merge barriers and treatment plan data into session JSON."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        data["assessment"]["barriers"] = barriers

        # Complete when any main barrier has been explicitly reviewed (True or False)
        main_barriers = [
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
        is_complete = any(barriers.get(fid) is not None for fid in main_barriers)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["07_barriers"] = is_complete
        data["sections_last_modified"]["07_barriers"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved barriers to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save barriers to {session_file}: {e}")
        return False


def write_tui_pid(pid: int) -> None:
    """Write the TUI process PID into session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
        data["tui_pid"] = pid
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"write_tui_pid: {e}")


def read_gtk_pid() -> int | None:
    """Read the GTK process PID from session_current.json. Returns None if absent."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text())
        pid = data.get("gtk_pid")
        return int(pid) if pid else None
    except Exception:
        return None


def read_tui_socket() -> str | None:
    """Read the kitty remote-control socket path from session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text())
        return data.get("tui_socket") or None
    except Exception:
        return None


def focus_signal_path(session_file: str, target: str) -> Path:
    """Return path to a focus signal file (.focus_gtk or .focus_tui) in the session dir."""
    return Path(session_file).parent / f".focus_{target}"


def write_focus_signal(session_file: str, target: str) -> None:
    """Write a focus signal file. The other app watches for this and raises its window."""
    try:
        focus_signal_path(session_file, target).touch()
    except Exception as e:
        logger.warning(f"write_focus_signal({target}): {e}")


# ---------------------------------------------------------------------------
# Session report export
# ---------------------------------------------------------------------------

def _yn(val) -> str:
    if val is True:  return "Yes"
    if val is False: return "No"
    return ""


def _row(*pairs) -> str:
    """Format key-value pairs on one line, skipping empty values."""
    parts = [f"**{k}:** {v}" for k, v in pairs if v not in (None, "", [])]
    return "  ".join(parts) if parts else ""


def export_session_report(session_file: str) -> str:
    """
    Write a compact Markdown assessment report to <session_dir>/<name>_report.md.
    Returns the output path, or empty string on failure.
    """
    try:
        data = json.loads(Path(session_file).read_text())
    except Exception as e:
        logger.error(f"export_session_report: {e}")
        return ""

    session_dir  = Path(session_file).parent
    session_name = data.get("session_name", "session")
    out_path     = session_dir / f"{session_name}_report.md"

    import time as _time
    created = data.get("created", 0)
    date_str = _time.strftime("%d %b %Y", _time.localtime(created)) if created else ""

    lines: list[str] = []

    def h1(text):  lines.append(f"# {text}\n")
    def h2(text):  lines.append(f"## {text}")
    def row(*pairs): r = _row(*pairs); lines.append(r) if r else None
    def text(label, val):
        if val and val.strip():
            lines.append(f"**{label}:** {val.strip()}")
    def gap(): lines.append("")

    a = data.get("assessment", {})

    # ── Title ──────────────────────────────────────────────────────────────
    pid   = data.get("patient_id", "")
    label = data.get("session_label", "")
    h1(f"Physiotherapy Assessment — {pid}")
    row(("Session", label), ("Date", date_str))
    gap()

    # ── 01 Consent ─────────────────────────────────────────────────────────
    c = a.get("consent", {})
    if isinstance(c, dict) and c:
        h2("01 Consent")
        row(("Preferred name", c.get("preferred_name")),
            ("Consent to proceed", _yn(c.get("consent_to_proceed"))),
            ("Consent (sensitive topics)", _yn(c.get("consent_sensitive_topics"))))
        row(("Pain multifactorial explained", _yn(c.get("pain_multifactorial_explained"))),
            ("Education as treatment explained", _yn(c.get("education_as_treatment_explained"))))
        text("Reason for attending", c.get("reason_for_attending"))
        text("Patient expectations", c.get("patient_expectations"))
        row(("Cause understanding", _yn(c.get("cause_understanding"))),
            ("Detail", c.get("cause_understanding_detail")))
        text("Prognosis expectations", c.get("prognosis_expectations"))
        text("Treatment preference", c.get("treatment_preference"))
        gap()

    # ── 02 Subjective ──────────────────────────────────────────────────────
    s = a.get("subjective", {})
    if isinstance(s, dict) and s:
        h2("02 Subjective Examination")
        text("History", s.get("history"))
        row(("Duration", s.get("duration")), ("Onset", s.get("onset")))
        row(("Current NRS", s.get("nrs_current")),
            ("Best", s.get("nrs_best")), ("Worst", s.get("nrs_worst")))
        row(("24-hr pattern", s.get("behaviour_24hr")))
        row(("Course", s.get("course")),
            ("Improving", _yn(s.get("course_improving"))),
            ("Worsening", _yn(s.get("course_worsening"))))
        text("Context at onset", s.get("context_at_onset"))
        text("Previous treatment", s.get("previous_treatment"))
        row(("Sleep difficulty", _yn(s.get("sleep_difficulty"))),
            ("Night waking", _yn(s.get("night_waking"))),
            ("Total sleep hrs", s.get("total_sleep_hours")))
        row(("Aggravating factors", s.get("aggravating_factors")))
        row(("Easing factors", s.get("easing_factors")))
        row(("Morning stiffness", _yn(s.get("morning_stiffness"))),
            ("Stiffness duration", s.get("morning_stiffness_duration")))
        row(("Mood influences", _yn(s.get("mood_influences"))),
            ("Psychological distress", _yn(s.get("psychological_distress"))))
        row(("Self-harm risk", _yn(s.get("self_harm_risk"))),
            ("Harm plan", _yn(s.get("harm_plan"))))
        row(("PSEQ confidence", s.get("confidence_score")))
        gap()

    # ── 03 Medical ─────────────────────────────────────────────────────────
    m = a.get("medical", {})
    if isinstance(m, dict) and m:
        h2("03 Medical Screening")
        # Red flags
        rf_map = [
            ("rf_saddle_anaesthesia", "Saddle anaesthesia"),
            ("rf_bladder_disturbance", "Bladder disturbance"),
            ("rf_bowel_disturbance", "Bowel disturbance"),
            ("rf_bilateral_paraesthesia", "Bilateral paraesthesia"),
            ("rf_gait_disturbance", "Gait disturbance"),
        ]
        positives = [label for fid, label in rf_map if m.get(fid) is True]
        if positives:
            lines.append(f"**Red flags +ve:** {', '.join(positives)}")
        comorbid_map = [
            ("comorbid_cardiovascular", "Cardiovascular"),
            ("comorbid_diabetes", "Diabetes"),
            ("comorbid_cancer", "Cancer"),
            ("comorbid_inflammatory", "Inflammatory arthritis"),
            ("comorbid_fibromyalgia", "Fibromyalgia"),
            ("comorbid_mental_health", "Mental health"),
            ("comorbid_drug_alcohol", "Drug/alcohol"),
            ("comorbid_whiplash", "Whiplash"),
        ]
        comorbid = [label for fid, label in comorbid_map if m.get(fid) is True]
        if comorbid:
            lines.append(f"**Comorbidities:** {', '.join(comorbid)}")
        meds = [m.get(f"medication_{i}_name", "").strip() for i in range(1, 6)]
        meds = [x for x in meds if x]
        if meds:
            lines.append(f"**Medications:** {', '.join(meds)}")
        gap()

    # ── 04 Pain Classification ─────────────────────────────────────────────
    pc = a.get("pain_classification", {})
    if isinstance(pc, dict) and pc:
        h2("04 Pain Classification")
        row(("Dominant type", pc.get("summary_dominant")),
            ("Secondary", pc.get("summary_secondary")))
        text("Reasoning", pc.get("summary_reasoning"))
        gap()

    # ── 05 Outcome Measures ────────────────────────────────────────────────
    om = a.get("outcome_measures", {})
    if isinstance(om, dict) and om:
        h2("05 Outcome Measures")
        score_map = [
            ("psfs_score", "psfs_interp",    "PSFS"),
            ("bpi_activity","",              "BPI activity"),
            ("dass_dep_score","dass_dep_interp","DASS dep"),
            ("dass_anx_score","dass_anx_interp","DASS anx"),
            ("dass_str_score","dass_str_interp","DASS stress"),
            ("pcs_total_score","pcs_total_risk","PCS total"),
            ("pseq_score","",               "PSEQ"),
            ("pcl5_score","pcl5_interp",    "PCL-5"),
            ("isi_score","isi_interp",      "ISI"),
            ("pbas_score","pbas_interp",    "PBAS"),
        ]
        parts = []
        for sfid, ifid, label in score_map:
            score = om.get(sfid, "").strip()
            if score:
                interp = om.get(ifid, "").strip() if ifid else ""
                parts.append(f"{label} {score}" + (f" ({interp})" if interp else ""))
        if parts:
            lines.append("  ".join(parts))
        goals = [om.get(f"psfs_goal_{i}", "").strip() for i in range(1, 6)]
        goals = [g for g in goals if g]
        if goals:
            lines.append(f"**PSFS goals:** {'; '.join(goals)}")
        gap()

    # ── 06 Diagnosis ──────────────────────────────────────────────────────
    dx = a.get("diagnosis", {})
    if isinstance(dx, dict) and dx:
        h2("06 Diagnosis")
        row(("Duration >3 months", _yn(dx.get("duration_over_3_months"))),
            ("Mechanism", dx.get("mechanism")))
        row(("Primary subtype", dx.get("primary_subtype")),
            ("Severity", dx.get("primary_severity")))
        row(("Surgical subtype", dx.get("surgical_subtype")),
            ("Procedure", dx.get("surgical_procedure")))
        row(("Traumatic subtype", dx.get("traumatic_subtype")),
            ("Event", dx.get("traumatic_event")))
        row(("MSK subtype", dx.get("msk_subtype")),
            ("Pathology", dx.get("msk_pathology")))
        row(("Neuro subtype", dx.get("neuro_subtype")),
            ("Lesion", dx.get("neuro_lesion")))
        row(("Mixed dominant", dx.get("mixed_dominant")))
        text("Mixed reasoning", dx.get("mixed_reasoning"))
        goals = [dx.get(f"goal_{i}", "").strip() for i in range(1, 5)]
        goals = [g for g in goals if g]
        if goals:
            lines.append("**SMART Goals:**")
            for i, g in enumerate(goals, 1):
                lines.append(f"{i}. {g}")
        gap()

    # ── 07 Barriers ────────────────────────────────────────────────────────
    br = a.get("barriers", {})
    if isinstance(br, dict) and br:
        h2("07 Barriers & Treatment Plan")
        barrier_map = [
            ("b_noci_disease",        "Disease/pathology"),
            ("b_noci_pacing",         "Pacing issues"),
            ("b_noci_inflammatory",   "Inflammatory features"),
            ("b_noci_deconditioning", "Deconditioning"),
            ("b_noci_movement",       "Reduced movement"),
            ("b_noci_gait",           "Asymmetrical gait"),
            ("b_noci_strength",       "Strength deficits"),
            ("b_noci_deep_muscle",    "Deep muscle activation"),
            ("b_noci_overactivity",   "Muscle overactivity"),
            ("b_noci_nerve_mech",     "Nerve mechanosensitivity"),
            ("b_noci_diet",           "Diet/weight"),
            ("b_neuro_confirmed",     "Neuropathic (confirmed)"),
            ("b_neuro_unconfirmed",   "Neuropathic (unconfirmed)"),
            ("b_nocip_moderate",      "Nociplastic/CS"),
            ("b_nocip_crps",          "CRPS"),
            ("b_nocip_fnd",           "FND"),
            ("b_psych_depression",    "Depression"),
            ("b_psych_anxiety",       "Anxiety"),
            ("b_psych_stress",        "Stress"),
            ("b_psych_catastrophising","Catastrophising"),
            ("b_psych_self_efficacy", "Reduced self-efficacy"),
            ("b_psych_unhelpful_beliefs","Unhelpful beliefs"),
            ("b_psych_ptsd",          "PTSD symptoms"),
            ("b_psych_readiness",     "Unclear readiness"),
            ("b_sleep_disturbed",     "Disturbed sleep"),
            ("b_social_home",         "Home/social barriers"),
            ("b_social_rtw",          "RTW barriers"),
            ("b_med_red_flag",        "Red flag"),
            ("b_med_substance",       "Substance use"),
            ("b_med_as",              "Possible AS"),
            ("b_med_aaa",             "Possible AAA"),
            ("b_med_vascular",        "Vascular claudication"),
            ("b_med_cervical_ha",     "Cervical headache"),
            ("b_med_medico_legal",    "Medico-legal"),
        ]
        present = [label for fid, label in barrier_map if br.get(fid) is True]
        if present:
            lines.append(f"**Barriers identified:** {', '.join(present)}")
        # Treatment plan
        text("Goal orientation", br.get("tx_goal_orientation"))
        text("Formulation", br.get("tx_formulation"))
        text("Program", br.get("tx_program"))
        text("Home program", br.get("tx_home_program"))
        text("Psychosocial strategies", br.get("tx_psychosocial"))
        text("Medical/referral", br.get("tx_medical"))
        text("RTW plan", br.get("tx_rtw"))
        # Follow-up
        text("Next session focus", br.get("fu_next_focus"))
        text("Monitoring", br.get("fu_monitoring"))
        gap()

    # ── Write ──────────────────────────────────────────────────────────────
    try:
        out_path.write_text("\n".join(lines))
        logger.info(f"Report written to {out_path}")
        return str(out_path)
    except Exception as e:
        logger.error(f"export_session_report write failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Scratchpad load / save
# ---------------------------------------------------------------------------

def load_scratchpad(session_file: str) -> dict:
    """Load scratchpad data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("scratchpad", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_scratchpad(session_file: str, scratchpad: dict) -> bool:
    """Merge scratchpad data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        data["assessment"]["scratchpad"] = scratchpad
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved scratchpad to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save scratchpad to {session_file}: {e}")
        return False


# ---------------------------------------------------------------------------
# Unified all-sections save
# ---------------------------------------------------------------------------

def save_all_sections(
    session_file: str,
    assessment: dict,
    sections_complete: dict[str, bool],
) -> bool:
    """
    Save all assessment sections in a single atomic write.

    Reads the current JSON to preserve body chart and other top-level data,
    replaces each named section under assessment.{key}, updates
    sections_complete and sections_last_modified, then writes atomically.

    assessment keys must match the JSON sub-keys:
      consent, subjective, medical, pain_classification,
      outcome_measures, diagnosis, barriers, scratchpad
    """
    path = Path(session_file)
    try:
        data = json.loads(path.read_text()) if path.exists() else {}

        if "assessment" not in data:
            data["assessment"] = {}
        for key, val in assessment.items():
            data["assessment"][key] = val
        data["assessment"]["modified"] = int(time.time())

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        now = int(time.time())
        for section_id, complete in sections_complete.items():
            data["sections_complete"][section_id] = complete
            data["sections_last_modified"][section_id] = now

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved all sections to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save all sections to {session_file}: {e}")
        return False


# ---------------------------------------------------------------------------
# Raw report export
# ---------------------------------------------------------------------------

LABELS: dict[str, str] = {
    # ── 01 Consent ──────────────────────────────────────────────────────────
    "consent_to_proceed":               "Consent to proceed",
    "consent_sensitive_topics":         "Consent to discuss sensitive topics",
    "preferred_name":                   "Preferred name",
    "pain_multifactorial_explained":    "Pain as multifactorial explained",
    "education_as_treatment_explained": "Education as part of treatment explained",
    "patient_expectations":             "Patient expectations",
    "reason_for_attending":             "Reason for attending",
    "cause_understanding":              "Has understanding of cause",
    "cause_understanding_detail":       "Understanding of cause (detail)",
    "prognosis_expectations":           "Prognosis expectations",
    "treatment_preference":             "Treatment preference",
    # ── 02 Subjective ───────────────────────────────────────────────────────
    "body_chart_completed":             "Body chart completed",
    "course_improving":                 "Course: Improving",
    "course_worsening":                 "Course: Worsening",
    "course_stable":                    "Course: Stable",
    "course_fluctuating":               "Course: Fluctuating",
    "flareup_rare":                     "Flare-ups: Rare",
    "flareup_occasional":               "Flare-ups: Occasional",
    "flareup_frequent":                 "Flare-ups: Frequent",
    "sleep_difficulty":                 "Sleep difficulty",
    "night_waking":                     "Night waking",
    "daytime_naps":                     "Daytime naps",
    "mood_influences":                  "Mood influences pain",
    "self_harm_risk":                   "Self-harm risk assessed",
    "symptom_location":                 "Symptom location",
    "symptom_nature":                   "Nature of symptoms",
    "onset":                            "Onset",
    "duration":                         "Duration",
    "context_at_onset":                 "Context at onset",
    "previous_episodes":                "Previous episodes",
    "previous_treatment":               "Previous treatment",
    "flareup_triggers":                 "Flare-up triggers",
    "flareup_predictability":           "Flare-up predictability",
    "flareup_duration":                 "Flare-up duration",
    "flareup_prevention":               "Flare-up prevention",
    "management_strategies":            "Management strategies",
    "pre_activity_level":               "Pre-injury activity level",
    "current_activity_level":           "Current activity level",
    "exercise_type":                    "Exercise type",
    "exercise_dose":                    "Exercise dose",
    "exercise_response":                "Exercise response",
    "pre_injury_role":                  "Pre-injury work role",
    "pre_injury_duties":                "Pre-injury duties",
    "current_work_status":              "Current work status",
    "current_duties":                   "Current duties",
    "bed_description":                  "Bed description",
    "sleep_position":                   "Sleep position",
    "night_waking_frequency":           "Night waking frequency",
    "night_waking_reason":              "Night waking reason",
    "morning_stiffness":                "Morning stiffness",
    "nap_frequency":                    "Nap frequency",
    "energy_levels":                    "Energy levels",
    "aggravating_factors":              "Aggravating factors",
    "easing_factors":                   "Easing factors",
    "daily_pattern_comments":           "Daily pattern comments",
    "social_situation":                 "Social situation",
    "financial_status":                 "Financial status",
    "cultural_considerations":          "Cultural considerations",
    "psychological_distress":           "Psychological distress",
    "screening_tool":                   "Screening tool used",
    "harm_plan":                        "Harm plan",
    "harm_means":                       "Harm means",
    "harm_intent":                      "Harm intent",
    "harm_action":                      "Harm action",
    "pain_control_score":               "Pain control score",
    "confidence_score":                 "Confidence score (PSEQ-2)",
    "pre_injury_hours":                 "Pre-injury work hours/week",
    "current_hours":                    "Current work hours/week",
    "sleep_difficulty_severity":        "Sleep difficulty severity",
    "sleep_onset_time":                 "Sleep onset time (mins)",
    "total_sleep_hours":                "Total sleep hours",
    "bed_exits_count":                  "Bed exits per night",
    "night_waking_severity":            "Night waking severity",
    "nap_duration":                     "Nap duration (mins)",
    # ── 03 Medical ──────────────────────────────────────────────────────────
    "no_previous_injuries":             "No previous injuries",
    "previous_injuries":                "Previous injuries (detail)",
    "comorbid_cancer":                  "Comorbidity: Cancer",
    "comorbid_mental_health":           "Comorbidity: Mental health",
    "comorbid_osteoporosis":            "Comorbidity: Osteoporosis",
    "comorbid_inflammatory":            "Comorbidity: Inflammatory arthritis",
    "comorbid_fibromyalgia":            "Comorbidity: Fibromyalgia",
    "comorbid_cfs":                     "Comorbidity: CFS",
    "comorbid_ibs":                     "Comorbidity: IBS",
    "comorbid_whiplash":                "Comorbidity: Whiplash",
    "comorbid_skin_rash":               "Comorbidity: Skin rash",
    "comorbid_drug_alcohol":            "Comorbidity: Drug/alcohol",
    "comorbid_fatigue_memory":          "Comorbidity: Fatigue/memory issues",
    "comorbid_other":                   "Other comorbidities",
    "cvd_hypercholesterolaemia":        "CVD risk: Hypercholesterolaemia",
    "cvd_cardiac":                      "CVD risk: Cardiac disease",
    "cvd_vascular":                     "CVD risk: Vascular disease",
    "cvd_stroke_tia":                   "CVD risk: Stroke/TIA",
    "cvd_diabetes":                     "CVD risk: Diabetes",
    "cvd_corticosteroids":              "CVD risk: Long-term corticosteroids",
    "cvd_clotting":                     "CVD risk: Clotting disorder",
    "cvd_ocp":                          "CVD risk: OCP use",
    "cvd_smoker":                       "CVD risk: Smoker",
    "cvd_postpartum":                   "CVD risk: Postpartum",
    "cvd_familial_history":             "CVD risk: Familial history",
    "rf_weight_loss":                   "Red flag: Unexplained weight loss",
    "rf_cancer_history":                "Red flag: Cancer history",
    "rf_age_50_spinal":                 "Red flag: Age >50 with spinal",
    "rf_failed_conservative":           "Red flag: Failed conservative care",
    "rf_trauma":                        "Red flag: Recent trauma",
    "rf_corticosteroids_fracture":      "Red flag: Corticosteroid fracture risk",
    "rf_osteoporosis_fracture":         "Red flag: Osteoporosis fracture risk",
    "rf_fever":                         "Red flag: Fever",
    "rf_immunosuppressed":              "Red flag: Immunosuppressed",
    "rf_spinal_procedure":              "Red flag: Recent spinal procedure",
    "rf_saddle_anaesthesia":            "Red flag: Saddle anaesthesia",
    "rf_bladder_disturbance":           "Red flag: Bladder disturbance",
    "rf_bowel_disturbance":             "Red flag: Bowel disturbance",
    "rf_bilateral_paraesthesia":        "Red flag: Bilateral paraesthesia",
    "rf_gait_disturbance":              "Red flag: Gait disturbance",
    "umn_hyperreflexia":                "UMN sign: Hyperreflexia",
    "umn_babinski":                     "UMN sign: Babinski positive",
    "umn_clonus":                       "UMN sign: Clonus",
    "umn_romberg":                      "UMN sign: Romberg positive",
    "umn_coordination":                 "UMN sign: Coordination impaired",
    "umn_interpretation":               "UMN interpretation",
    "cauda_equina_action":              "Cauda equina action taken",
    "spinal_cord_action":               "Spinal cord compression action taken",
    "diff_as_insidious":                "Diff AS: Insidious onset",
    "diff_as_lumbar_sij":               "Diff AS: Lumbar/SIJ location",
    "diff_as_inflammatory":             "Diff AS: Inflammatory pattern",
    "diff_as_breathing":                "Diff AS: Thoracic/breathing",
    "diff_as_fever_weight_loss":        "Diff AS: Fever/weight loss",
    "diff_as_likelihood":               "Diff AS: Likelihood",
    "diff_as_action":                   "Diff AS: Action taken",
    "diff_aaa_pulsating":               "Diff AAA: Pulsating abdominal mass",
    "diff_aaa_age_50":                  "Diff AAA: Age >50",
    "diff_aaa_cvd_risk":                "Diff AAA: CVD risk factors",
    "diff_aaa_ruptured":                "Diff AAA: Ruptured symptoms",
    "diff_aaa_likelihood":              "Diff AAA: Likelihood",
    "diff_aaa_action":                  "Diff AAA: Action taken",
    "diff_vc_non_dermatomal":           "Diff VC: Non-dermatomal leg pain",
    "diff_vc_age_50":                   "Diff VC: Age >50",
    "diff_vc_cvd_risk":                 "Diff VC: CVD risk factors",
    "diff_vc_walking_pain":             "Diff VC: Walking-related pain",
    "diff_vc_pvd_signs":                "Diff VC: PVD signs",
    "diff_vc_impotence":                "Diff VC: Impotence",
    "diff_vc_night_pain":               "Diff VC: Night pain",
    "diff_vc_likelihood":               "Diff VC: Likelihood",
    "diff_vc_action":                   "Diff VC: Action taken",
    # ── 04 Pain Classification ───────────────────────────────────────────────
    "infl_constant":                    "Inflammatory: Constant pain",
    "infl_morning":                     "Inflammatory: Morning stiffness",
    "infl_sleep":                       "Inflammatory: Night/sleep pain",
    "infl_activity":                    "Inflammatory: Activity improves",
    "infl_likelihood":                  "Inflammatory likelihood",
    "noci_subj_mechanical":             "Nociceptive (Sx): Mechanical",
    "noci_subj_trauma":                 "Nociceptive (Sx): Trauma/incident",
    "noci_subj_localised":              "Nociceptive (Sx): Localised",
    "noci_subj_resolving":              "Nociceptive (Sx): Resolving",
    "noci_subj_analgesia":              "Nociceptive (Sx): Responds to analgesia",
    "noci_subj_no_constant":            "Nociceptive (Sx): Not constant",
    "noci_subj_inflammation":           "Nociceptive (Sx): Local inflammation",
    "noci_subj_recent":                 "Nociceptive (Sx): Recent onset",
    "noci_exam_mechanical":             "Nociceptive (Ex): Mechanical reproduction",
    "noci_exam_palpation":              "Nociceptive (Ex): Palpation reproduction",
    "noci_exam_hyperalgesia":           "Nociceptive (Ex): Local hyperalgesia",
    "noci_exam_antalgic":               "Nociceptive (Ex): Antalgic posture",
    "noci_likelihood":                  "Nociceptive likelihood",
    "noci_interpretation":              "Nociceptive interpretation",
    "neuro_subj_quality":               "Neuropathic (Sx): Burning/electric/shooting quality",
    "neuro_subj_nerve_injury":          "Neuropathic (Sx): Known nerve injury/pathology",
    "neuro_subj_neurological":          "Neuropathic (Sx): Neurological symptoms",
    "neuro_subj_dermatomal":            "Neuropathic (Sx): Dermatomal/nerve trunk",
    "neuro_subj_medication":            "Neuropathic (Sx): Responds to neuropathic meds",
    "neuro_subj_severity":              "Neuropathic (Sx): Severe/night pain",
    "neuro_subj_neural_loading":        "Neuropathic (Sx): Provoked by neural loading",
    "neuro_subj_dysaesthesia":          "Neuropathic (Sx): Dysaesthesia/allodynia",
    "neuro_subj_spontaneous":           "Neuropathic (Sx): Spontaneous pain",
    "neuro_exam_neurodynamic":          "Neuropathic (Ex): Positive neurodynamic test",
    "neuro_exam_neural_palpation":      "Neuropathic (Ex): Neural palpation sensitive",
    "neuro_exam_neurology":             "Neuropathic (Ex): Neurology change",
    "neuro_exam_antalgic":              "Neuropathic (Ex): Antalgic posture",
    "neuro_exam_hyperalgesia":          "Neuropathic (Ex): Hyperalgesia in distribution",
    "neuro_likelihood":                 "Neuropathic likelihood",
    "neuro_interpretation":             "Neuropathic interpretation",
    "nocip_subj_disproportionate":      "Nociplastic (Sx): Disproportionate to pathology",
    "nocip_subj_persistent":            "Nociplastic (Sx): Persistent beyond healing",
    "nocip_subj_disproportionate2":     "Nociplastic (Sx): Disproportionate to stimulus",
    "nocip_subj_widespread":            "Nociplastic (Sx): Widespread/multifocal",
    "nocip_subj_failed":                "Nociplastic (Sx): Failed previous treatment",
    "nocip_subj_psychosocial":          "Nociplastic (Sx): Psychosocial contributors",
    "nocip_subj_medication":            "Nociplastic (Sx): Responds to centrally-acting meds",
    "nocip_subj_spontaneous":           "Nociplastic (Sx): Spontaneous pain",
    "nocip_subj_disability":            "Nociplastic (Sx): High disability",
    "nocip_subj_constant":              "Nociplastic (Sx): Constant/unpredictable",
    "nocip_subj_night_pain":            "Nociplastic (Sx): Disturbed sleep/night pain",
    "nocip_subj_dysaesthesia":          "Nociplastic (Sx): Dysaesthesia",
    "nocip_subj_severity":              "Nociplastic (Sx): Severe/difficult to control",
    "nocip_exam_disproportionate":      "Nociplastic (Ex): Disproportionate exam findings",
    "nocip_exam_hyperalgesia":          "Nociplastic (Ex): Widespread hyperalgesia/allodynia",
    "nocip_exam_diffuse":               "Nociplastic (Ex): Diffuse palpation tenderness",
    "nocip_exam_psychosocial":          "Nociplastic (Ex): Psychosocial features on exam",
    "nocip_likelihood":                 "Nociplastic likelihood",
    "nocip_interpretation":             "Nociplastic interpretation",
    "cs_light":                         "CS feature: Light sensitivity",
    "cs_touch":                         "CS feature: Touch sensitivity",
    "cs_noise":                         "CS feature: Noise sensitivity",
    "cs_pesticides":                    "CS feature: Chemical/smell sensitivity",
    "cs_temperature":                   "CS feature: Temperature sensitivity",
    "cs_fatigue":                       "CS feature: Fatigue",
    "cs_sleep":                         "CS feature: Sleep disturbance",
    "cs_concentration":                 "CS feature: Concentration difficulty",
    "cs_swelling":                      "CS feature: Perceived swelling",
    "cs_tingling":                      "CS feature: Tingling",
    "csi_score":                        "CSI score",
    "summary_dominant":                 "Dominant pain type",
    "summary_contributing":             "Contributing pain types",
    "summary_reasoning":                "Pain classification reasoning",
    # ── 05 Outcome Measures ───────────────────────────────────────────────────
    "psfs_score":                       "PSFS score",
    "psfs_act_1":                       "PSFS activity 1",
    "psfs_act_2":                       "PSFS activity 2",
    "psfs_act_3":                       "PSFS activity 3",
    "psfs_act_4":                       "PSFS activity 4",
    "psfs_act_5":                       "PSFS activity 5",
    "psfs_interp":                      "PSFS interpretation",
    "bpi_activity":                     "BPI: Activity interference",
    "bpi_mood":                         "BPI: Mood interference",
    "bpi_walking":                      "BPI: Walking interference",
    "bpi_work":                         "BPI: Normal work interference",
    "bpi_relations":                    "BPI: Relations with others",
    "bpi_sleep":                        "BPI: Sleep interference",
    "bpi_enjoyment":                    "BPI: Enjoyment of life interference",
    "dass_dep_score":                   "DASS-21: Depression score",
    "dass_anx_score":                   "DASS-21: Anxiety score",
    "dass_str_score":                   "DASS-21: Stress score",
    "dass_dep_interp":                  "DASS-21: Depression interpretation",
    "dass_anx_interp":                  "DASS-21: Anxiety interpretation",
    "dass_str_interp":                  "DASS-21: Stress interpretation",
    "pcs_rum_score":                    "PCS: Rumination score",
    "pcs_mag_score":                    "PCS: Magnification score",
    "pcs_help_score":                   "PCS: Helplessness score",
    "pcs_total_score":                  "PCS: Total score",
    "pcs_rum_risk":                     "PCS: Rumination risk",
    "pcs_mag_risk":                     "PCS: Magnification risk",
    "pcs_help_risk":                    "PCS: Helplessness risk",
    "pcs_total_risk":                   "PCS: Total risk",
    "pseq_score":                       "PSEQ score",
    "pcl5_score":                       "PCL-5 score",
    "pcl5_interp":                      "PCL-5 interpretation",
    "pcl5_action":                      "PCL-5 action taken",
    "isi_score":                        "ISI score",
    "isi_interp":                       "ISI interpretation",
    "pbas_score":                       "PBAS score",
    "pbas_interp":                      "PBAS interpretation",
    "add_audit":                        "AUDIT administered",
    "add_dudit":                        "DUDIT administered",
    "add_epoc":                         "EPPOC notes",
    "add_other":                        "Additional measures notes",
    # ── 06 Diagnosis ──────────────────────────────────────────────────────────
    "mechanism":                        "Mechanism",
    "primary_subtype":                  "Primary subtype",
    "primary_severity":                 "Primary severity",
    "primary_distress":                 "Primary: High psychological distress",
    "primary_not_other_dx":             "Primary: Not better explained by other dx",
    "surgical_subtype":                 "Surgical subtype",
    "surgical_severity":                "Surgical severity",
    "surgical_procedure":               "Surgical procedure",
    "surgical_source":                  "Surgical source",
    "traumatic_subtype":                "Traumatic subtype",
    "traumatic_severity":               "Traumatic severity",
    "traumatic_event":                  "Traumatic event",
    "traumatic_source":                 "Traumatic source",
    "msk_subtype":                      "MSK subtype",
    "msk_severity":                     "MSK severity",
    "msk_pathology":                    "MSK pathology",
    "msk_source":                       "MSK source",
    "neuro_subtype":                    "Neurological subtype",
    "neuro_severity":                   "Neurological severity",
    "neuro_lesion":                     "Neurological lesion",
    "mixed_dominant":                   "Mixed: Dominant type",
    "mixed_reasoning":                  "Mixed reasoning",
    "duration_over_3_months":           "Duration > 3 months",
    "goal_1":                           "SMART Goal 1",
    "goal_2":                           "SMART Goal 2",
    "goal_3":                           "SMART Goal 3",
    "goal_4":                           "SMART Goal 4",
    # ── 07 Barriers & Treatment ───────────────────────────────────────────────
    "b_noci_disease":                   "Barrier: Disease/pathology",
    "b_noci_pacing":                    "Barrier: Pacing issues",
    "b_noci_inflammatory":              "Barrier: Inflammatory features",
    "b_noci_deconditioning":            "Barrier: Deconditioning",
    "b_noci_movement":                  "Barrier: Reduced movement",
    "b_noci_gait":                      "Barrier: Asymmetrical gait",
    "b_noci_strength":                  "Barrier: Strength deficits",
    "b_noci_deep_muscle":               "Barrier: Deep muscle activation",
    "b_noci_overactivity":              "Barrier: Muscle overactivity",
    "b_noci_nerve_mech":                "Barrier: Nerve mechanosensitivity",
    "b_noci_diet":                      "Barrier: Diet/weight",
    "bx_strength_glute_max":            "  Strength deficit: Glute max",
    "bx_strength_glute_med":            "  Strength deficit: Glute med",
    "bx_strength_iliopsoas":            "  Strength deficit: Iliopsoas",
    "bx_strength_quads":                "  Strength deficit: Quads",
    "bx_deep_multifidus":               "  Deep muscle: Multifidus",
    "bx_deep_ta":                       "  Deep muscle: Transversus abdominis",
    "bx_deep_erector":                  "  Deep muscle: Erector spinae",
    "bx_over_erector":                  "  Overactivity: Erector spinae",
    "bx_over_ql":                       "  Overactivity: Quadratus lumborum",
    "bx_over_ra":                       "  Overactivity: Rectus abdominis",
    "bx_over_obliques":                 "  Overactivity: Obliques",
    "bx_over_piriformis":               "  Overactivity: Piriformis",
    "bx_over_iliopsoas":                "  Overactivity: Iliopsoas",
    "bx_over_hamstrings":               "  Overactivity: Hamstrings",
    "bx_over_adductors":                "  Overactivity: Adductors",
    "bi_movement_region":               "  Movement region",
    "bi_strength_other":                "  Strength other",
    "bi_deep_other":                    "  Deep muscle other",
    "bi_over_other":                    "  Overactivity other",
    "bi_nerve_region":                  "  Nerve region",
    "bi_red_flag_detail":               "  Red flag detail",
    "bi_substance_detail":              "  Substance detail",
    "b_neuro_confirmed":                "Barrier: Neuropathic (confirmed)",
    "b_neuro_unconfirmed":              "Barrier: Neuropathic (unconfirmed)",
    "b_nocip_moderate":                 "Barrier: Nociplastic/CS",
    "b_nocip_crps":                     "Barrier: CRPS",
    "b_nocip_fnd":                      "Barrier: FND",
    "b_psych_depression":               "Barrier: Depression",
    "b_psych_anxiety":                  "Barrier: Anxiety",
    "b_psych_stress":                   "Barrier: Stress",
    "b_psych_catastrophising":          "Barrier: Catastrophising",
    "b_psych_self_efficacy":            "Barrier: Reduced self-efficacy",
    "b_psych_unhelpful_beliefs":        "Barrier: Unhelpful beliefs",
    "b_psych_ptsd":                     "Barrier: PTSD symptoms",
    "b_psych_readiness":                "Barrier: Unclear readiness to change",
    "bx_dep_psychiatry":                "  Depression: Psychiatry referral",
    "bx_anx_psychiatry":                "  Anxiety: Psychiatry referral",
    "bx_stress_psychiatry":             "  Stress: Psychiatry referral",
    "bx_ptsd_psychiatry":               "  PTSD: Psychiatry referral",
    "bx_dep_severity":                  "  Depression severity",
    "bx_anx_severity":                  "  Anxiety severity",
    "bx_stress_severity":               "  Stress severity",
    "bx_ptsd_mechanism":                "  PTSD mechanism",
    "bx_belief_expectations":           "  Belief: Unrealistic expectations",
    "bx_belief_symptom_focus":          "  Belief: Symptom focus",
    "bx_belief_cure_focus":             "  Belief: Cure focus",
    "bx_belief_further_tx":             "  Belief: Further treatment needed",
    "b_sleep_disturbed":                "Barrier: Disturbed sleep",
    "b_social_home":                    "Barrier: Home/social barriers",
    "b_social_rtw":                     "Barrier: Return to work barriers",
    "bx_soc_family_support":            "  Social: Family support",
    "bx_soc_social_support":            "  Social: Social support",
    "bx_soc_relationship":              "  Social: Relationship issues",
    "bx_soc_personal_rel":              "  Social: Personal relationships",
    "bx_soc_financial":                 "  Social: Financial",
    "bx_soc_residential":               "  Social: Residential",
    "bx_soc_distance":                  "  Social: Distance to care",
    "b_med_red_flag":                   "Barrier: Red flag",
    "b_med_substance":                  "Barrier: Substance use",
    "b_med_as":                         "Barrier: Possible AS",
    "b_med_aaa":                        "Barrier: Possible AAA",
    "b_med_vascular":                   "Barrier: Vascular claudication",
    "b_med_cervical_ha":                "Barrier: Cervical headache",
    "b_med_medico_legal":               "Barrier: Medico-legal",
    "custom_1_barrier":                 "Custom barrier 1",
    "custom_1_strategy":                "Custom strategy 1",
    "custom_2_barrier":                 "Custom barrier 2",
    "custom_2_strategy":                "Custom strategy 2",
    "tx_consent_explanation":           "Treatment: Consent/explanation given",
    "s1_consent_content":               "Session 1: Consent content discussed",
    "tx_email_obtained":                "Treatment: Email obtained",
    "tx_display_book":                  "Treatment: Display book shown",
    "hw_online_module":                 "Homework: Online module",
    "hw_mindfulness":                   "Homework: Mindfulness",
    "hw_goal_sheet":                    "Homework: Goal sheet",
    "hw_activity_diary":                "Homework: Activity diary",
    "hw_sleep_diary":                   "Homework: Sleep diary",
    "d1_explanation":                   "Day 1: Explanation provided",
    "d1_session2":                      "Day 1: Session 2 booked",
    "d1_hypothesis":                    "Day 1: Hypothesis shared",
    "d1_diagnosis":                     "Day 1: Diagnosis discussed",
    "d1_values":                        "Day 1: Values explored",
    "d1_evidence":                      "Day 1: Evidence discussed",
    "d1_plan":                          "Day 1: Plan shared",
    "d1_prognosis":                     "Day 1: Prognosis discussed",
    "d1_stakeholders":                  "Day 1: Stakeholders identified",
    "d1_confidence_tested":             "Day 1: Confidence tested",
    "d1_questionnaires":                "Day 1: Questionnaires completed",
    "ps_questionnaires":                "Post-session: Questionnaires saved",
    "ps_eppoc":                         "Post-session: EPPOC submitted",
    "ps_ptsd_scored":                   "Post-session: PTSD scored",
    "ps_isi_pbas":                      "Post-session: ISI/PBAS scored",
    "ps_csi":                           "Post-session: CSI scored",
    "ps_audit_dudit":                   "Post-session: AUDIT/DUDIT scored",
    "s1_confidence_nrs":                "Session 1: Confidence NRS",
    "fu_om_schedule":                   "Follow-up: OM schedule",
    "tx_goal_orientation":              "Treatment: Goal orientation",
    "tx_formulation":                   "Treatment: Formulation",
    "tx_program":                       "Treatment: Program",
    "tx_home_program":                  "Treatment: Home program",
    "tx_psychosocial":                  "Treatment: Psychosocial strategies",
    "tx_medical":                       "Treatment: Medical/referral plan",
    "tx_rtw":                           "Treatment: RTW plan",
    "tx_pain_type":                     "Treatment: Pain type (for debunking)",
    "tx_debunk_radiology":              "Treatment: Debunk radiology",
    "s1_education":                     "Session 1: Education provided",
    "s1_experiential":                  "Session 1: Experiential learning",
    "s1_hw_other":                      "Session 1: Homework other",
    "fu_next_focus":                    "Follow-up: Next session focus",
    "fu_monitoring":                    "Follow-up: Monitoring plan",
}


def _label(fid: str) -> str:
    return LABELS.get(fid, fid)


def _val_raw(val) -> str:
    if val is True:
        return "✓ Yes"
    if val is False:
        return "✗ No"
    if val is None:
        return "(not answered)"
    if isinstance(val, str):
        s = val.strip()
        return s if s else "(empty)"
    if isinstance(val, list):
        return f"[{len(val)} items]"
    return str(val)


def export_raw_report(session_data: dict) -> str:  # noqa: C901
    """
    Generate a complete plain-text raw export of ALL session fields.

    Every field from every section (01→07 + scratchpad + body chart) is
    enumerated explicitly in UI order. Unanswered fields show "(not answered)"
    so nothing is silently omitted.
    """
    import time as _time

    SEP  = "═" * 60
    SEP2 = "─" * 60

    lines: list[str] = []
    a = session_data.get("assessment", {})

    # ── helpers ─────────────────────────────────────────────────────────────

    def sec(title: str) -> None:
        lines.append("")
        lines.append(SEP)
        lines.append(title)
        lines.append(SEP)

    def sub(title: str) -> None:
        lines.append(f"  — {title} —")

    def f(fid: str, d: dict) -> None:
        """Emit one field. Multi-line text gets indented continuation lines."""
        val = d.get(fid)
        label = _label(fid)
        if isinstance(val, str) and "\n" in val.strip():
            lines.append(f"  {label}:")
            for row in val.strip().split("\n"):
                lines.append(f"    {row}" if row.strip() else "")
        else:
            lines.append(f"  {label}: {_val_raw(val)}")

    def txt(fid: str, d: dict) -> None:
        """Text field — always multi-line block even if single line."""
        val = (d.get(fid) or "").strip()
        label = _label(fid)
        lines.append(f"  {label}:")
        if val:
            for row in val.split("\n"):
                lines.append(f"    {row}")
        else:
            lines.append("    (empty)")

    # ── header ──────────────────────────────────────────────────────────────

    c_hdr = a.get("consent", {}) or {}
    preferred_name = c_hdr.get("preferred_name", "").strip() or "(not set)"
    session_name   = session_data.get("session_name", "")
    created        = session_data.get("created", 0)
    date_str       = _time.strftime("%d %b %Y %H:%M", _time.localtime(created)) if created else "(unknown)"
    regions        = ", ".join(session_data.get("regions", [])) or "(not set)"

    lines.append(SEP)
    lines.append("PHYSIOTHERAPY ASSESSMENT — FULL RAW DATA")
    lines.append(f"Patient:    {preferred_name}")
    lines.append(f"Date:       {date_str}")
    lines.append(f"Region:     {regions}")
    lines.append(f"Session ID: {session_name}")
    lines.append(SEP)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1: CONSENT & SETUP
    # ════════════════════════════════════════════════════════════════════════
    c = a.get("consent", {}) or {}
    sec("SECTION 1: CONSENT & SETUP")

    sub("Consent")
    f("consent_to_proceed",        c)
    f("consent_sensitive_topics",  c)
    f("preferred_name",            c)

    sub("Session Framing")
    f("pain_multifactorial_explained",    c)
    f("education_as_treatment_explained", c)
    txt("patient_expectations",           c)

    sub("Patient Perspective (ICE+)")
    txt("reason_for_attending",     c)
    f("cause_understanding",        c)
    txt("cause_understanding_detail", c)
    txt("prognosis_expectations",   c)
    txt("treatment_preference",     c)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2: SUBJECTIVE EXAMINATION
    # ════════════════════════════════════════════════════════════════════════
    s = a.get("subjective", {}) or {}
    sec("SECTION 2: SUBJECTIVE EXAMINATION")

    sub("Symptoms")
    f("body_chart_completed", s)
    txt("symptom_location",    s)
    txt("symptom_nature",      s)

    sub("History")
    txt("onset",              s)
    txt("duration",           s)
    f("course_improving",     s)
    f("course_worsening",     s)
    f("course_stable",        s)
    f("course_fluctuating",   s)
    txt("context_at_onset",   s)
    txt("previous_episodes",  s)
    txt("previous_treatment", s)

    sub("Flare-ups")
    f("flareup_rare",           s)
    f("flareup_occasional",     s)
    f("flareup_frequent",       s)
    txt("flareup_triggers",     s)
    txt("flareup_predictability", s)
    txt("flareup_duration",     s)

    sub("Self-Management & Control")
    f("pain_control_score",      s)
    txt("flareup_prevention",    s)
    txt("management_strategies", s)
    f("confidence_score",        s)

    sub("Activity & Exercise")
    txt("pre_activity_level",     s)
    txt("current_activity_level", s)
    txt("exercise_type",          s)
    txt("exercise_dose",          s)
    txt("exercise_response",      s)

    sub("Work")
    txt("pre_injury_role",    s)
    f("pre_injury_hours",     s)
    txt("pre_injury_duties",  s)
    txt("current_work_status", s)
    f("current_hours",        s)
    txt("current_duties",     s)

    sub("Sleep")
    txt("bed_description",         s)
    f("sleep_difficulty",          s)
    f("sleep_difficulty_severity", s)
    f("sleep_onset_time",          s)
    txt("sleep_position",          s)
    f("total_sleep_hours",         s)
    f("night_waking",              s)
    txt("night_waking_frequency",  s)
    txt("night_waking_reason",     s)
    f("bed_exits_count",           s)
    f("night_waking_severity",     s)
    txt("morning_stiffness",       s)
    f("daytime_naps",              s)
    txt("nap_frequency",           s)
    f("nap_duration",              s)
    txt("energy_levels",           s)

    sub("Behaviour of Symptoms")
    txt("aggravating_factors",    s)
    txt("easing_factors",         s)
    f("mood_influences",          s)
    txt("daily_pattern_comments", s)

    sub("Psychosocial")
    txt("social_situation",       s)
    txt("financial_status",       s)
    txt("cultural_considerations", s)
    txt("psychological_distress", s)
    txt("screening_tool",         s)

    sub("Suicide / Self-Harm Risk")
    f("self_harm_risk",   s)
    txt("harm_plan",      s)
    txt("harm_means",     s)
    txt("harm_intent",    s)
    txt("harm_action",    s)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3: MEDICAL SCREENING
    # ════════════════════════════════════════════════════════════════════════
    m = a.get("medical", {}) or {}
    sec("SECTION 3: MEDICAL SCREENING")

    sub("Comorbidities / PMH")
    f("no_previous_injuries",     m)
    txt("previous_injuries",      m)
    f("comorbid_cancer",          m)
    f("comorbid_mental_health",   m)
    f("comorbid_osteoporosis",    m)
    f("comorbid_inflammatory",    m)
    f("comorbid_fibromyalgia",    m)
    f("comorbid_cfs",             m)
    f("comorbid_ibs",             m)
    f("comorbid_whiplash",        m)
    f("comorbid_skin_rash",       m)
    f("comorbid_drug_alcohol",    m)
    f("comorbid_fatigue_memory",  m)
    txt("comorbid_other",         m)

    sub("Cardiovascular Risk Factors")
    f("cvd_hypercholesterolaemia", m)
    f("cvd_cardiac",              m)
    f("cvd_vascular",             m)
    f("cvd_stroke_tia",           m)
    f("cvd_diabetes",             m)
    f("cvd_corticosteroids",      m)
    f("cvd_clotting",             m)
    f("cvd_ocp",                  m)
    f("cvd_smoker",               m)
    f("cvd_postpartum",           m)
    f("cvd_familial_history",     m)

    sub("Red Flags — Malignancy")
    f("rf_weight_loss",          m)
    f("rf_cancer_history",       m)
    f("rf_age_50_spinal",        m)
    f("rf_failed_conservative",  m)

    sub("Red Flags — Fracture")
    f("rf_trauma",                  m)
    f("rf_corticosteroids_fracture", m)
    f("rf_osteoporosis_fracture",   m)

    sub("Red Flags — Infection")
    f("rf_fever",           m)
    f("rf_immunosuppressed", m)
    f("rf_spinal_procedure", m)

    sub("Red Flags — Cauda Equina (URGENT)")
    f("rf_saddle_anaesthesia", m)
    f("rf_bladder_disturbance", m)
    f("rf_bowel_disturbance",  m)
    txt("cauda_equina_action", m)

    sub("Red Flags — Spinal Cord (URGENT)")
    f("rf_bilateral_paraesthesia", m)
    f("rf_gait_disturbance",      m)
    txt("spinal_cord_action",     m)

    sub("Upper Motor Neurone Signs")
    f("umn_hyperreflexia",   m)
    f("umn_babinski",        m)
    f("umn_clonus",          m)
    f("umn_romberg",         m)
    f("umn_coordination",    m)
    txt("umn_interpretation", m)

    sub("Differential — Ankylosing Spondylitis")
    f("diff_as_insidious",         m)
    f("diff_as_lumbar_sij",        m)
    f("diff_as_inflammatory",      m)
    f("diff_as_breathing",         m)
    f("diff_as_fever_weight_loss", m)
    f("diff_as_likelihood",        m)
    txt("diff_as_action",          m)

    sub("Differential — Abdominal Aortic Aneurysm")
    f("diff_aaa_pulsating",  m)
    f("diff_aaa_age_50",     m)
    f("diff_aaa_cvd_risk",   m)
    f("diff_aaa_ruptured",   m)
    f("diff_aaa_likelihood", m)
    txt("diff_aaa_action",   m)

    sub("Differential — Vascular Claudication")
    f("diff_vc_non_dermatomal", m)
    f("diff_vc_age_50",         m)
    f("diff_vc_cvd_risk",       m)
    f("diff_vc_walking_pain",   m)
    f("diff_vc_pvd_signs",      m)
    f("diff_vc_impotence",      m)
    f("diff_vc_night_pain",     m)
    f("diff_vc_likelihood",     m)
    txt("diff_vc_action",       m)

    sub("Medications")
    meds = m.get("medications", [])
    if meds:
        for i, med in enumerate(meds, 1):
            name     = med.get("name", "").strip()
            dose     = med.get("dose", "").strip()
            timing   = med.get("timing", "").strip()
            comments = med.get("comments", "").strip()
            parts    = [x for x in [name, dose, timing] if x]
            med_str  = "  ".join(parts) if parts else "(unnamed)"
            if comments:
                med_str += f"  [{comments}]"
            lines.append(f"  {i}. {med_str}")
    else:
        lines.append("  (none recorded)")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4: PAIN CLASSIFICATION
    # ════════════════════════════════════════════════════════════════════════
    pc = a.get("pain_classification", {}) or {}
    sec("SECTION 4: PAIN CLASSIFICATION")

    sub("Inflammatory Pain Features")
    f("infl_constant",    pc)
    f("infl_morning",     pc)
    f("infl_sleep",       pc)
    f("infl_activity",    pc)
    f("infl_likelihood",  pc)

    sub("Nociceptive Pain — Subjective Features")
    f("noci_subj_mechanical",   pc)
    f("noci_subj_trauma",       pc)
    f("noci_subj_localised",    pc)
    f("noci_subj_resolving",    pc)
    f("noci_subj_analgesia",    pc)
    f("noci_subj_no_constant",  pc)
    f("noci_subj_inflammation", pc)
    f("noci_subj_recent",       pc)

    sub("Nociceptive Pain — Examination Features")
    f("noci_exam_mechanical",  pc)
    f("noci_exam_palpation",   pc)
    f("noci_exam_hyperalgesia", pc)
    f("noci_exam_antalgic",    pc)
    f("noci_likelihood",       pc)
    txt("noci_interpretation", pc)

    sub("Neuropathic Pain — Subjective Features")
    f("neuro_subj_quality",        pc)
    f("neuro_subj_nerve_injury",   pc)
    f("neuro_subj_neurological",   pc)
    f("neuro_subj_dermatomal",     pc)
    f("neuro_subj_medication",     pc)
    f("neuro_subj_severity",       pc)
    f("neuro_subj_neural_loading", pc)
    f("neuro_subj_dysaesthesia",   pc)
    f("neuro_subj_spontaneous",    pc)

    sub("Neuropathic Pain — Examination Features")
    f("neuro_exam_neurodynamic",    pc)
    f("neuro_exam_neural_palpation", pc)
    f("neuro_exam_neurology",       pc)
    f("neuro_exam_antalgic",        pc)
    f("neuro_exam_hyperalgesia",    pc)
    f("neuro_likelihood",           pc)
    txt("neuro_interpretation",     pc)

    sub("Nociplastic Pain — Subjective Features")
    f("nocip_subj_disproportionate",  pc)
    f("nocip_subj_persistent",        pc)
    f("nocip_subj_disproportionate2", pc)
    f("nocip_subj_widespread",        pc)
    f("nocip_subj_failed",            pc)
    f("nocip_subj_psychosocial",      pc)
    f("nocip_subj_medication",        pc)
    f("nocip_subj_spontaneous",       pc)
    f("nocip_subj_disability",        pc)
    f("nocip_subj_constant",          pc)
    f("nocip_subj_night_pain",        pc)
    f("nocip_subj_dysaesthesia",      pc)
    f("nocip_subj_severity",          pc)

    sub("Nociplastic Pain — Examination Features")
    f("nocip_exam_disproportionate", pc)
    f("nocip_exam_hyperalgesia",     pc)
    f("nocip_exam_diffuse",          pc)
    f("nocip_exam_psychosocial",     pc)
    f("nocip_likelihood",            pc)
    txt("nocip_interpretation",      pc)

    sub("Central Sensitisation")
    f("csi_score",        pc)
    f("cs_light",         pc)
    f("cs_touch",         pc)
    f("cs_noise",         pc)
    f("cs_pesticides",    pc)
    f("cs_temperature",   pc)
    f("cs_fatigue",       pc)
    f("cs_sleep",         pc)
    f("cs_concentration", pc)
    f("cs_swelling",      pc)
    f("cs_tingling",      pc)

    sub("Pain Type Summary")
    f("summary_dominant",       pc)
    txt("summary_contributing", pc)
    txt("summary_reasoning",    pc)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5: OUTCOME MEASURES
    # ════════════════════════════════════════════════════════════════════════
    om = a.get("outcome_measures", {}) or {}
    sec("SECTION 5: OUTCOME MEASURES")

    sub("Patient Specific Functional Scale (PSFS)")
    f("psfs_score",  om)
    f("psfs_interp", om)
    f("psfs_act_1",  om)
    f("psfs_act_2",  om)
    f("psfs_act_3",  om)
    f("psfs_act_4",  om)
    f("psfs_act_5",  om)

    sub("Brief Pain Inventory (BPI) — interference /10")
    f("bpi_activity",  om)
    f("bpi_mood",      om)
    f("bpi_walking",   om)
    f("bpi_work",      om)
    f("bpi_relations", om)
    f("bpi_sleep",     om)
    f("bpi_enjoyment", om)

    sub("DASS-21")
    f("dass_dep_score",  om)
    f("dass_dep_interp", om)
    f("dass_anx_score",  om)
    f("dass_anx_interp", om)
    f("dass_str_score",  om)
    f("dass_str_interp", om)

    sub("Pain Catastrophising Scale (PCS)")
    f("pcs_rum_score",   om)
    f("pcs_rum_risk",    om)
    f("pcs_mag_score",   om)
    f("pcs_mag_risk",    om)
    f("pcs_help_score",  om)
    f("pcs_help_risk",   om)
    f("pcs_total_score", om)
    f("pcs_total_risk",  om)

    sub("Pain Self-Efficacy Questionnaire (PSEQ)")
    f("pseq_score", om)

    sub("PCL-5 (PTSD)")
    f("pcl5_score",      om)
    f("pcl5_interp",     om)
    txt("pcl5_action",   om)

    sub("Sleep Measures")
    f("isi_score",   om)
    f("isi_interp",  om)
    f("pbas_score",  om)
    f("pbas_interp", om)

    sub("Additional Measures")
    f("add_audit",    om)
    f("add_dudit",    om)
    txt("add_epoc",   om)
    txt("add_other",  om)

    sub("Hypothesis Testing")
    for i in range(3):
        measure   = (om.get(f"hyp_{i}_measure",   "") or "").strip()
        baseline  = (om.get(f"hyp_{i}_baseline",  "") or "").strip()
        interval  = (om.get(f"hyp_{i}_interval",  "") or "").strip()
        rationale = (om.get(f"hyp_{i}_rationale", "") or "").strip()
        lines.append(
            f"  Row {i+1}: {measure or '—'}"
            f"  |  baseline: {baseline or '—'}"
            f"  |  interval: {interval or '—'}"
            f"  |  rationale: {rationale or '—'}"
        )

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6: DIAGNOSIS
    # ════════════════════════════════════════════════════════════════════════
    dx = a.get("diagnosis", {}) or {}
    sec("SECTION 6: DIAGNOSIS")

    sub("ICD-11 Pathway Selection")
    f("duration_over_3_months", dx)
    f("mechanism",              dx)

    sub("Chronic Primary Pain")
    f("primary_distress",     dx)
    f("primary_not_other_dx", dx)
    f("primary_subtype",      dx)
    f("primary_severity",     dx)

    sub("Chronic Post-Surgical Pain")
    f("surgical_procedure", dx)
    f("surgical_subtype",   dx)
    f("surgical_source",    dx)
    f("surgical_severity",  dx)

    sub("Chronic Post-Traumatic Pain")
    f("traumatic_event",    dx)
    f("traumatic_subtype",  dx)
    f("traumatic_source",   dx)
    f("traumatic_severity", dx)

    sub("Chronic Secondary MSK Pain")
    f("msk_pathology", dx)
    f("msk_subtype",   dx)
    f("msk_source",    dx)
    f("msk_severity",  dx)

    sub("Chronic Neuropathic Pain")
    f("neuro_lesion",   dx)
    f("neuro_subtype",  dx)
    f("neuro_severity", dx)

    sub("Mixed / Indeterminate")
    f("mixed_dominant",     dx)
    txt("mixed_reasoning",  dx)

    sub("SMART Goals")
    f("goal_1", dx)
    f("goal_2", dx)
    f("goal_3", dx)
    f("goal_4", dx)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7: BARRIERS & TREATMENT PLAN
    # ════════════════════════════════════════════════════════════════════════
    br = a.get("barriers", {}) or {}
    sec("SECTION 7: BARRIERS & TREATMENT PLAN")

    sub("Physical / Nociceptive Barriers")
    f("b_noci_disease",        br)
    f("b_noci_pacing",         br)
    f("b_noci_inflammatory",   br)
    f("b_noci_deconditioning", br)
    f("b_noci_movement",       br)
    f("bi_movement_region",    br)
    f("b_noci_gait",           br)
    f("b_noci_strength",       br)
    f("bx_strength_glute_max", br)
    f("bx_strength_glute_med", br)
    f("bx_strength_iliopsoas", br)
    f("bx_strength_quads",     br)
    f("bi_strength_other",     br)
    f("b_noci_deep_muscle",    br)
    f("bx_deep_multifidus",    br)
    f("bx_deep_ta",            br)
    f("bx_deep_erector",       br)
    f("bi_deep_other",         br)
    f("b_noci_overactivity",   br)
    f("bx_over_erector",       br)
    f("bx_over_ql",            br)
    f("bx_over_ra",            br)
    f("bx_over_obliques",      br)
    f("bx_over_piriformis",    br)
    f("bx_over_iliopsoas",     br)
    f("bx_over_hamstrings",    br)
    f("bx_over_adductors",     br)
    f("bi_over_other",         br)
    f("b_noci_nerve_mech",     br)
    f("bi_nerve_region",       br)
    f("b_noci_diet",           br)

    sub("Neuropathic Barriers")
    f("b_neuro_confirmed",   br)
    f("b_neuro_unconfirmed", br)

    sub("Nociplastic / Central Sensitisation Barriers")
    f("b_nocip_moderate", br)
    f("b_nocip_crps",     br)
    f("b_nocip_fnd",      br)

    sub("Psychological Barriers")
    f("b_psych_depression",       br)
    f("bx_dep_severity",          br)
    f("bx_dep_psychiatry",        br)
    f("b_psych_anxiety",          br)
    f("bx_anx_severity",          br)
    f("bx_anx_psychiatry",        br)
    f("b_psych_stress",           br)
    f("bx_stress_severity",       br)
    f("bx_stress_psychiatry",     br)
    f("b_psych_catastrophising",  br)
    f("b_psych_self_efficacy",    br)
    f("b_psych_unhelpful_beliefs", br)
    f("bx_belief_expectations",   br)
    f("bx_belief_symptom_focus",  br)
    f("bx_belief_cure_focus",     br)
    f("bx_belief_further_tx",     br)
    f("b_psych_ptsd",             br)
    f("bx_ptsd_mechanism",        br)
    f("bx_ptsd_psychiatry",       br)
    f("b_psych_readiness",        br)

    sub("Sleep & Social / Contextual Barriers")
    f("b_sleep_disturbed",       br)
    f("b_social_home",           br)
    f("bx_soc_family_support",   br)
    f("bx_soc_social_support",   br)
    f("bx_soc_relationship",     br)
    f("bx_soc_personal_rel",     br)
    f("bx_soc_financial",        br)
    f("bx_soc_residential",      br)
    f("bx_soc_distance",         br)
    f("b_social_rtw",            br)

    sub("Medical / Systemic Barriers")
    f("b_med_red_flag",     br)
    f("bi_red_flag_detail", br)
    f("b_med_substance",    br)
    f("bi_substance_detail", br)
    f("b_med_as",           br)
    f("b_med_aaa",          br)
    f("b_med_vascular",     br)
    f("b_med_cervical_ha",  br)
    f("b_med_medico_legal", br)

    sub("Custom Barriers")
    f("custom_1_barrier",  br)
    f("custom_1_strategy", br)
    f("custom_2_barrier",  br)
    f("custom_2_strategy", br)

    sub("Treatment Plan Summary")
    f("tx_pain_type",           br)
    f("tx_debunk_radiology",    br)
    f("tx_consent_explanation", br)
    txt("tx_goal_orientation",  br)
    txt("tx_formulation",       br)
    txt("tx_program",           br)
    txt("tx_home_program",      br)
    txt("tx_psychosocial",      br)
    txt("tx_medical",           br)
    txt("tx_rtw",               br)

    sub("Session 1 Treatment")
    txt("s1_education",     br)
    txt("s1_experiential",  br)
    f("s1_consent_content", br)
    f("s1_confidence_nrs",  br)
    f("hw_online_module",   br)
    f("hw_mindfulness",     br)
    f("hw_goal_sheet",      br)
    f("hw_activity_diary",  br)
    f("hw_sleep_diary",     br)
    txt("s1_hw_other",      br)
    f("tx_email_obtained",  br)
    f("tx_display_book",    br)

    sub("Day 1 Checklist")
    f("d1_explanation",       br)
    f("d1_session2",          br)
    f("d1_hypothesis",        br)
    f("d1_diagnosis",         br)
    f("d1_values",            br)
    f("d1_evidence",          br)
    f("d1_plan",              br)
    f("d1_prognosis",         br)
    f("d1_stakeholders",      br)
    f("d1_confidence_tested", br)
    f("d1_questionnaires",    br)

    sub("Follow-Up Plan")
    txt("fu_next_focus",    br)
    txt("fu_monitoring",    br)
    f("fu_om_schedule",     br)
    f("ps_questionnaires",  br)
    f("ps_eppoc",           br)
    f("ps_ptsd_scored",     br)
    f("ps_isi_pbas",        br)
    f("ps_csi",             br)
    f("ps_audit_dudit",     br)

    # ════════════════════════════════════════════════════════════════════════
    # SCRATCHPAD
    # ════════════════════════════════════════════════════════════════════════
    sp = a.get("scratchpad", {}) or {}
    sec("SCRATCHPAD NOTES")
    notes = (sp.get("notes") or "").strip()
    if notes:
        for row in notes.split("\n"):
            lines.append(f"  {row}")
    else:
        lines.append("  (empty)")

    # ════════════════════════════════════════════════════════════════════════
    # BODY CHART SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    subj_chart = session_data.get("subjective", {}) or {}
    obj_chart  = session_data.get("objective",  {}) or {}
    sec("BODY CHART SUMMARY")
    n_strokes = len(subj_chart.get("strokes", []))
    n_notes   = len(subj_chart.get("notes",   []))
    n_arrows  = len(subj_chart.get("arrows",  []))
    n_zones   = len(obj_chart.get("zones",    []))
    n_points  = len(obj_chart.get("points",   []))
    lines.append(f"  Symptom strokes drawn:    {n_strokes}")
    lines.append(f"  Note annotations:         {n_notes}")
    lines.append(f"  Arrows:                   {n_arrows}")
    lines.append(f"  Objective zones:          {n_zones}")
    lines.append(f"  Measurement points (PPT): {n_points}")

    # symptom types from the chart watcher summary (if present)
    body_chart = session_data.get("body_chart") or session_data.get("assessment", {}).get("body_chart")
    if isinstance(body_chart, dict):
        sym_types = body_chart.get("symptom_types_used", [])
        if sym_types:
            lines.append(f"  Symptom types used: {', '.join(str(t) for t in sym_types)}")
        views = body_chart.get("views_drawn", [])
        if views:
            lines.append(f"  Views drawn: {', '.join(str(v) for v in views)}")

    # ── footer ──────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(SEP)
    lines.append("END OF RAW ASSESSMENT DATA")
    lines.append(f"Generated: {_time.strftime('%d %b %Y %H:%M:%S')}")
    lines.append("For clinical use only — verify all entries before use")
    lines.append(SEP)

    return "\n".join(lines)


def save_raw_report(session_file: str) -> str:
    """
    Generate and save a raw plain-text report into the session directory.

    Output: <session_dir>/<session_name>_raw.txt  (same folder as all other
    session files — overwrites on each call so the file stays current).
    Returns the output path, or empty string on failure.
    """
    try:
        data = json.loads(Path(session_file).read_text())
    except Exception as e:
        logger.error(f"save_raw_report: failed to read session: {e}")
        return ""

    content = export_raw_report(data)
    session_name = data.get("session_name", "session")
    out_path = Path(session_file).parent / f"{session_name}_raw.txt"

    try:
        out_path.write_text(content, encoding="utf-8")
        logger.debug(f"Raw report written to {out_path}")
        return str(out_path)
    except Exception as e:
        logger.error(f"save_raw_report: write failed: {e}")
        return ""


def create_new_session(patient_id: str, regions: list[str]) -> dict:
    """
    Create a new assessment session (JSON scaffold).

    Returns session dict with initialized fields ready to save.
    """
    from datetime import datetime
    now = int(time.time())
    iso_date = datetime.fromtimestamp(now).isoformat() + "Z"

    return {
        "version": 2,
        "patient_id": patient_id,
        "session_label": f"Assessment - {regions[0] if regions else 'General'}" if regions else "Assessment",
        "session_name": f"{patient_id}_{datetime.now().strftime('%d_%m_%Y_%H%M')}",
        "created": now,
        "modified": now,
        "regions": regions,
        "launched_by": "tui",
        "workflow_stage": "01_consent",
        "body_chart_requested": False,
        "body_chart_complete": False,
        "ui": {
            "layout_mode": 0,
            "right_slot_views": [0, 1],
        },
        "subjective": {
            "strokes": [],
            "notes": [],
            "arrows": [],
            "link_matrix": [],
            "link_relations": [],
            "link_summary_active": False,
            "link_summary_view": 0,
            "link_summary_bx": 12.0,
            "link_summary_by": 378.0,
        },
        "objective": {
            "zones": [],
            "points": [],
        },
        "neuro": {},
        "assessment": {
            "consent": {
                "consent_to_proceed": None,
                "consent_sensitive_topics": None,
                "preferred_name": "",
                "pain_multifactorial_explained": None,
                "education_as_treatment_explained": None,
                "patient_expectations": "",
                "reason_for_attending": "",
                "cause_understanding": None,
                "cause_understanding_detail": "",
                "prognosis_expectations": "",
                "treatment_preference": "",
            },
            "history": "",
            "agg_factors": "",
            "ease_factors": "",
            "behaviour_24hr": "",
            "diagnosis": "",
            "plan": "",
            "clinical_notes": "",
            "modified": now,
        },
        "report": {
            "assessment": "",
            "plan": "",
            "clinical_notes": "",
            "note_subj": [],
        },
    }
