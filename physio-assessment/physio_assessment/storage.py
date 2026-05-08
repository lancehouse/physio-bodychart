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

    # Define core sections and their mandatory fields
    sections = {
        "01_consent": {
            "mandatory": ["patient_name"],  # Will be at top-level for now
            "assessment_fields": [],
        },
        "02_subjective": {
            "mandatory": [],
            "assessment_fields": ["history"],
        },
        "03_medical": {
            "mandatory": [],
            "assessment_fields": ["agg_factors", "ease_factors", "behaviour_24hr"],
        },
        "04_pain_classification": {
            "mandatory": [],
            "assessment_fields": [],
        },
        "05_outcome_measures": {
            "mandatory": [],
            "assessment_fields": [],
        },
        "06_diagnosis": {
            "mandatory": [],
            "assessment_fields": ["diagnosis"],
        },
        "07_barriers": {
            "mandatory": [],
            "assessment_fields": ["plan", "clinical_notes"],
        },
    }

    complete_status = {}
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
