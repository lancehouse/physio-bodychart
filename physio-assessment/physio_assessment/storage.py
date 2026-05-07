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
