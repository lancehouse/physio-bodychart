"""
Session storage — read/write assessment data to session JSON files.

Handles atomic writes via temp file + rename to prevent JSON corruption.
Preserves GTK-owned sections (subjective, objective) while updating
Python-owned assessment block.
"""

import json
import re
import subprocess
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


def assessment_path(session_file: str) -> Path:
    """Return the TUI-owned _assessment.json path for a given GTK _session.json path."""
    p = Path(session_file)
    return p.parent / p.name.replace("_session.json", "_assessment.json")


def objective_path(session_file: str) -> Path:
    """Return the Objective TUI-owned _objective.json path for a given _session.json path."""
    p = Path(session_file)
    return p.parent / p.name.replace("_session.json", "_objective.json")


def load_objective(session_file: str) -> dict:
    """Load objective data from _objective.json. Returns empty dict if absent."""
    path = objective_path(session_file)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse objective file {path}: {e}")
        return {}


def save_objective(
    session_file: str,
    assessment: dict,
    sections_complete: dict[str, bool],
) -> bool:
    """Save all objective sections to _objective.json atomically."""
    path = objective_path(session_file)
    try:
        data = json.loads(path.read_text()) if path.exists() else {}

        if "assessment" not in data:
            data["assessment"] = {}
        for key, val in assessment.items():
            data["assessment"][key] = val
        data["assessment"]["modified"] = int(time.time())

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        for section_id, complete in sections_complete.items():
            data["sections_complete"][section_id] = complete

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved objective to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save objective to {path}: {e}")
        return False


def write_objective_pid(pid: int) -> None:
    """Write the Objective TUI process PID into session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
        data["objective_pid"] = pid
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"write_objective_pid: {e}")


def read_objective_pid() -> int | None:
    """Read the Objective TUI PID from session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text())
        pid = data.get("objective_pid")
        return int(pid) if pid else None
    except Exception:
        return None


def get_objective_sections_complete(session_file: str) -> dict[str, bool]:
    """Read sections_complete from _objective.json."""
    path = objective_path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("sections_complete", {})
    except Exception:
        return {}


def count_objective_complete_sections(session_file: str) -> int:
    """Count how many objective sections are marked complete in _objective.json."""
    sections = get_objective_sections_complete(session_file)
    return sum(1 for v in sections.values() if v)


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

            # Merge TUI assessment data from separate _assessment.json if present
            assess_p = assessment_path(str(session_file))
            if assess_p.exists():
                try:
                    assess_data = json.loads(assess_p.read_text())
                    data["assessment"] = assess_data.get("assessment", data.get("assessment", {}))
                    data["sections_complete"] = assess_data.get("sections_complete", {})
                    data["sections_last_modified"] = assess_data.get("sections_last_modified", {})
                except Exception:
                    pass

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
                "sections_complete": sum(1 for v in data.get("sections_complete", {}).values() if v),
                "obj_sections_complete": count_objective_complete_sections(str(session_file)),
            }
            sessions.append(session)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read session {session_file}: {e}")
            continue

    return sessions


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


# ─────────────────────────────────────────────────────────────────────────────
# Objective section report rendering
# ─────────────────────────────────────────────────────────────────────────────

def _md_table(headers: list, rows: list) -> list:
    """Return Markdown table as a list of strings. Returns [] when all value cols are blank."""
    if not rows:
        return []
    n = len(headers)
    rows = [[str(r[i]) if i < len(r) else "" for i in range(n)] for r in rows]
    col_w = [len(str(headers[i])) for i in range(n)]
    for r in rows:
        for i, v in enumerate(r):
            col_w[i] = max(col_w[i], len(v))
    def _fmt(cells):
        return "| " + " | ".join(str(v).ljust(col_w[i]) for i, v in enumerate(cells)) + " |"
    sep = "| " + " | ".join("-" * w for w in col_w) + " |"
    return [_fmt(headers), sep] + [_fmt(r) for r in rows]


def _raw_table(headers: list, rows: list) -> list:
    """Return fixed-width plain-text table lines."""
    if not rows:
        return []
    n = len(headers)
    rows = [[str(r[i]) if i < len(r) else "" for i in range(n)] for r in rows]
    col_w = [len(str(headers[i])) for i in range(n)]
    for r in rows:
        for i, v in enumerate(r):
            col_w[i] = max(col_w[i], len(v))
    def _fmt(cells, sep=" | "):
        return "  " + sep.join(str(v).ljust(col_w[i]) for i, v in enumerate(cells))
    divider = "  " + "-+-".join("-" * w for w in col_w)
    return [_fmt(headers), divider] + [_fmt(r) for r in rows]


def _render_objective_md(obj: dict, clean: bool = False) -> list:
    """Render all objective sections as Markdown.

    clean=False: all fields shown; empty values shown as — / *(not answered)*.
    clean=True: only sections/tables/rows with real data are included.
    """
    lines: list = []

    gen  = obj.get("general",      {}) or {}
    act  = obj.get("active",       {}) or {}
    pas  = obj.get("passive",      {}) or {}
    neu  = obj.get("neurological", {}) or {}
    sen  = obj.get("sensory",      {}) or {}
    mus  = obj.get("muscle",       {}) or {}
    func = obj.get("functional",   {}) or {}

    if not any([gen, act, pas, neu, sen, mus, func]):
        return []

    # ── clean-mode helpers ────────────────────────────────────────────────────

    _EMPTY = frozenset(["—", "*(not answered)*", "*(not recorded)*", "*(empty)*", ""])

    def _nodata(v) -> bool:
        return v is None or str(v).strip() in _EMPTY

    def _filter_rows(rows: list, data_from: int = 1) -> list:
        if not clean:
            return rows
        return [r for r in rows if not all(_nodata(c) for c in r[data_from:])]

    def _maybe_table(sl: list, title: str, headers: list, rows: list, data_from: int = 1) -> None:
        rows = _filter_rows(rows, data_from)
        if not rows:
            return
        if title:
            sl.append(f"#### {title}")
        sl.extend(_md_table(headers, rows))

    def _maybe_note(sl: list, lbl: str, v: str) -> None:
        if v:
            sl.append(f"{lbl}: {v}")
        elif not clean:
            sl.append(f"{lbl}: *(empty)*")

    def _flush_section(header: str, sl: list) -> None:
        if sl:
            if clean:
                header = re.sub(r'^(#{1,3})\s*\d{2}\s+', r'\1 ', header)
            lines.append(header)
            lines.extend(sl)
            lines.append("")

    # ── 01 General Observation ────────────────────────────────────────────────
    if gen:
        sl: list[str] = []
        for key, lbl, unit in [("go_height","Height","cm"),("go_weight","Weight","kg"),
                                ("go_bmi","BMI",""),("go_nrs","NRS rest","/10"),
                                ("go_sit_tol","Sit tol","min")]:
            v = (gen.get(key) or "").strip()
            if v:
                sl.append(f"**{lbl}:** {v}{unit}")
            elif not clean:
                sl.append(f"**{lbl}:** *(not recorded)*")
        _posture_def = [("Lumbar lordosis","go_lx_lord"),("Thoracic kyphosis","go_tx_kyph"),
                        ("Antalgic lean","go_lean"),("Sway posture","go_sway"),
                        ("Breathing","go_breath"),("Scapular L","go_scap_l"),
                        ("Scapular R","go_scap_r"),("Muscle wasting","go_wasting"),
                        ("Undress/transfer","go_transfer")]
        posture_rows = []
        for lbl, key in _posture_def:
            v = gen.get(key) or "—"
            cmt = gen.get(f"{key}_cmt", "").strip()
            posture_rows.append([lbl, f"{v} — {cmt}" if cmt else v])
        _maybe_table(sl, "Posture", ["", "Finding"], posture_rows)
        _func_def = [("Gait","go_gait"),("SLS Left","go_sls_l"),
                     ("SLS Right","go_sls_r"),("Sit-to-stand","go_sts")]
        func_rows = []
        for lbl, key in _func_def:
            v = gen.get(key) or "—"
            cmt = gen.get(f"{key}_cmt", "").strip()
            func_rows.append([lbl, f"{v} — {cmt}" if cmt else v])
        _maybe_table(sl, "Functional Movement", ["", "Finding"], func_rows)
        for key, lbl in [("go_posture_notes","*Posture notes*"),
                          ("go_functional_notes","*Functional notes*")]:
            _maybe_note(sl, lbl, gen.get(key, "").strip())
        _flush_section("### 01 General Observation", sl)

    # ── 02 Active Movement ────────────────────────────────────────────────────
    if act:
        sl = []
        lx_rows_def = [("Flexion","lx_flex",True),("Extension","lx_ext",True),
                       ("Lat Flex","lx_lf",False),("Rotation","lx_rot",False)]
        tx_rows_def = [("Flexion","tx_flex",True),("Extension","tx_ext",True),
                       ("Rotation","tx_rot",False)]
        for title, rows_def in [("Lumbar ROM", lx_rows_def), ("Thoracic ROM", tx_rows_def)]:
            tbl_rows = []
            for label, prefix, bilateral in rows_def:
                def _cell(p, s):
                    v   = act.get(f"{p}_{s}_range", "") or ""
                    ps  = act.get(f"{p}_{s}_ps") or ""
                    txt = f"{v}°" if v else "—"
                    return f"{txt} {ps}".strip() if ps else txt
                ax_l = _cell(prefix, "ax_l"); reax_l = _cell(prefix, "reax_l")
                if bilateral:
                    tbl_rows.append([label, ax_l, "—", reax_l, "—"])
                else:
                    ax_r = _cell(prefix, "ax_r"); reax_r = _cell(prefix, "reax_r")
                    tbl_rows.append([label, ax_l, ax_r, reax_l, reax_r])
            _maybe_table(sl, title, ["", "Ax L", "Ax R", "ReAx L", "ReAx R"], tbl_rows)
        for key, lbl in [("am_lx_notes","*Lumbar notes*"),("am_tx_notes","*Thoracic notes*")]:
            _maybe_note(sl, lbl, act.get(key, "").strip())
        _flush_section("### 02 Active Movement", sl)

    # ── 03 Passive Movement ───────────────────────────────────────────────────
    if pas:
        sl = []
        op_def = [("Tx Flexion","op_tx_flex"),("Tx Extension","op_tx_ext"),
                  ("Tx Rot L","op_tx_rot_l"),("Tx Rot R","op_tx_rot_r"),
                  ("Lx Flexion","op_lx_flex"),("Lx Extension","op_lx_ext"),
                  ("Lx Lat Fl L","op_lx_lf_l"),("Lx Lat Fl R","op_lx_lf_r")]
        op_rows = [[lbl, pas.get(f"{p}_ef") or "—", pas.get(f"{p}_resp") or "—"]
                   for lbl, p in op_def]
        _maybe_table(sl, "Overpressure", ["Movement", "End-feel", "Response"], op_rows)
        paivm_levels = ["L5","L4","L3","L2","L1","T12","T11","T10","T9","T8"]
        paivm_rows = [[lv, pas.get(f"pm_{lv}_c") or "—",
                          pas.get(f"pm_{lv}_ul_l") or "—",
                          pas.get(f"pm_{lv}_ul_r") or "—"]
                      for lv in paivm_levels]
        _maybe_table(sl, "PAIVMs", ["Level", "Central", "UL Left", "UL Right"], paivm_rows)
        for key, lbl in [("pm_op_notes","*OP notes*"),("pm_paivm_notes","*PAIVM notes*")]:
            _maybe_note(sl, lbl, pas.get(key, "").strip())
        _flush_section("### 03 Passive Movement & Overpressure", sl)

    # ── 04 Neurological ───────────────────────────────────────────────────────
    if neu:
        sl = []
        neuro_def = [
            ("Knee jerk L3/4","nr_knee"),("Ankle jerk S1","nr_ankle"),("Plantar","nr_plantar"),
            ("L2 Hip flex","nr_l2"),("L3 Knee ext","nr_l3"),("L4 Ankle DF","nr_l4"),
            ("L5 GT ext/EHL","nr_l5"),("S1 PF/evert","nr_s1"),("S2 Ham/KF","nr_s2"),
        ]
        neuro_rows = [[lbl, neu.get(f"{p}_l") or "—", neu.get(f"{p}_r") or "—"]
                      for lbl, p in neuro_def]
        _maybe_table(sl, "", ["Test", "Left", "Right"], neuro_rows)
        _derm_def_nr = [("L2 Ant thigh","sn_l2"),("L3 Med knee","sn_l3"),
                        ("L4 Med leg","sn_l4"),("L5 Lat leg/GT","sn_l5"),
                        ("S1 Lat foot","sn_s1"),("S2 Post thigh","sn_s2")]
        derm_rows_nr = [[lbl, neu.get(f"{p}_l") or "—", neu.get(f"{p}_r") or "—"]
                        for lbl, p in _derm_def_nr]
        _maybe_table(sl, "Dermatomes", ["Level", "Left", "Right"], derm_rows_nr)
        nd_def = [("SLR","nr_slr"),("Slump","nr_slump"),("PKF","nr_pkf")]
        nd_rows = []
        for lbl, p in nd_def:
            ld = neu.get(f"{p}_l_deg","") or ""; lr = neu.get(f"{p}_l_resp","") or "—"
            rd = neu.get(f"{p}_r_deg","") or ""; rr = neu.get(f"{p}_r_resp","") or "—"
            nd_rows.append([lbl, f"{ld}°" if ld else "—", lr,
                                  f"{rd}°" if rd else "—", rr])
        _maybe_table(sl, "Neurodynamics", ["Test", "L °", "L Resp", "R °", "R Resp"], nd_rows)
        umn_items = [("Hyperreflexia","nr_umn_hyper"),("Babinski +","nr_umn_bab"),
                     ("Clonus","nr_umn_clonus"),("Romberg +","nr_umn_romberg"),
                     ("Coord impaired","nr_umn_coord")]
        umn_rows = [[lbl, "Yes" if neu.get(uid) is True else "No" if neu.get(uid) is False else "*(not answered)*"]
                    for lbl, uid in umn_items]
        _maybe_table(sl, "UMN Signs", ["Sign", "Result"], umn_rows)
        _maybe_note(sl, "*Notes:*", neu.get("nr_notes", "").strip())
        _flush_section("### 04 Neurological", sl)

    # ── 05 Sensory ────────────────────────────────────────────────────────────
    if sen:
        sl = []
        ppt = (sen.get("sn_ppt") or "").strip()
        ppt_detail = sen.get("sn_ppt_detail", "").strip()
        if ppt:
            sl.append(f"**PPT (algometer):** {ppt}" + (f" — {ppt_detail}" if ppt_detail else ""))
        elif not clean:
            sl.append("**PPT (algometer):** *(not recorded)*")
        hypo_items = [("Sharp/blunt","sn_sharp_blunt",True),("Two-point discrim","sn_tpd",True),
                      ("Light touch","sn_lt",True),("Body perception","sn_body",False)]
        hyper_items = [("Static allodynia","sn_static_allodynia",True),
                       ("Dynamic allodynia","sn_dynamic_allodynia",True),
                       ("2° hyperalgesia PPT","sn_secondary_hyper",True),
                       ("Pin prick hyper","sn_pin_prick",True),
                       ("Cold hyperalgesia","sn_cold",False),
                       ("Heat hyperalgesia","sn_heat",False),
                       ("Temporal summation","sn_temporal_sum",True)]
        for sec_lbl, items in [("Hyposensitivity", hypo_items), ("Hypersensitivity", hyper_items)]:
            rows = []
            for lbl, sid, has_detail in items:
                v = sen.get(sid)
                if clean and v is None:
                    continue
                state = "Yes" if v is True else "No" if v is False else "*(not answered)*"
                detail = sen.get(f"{sid}_detail", "").strip() if has_detail and v is True else ""
                rows.append([lbl, f"{state} — {detail}" if detail else state])
            if rows:
                sl.append(f"**{sec_lbl}:**")
                sl.extend(_md_table(["Test", "Result"], rows))
        _maybe_note(sl, "*Notes:*", sen.get("sn_notes", "").strip())
        _flush_section("### 05 Sensory", sl)

    # ── 06 Muscle Testing ─────────────────────────────────────────────────────
    if mus:
        sl = []
        ml_def = [("QL (side sit)","ml_ql"),("Thomas test","ml_thomas"),
                  ("Hamstrings SLR","ml_ham")]
        ml_rows = [[lbl, mus.get(f"{p}_l") or "—", mus.get(f"{p}_r") or "—"]
                   for lbl, p in ml_def]
        _maybe_table(sl, "Muscle Length", ["Test", "Left", "Right"], ml_rows)
        ma_def = [("Tx erector spinae","ma_tx_es"),("Transversus abd","ma_tva"),
                  ("Lumbar multifidus","ma_lmf")]
        ma_rows = [[lbl, mus.get(mid) or "—"] for lbl, mid in ma_def]
        _maybe_table(sl, "Muscle Activation", ["Test", "Finding"], ma_rows)
        for key, lbl, unit in [("st_flex","Trunk flexion","reps/min"),
                                ("st_ext","Trunk extension","raises/min")]:
            v = (mus.get(key) or "").strip()
            if v:
                sl.append(f"**{lbl}:** {v} {unit}")
            elif not clean:
                sl.append(f"**{lbl}:** *(not recorded)* {unit}")
        hip_def = [("Hip flexion","sh_hip_flex"),("Hip extension","sh_hip_ext"),
                   ("Hip abduction","sh_hip_abd"),("Hip adduction","sh_hip_add"),
                   ("Hip int rotation","sh_hip_ir"),("Hip ext rotation","sh_hip_er")]
        hip_rows = [[lbl, mus.get(f"{p}_l") or "—", mus.get(f"{p}_r") or "—"]
                    for lbl, p in hip_def]
        _maybe_table(sl, "Hip Strength (Wagner FPX kg)", ["Movement", "Left kg", "Right kg"], hip_rows)
        sij_items = [("Sacral thrust","sij_sacral"),("Post thigh thrust","sij_ptt"),
                     ("Distraction supine","sij_dist"),("Compression s/l","sij_comp"),
                     ("Gaenslen","sij_gaenslen"),("ASLR compression","sij_aslr")]
        sij_rows = [[lbl, "Yes" if mus.get(sid) is True else "No" if mus.get(sid) is False else "*(not answered)*"]
                    for lbl, sid in sij_items]
        _maybe_table(sl, "SIJ Provocation", ["Test", "Result"], sij_rows)
        _maybe_note(sl, "*Notes:*", mus.get("mu_notes", "").strip())
        _flush_section("### 06 Muscle Testing", sl)

    # ── 07 Functional ─────────────────────────────────────────────────────────
    if func:
        sl = []
        obs_def = [("Gait","ft_gait"),("Prone hip rot","ft_phr"),
                   ("Sit-to-stand","ft_sts_q"),("SLS Left","ft_sls_l"),
                   ("SLS Right","ft_sls_r")]
        obs_rows = [[lbl, func.get(fid) or "—"] for lbl, fid in obs_def]
        _maybe_table(sl, "Movement Observation", ["Test", "Finding"], obs_rows)
        bal_def = [("Both legs",["ft_bal_both"]),("Feet together",["ft_bal_feet"]),
                   ("Tandem",["ft_bal_tandem"]),
                   ("SLS eyes open",["ft_sls_eo_l","ft_sls_eo_r"]),
                   ("SLS eyes closed",["ft_sls_ec_l","ft_sls_ec_r"]),
                   ("SLS foam 10cm",["ft_sls_foam_l","ft_sls_foam_r"])]
        bal_rows = []
        for lbl, ids in bal_def:
            vals = [func.get(i,"") or "—" for i in ids]
            if len(ids) == 1:
                vals = [vals[0], "—"]
            bal_rows.append([lbl] + vals)
        _maybe_table(sl, "Balance (Steffen 2002)", ["Test", "Left s", "Right s"], bal_rows)
        cap_def = [("TUG (3m)","ft_tug","s"),("5× Sit-to-Stand","ft_sts5","s"),
                   ("10m comfortable","ft_10m_e","m/s"),("10m fast","ft_10m_f","m/s"),
                   ("2 min walk","ft_2mw","m")]
        cap_rows = [[lbl, f"{func.get(fid,'') or '—'} {unit}".strip() if func.get(fid,"") else "—"]
                    for lbl, fid, unit in cap_def]
        _maybe_table(sl, "Timed Capability", ["Test", "Result"], cap_rows)
        _maybe_note(sl, "*Notes:*", func.get("ft_notes", "").strip())
        _flush_section("### 07 Functional", sl)

    if not lines:
        return []

    obj_heading = "## Objective Examination" if clean else "## 04 Objective Examination"
    lines.insert(0, obj_heading)
    lines.insert(1, "")
    return lines


def _render_objective_raw(obj: dict, lines: list, SEP: str, SEP2: str,
                          clean: bool = False) -> None:
    """Append objective sections in plain-text format to lines list.

    clean=True: omit sections/tables/rows with no real data.
    """
    gen  = obj.get("general",      {}) or {}
    act  = obj.get("active",       {}) or {}
    pas  = obj.get("passive",      {}) or {}
    neu  = obj.get("neurological", {}) or {}
    sen  = obj.get("sensory",      {}) or {}
    mus  = obj.get("muscle",       {}) or {}
    func = obj.get("functional",   {}) or {}

    if not any([gen, act, pas, neu, sen, mus, func]):
        return

    # ── clean-mode helpers ────────────────────────────────────────────────────
    _EMPTY_RAW = frozenset(["-", "(not answered)", "(not recorded)", "(empty)", ""])

    def _nodata(v) -> bool:
        return v is None or str(v).strip() in _EMPTY_RAW

    def _filter_rows(rows: list, data_from: int = 1) -> list:
        if not clean:
            return rows
        return [r for r in rows if not all(_nodata(c) for c in r[data_from:])]

    def _maybe_table(sl: list, headers: list, rows: list, data_from: int = 1) -> None:
        rows = _filter_rows(rows, data_from)
        if not rows:
            return
        sl.extend(_raw_table(headers, rows))

    _obj_header_written = [False]

    def _flush_section(header: str, sl: list) -> None:
        if sl:
            if not _obj_header_written[0]:
                lines.extend(["", SEP, "SECTION 8: OBJECTIVE EXAMINATION", SEP])
                _obj_header_written[0] = True
            lines.extend(["", f"  — {header} —"])
            lines.extend(sl)

    # ── 01 General Observation ────────────────────────────────────────────────
    if gen:
        sl: list[str] = []
        for key, lbl, unit in [("go_height","Height","cm"),("go_weight","Weight","kg"),
                                ("go_bmi","BMI",""),("go_nrs","NRS rest","/10"),
                                ("go_sit_tol","Sit tol","min")]:
            v = (gen.get(key) or "").strip()
            if v:
                sl.append(f"  {lbl}: {v}{unit}")
            elif not clean:
                sl.append(f"  {lbl}: (not recorded)")
        _posture_raw = [("Lumbar lordosis","go_lx_lord"),("Thoracic kyphosis","go_tx_kyph"),
                        ("Antalgic lean","go_lean"),("Sway posture","go_sway"),
                        ("Breathing","go_breath"),("Scapular L","go_scap_l"),
                        ("Scapular R","go_scap_r"),("Muscle wasting","go_wasting"),
                        ("Undress/transfer","go_transfer")]
        p_rows = [[lbl, gen.get(key) or "(not recorded)", gen.get(f"{key}_cmt", "")]
                  for lbl, key in _posture_raw]
        _maybe_table(sl, ["Posture", "Finding", "Comment"], p_rows)
        _func_raw = [("Gait","go_gait"),("SLS Left","go_sls_l"),
                     ("SLS Right","go_sls_r"),("Sit-to-stand","go_sts")]
        f_rows = [[lbl, gen.get(key) or "(not recorded)", gen.get(f"{key}_cmt", "")]
                  for lbl, key in _func_raw]
        _maybe_table(sl, ["Function", "Finding", "Comment"], f_rows)
        for key, lbl in [("go_posture_notes","Posture notes"),
                          ("go_functional_notes","Functional notes")]:
            v = gen.get(key, "").strip()
            if v:
                sl.append(f"  {lbl}: {v}")
            elif not clean:
                sl.append(f"  {lbl}: (empty)")
        _flush_section("01 General Observation", sl)

    # ── 02 Active Movement ────────────────────────────────────────────────────
    if act:
        sl = []
        lx_rows_def = [("Flexion","lx_flex",True),("Extension","lx_ext",True),
                       ("Lat Flex","lx_lf",False),("Rotation","lx_rot",False)]
        tx_rows_def = [("Flexion","tx_flex",True),("Extension","tx_ext",True),
                       ("Rotation","tx_rot",False)]
        for title, rows_def in [("Lumbar ROM", lx_rows_def), ("Thoracic ROM", tx_rows_def)]:
            tbl_rows = []
            for lbl, prefix, bilateral in rows_def:
                def _cell(p, s):
                    v  = act.get(f"{p}_{s}_range", "") or ""
                    ps = act.get(f"{p}_{s}_ps") or ""
                    t  = f"{v}°" if v else "-"
                    return f"{t} {ps}".strip() if ps else t
                ax_l = _cell(prefix,"ax_l"); reax_l = _cell(prefix,"reax_l")
                if bilateral:
                    tbl_rows.append([lbl, ax_l, "-", reax_l, "-"])
                else:
                    ax_r = _cell(prefix,"ax_r"); reax_r = _cell(prefix,"reax_r")
                    tbl_rows.append([lbl, ax_l, ax_r, reax_l, reax_r])
            filtered = _filter_rows(tbl_rows)
            if filtered:
                sl.append(f"  {title}:")
                sl.extend(_raw_table(["", "Ax L", "Ax R", "ReAx L", "ReAx R"], filtered))
            elif not clean:
                sl.append(f"  {title}:")
                sl.extend(_raw_table(["", "Ax L", "Ax R", "ReAx L", "ReAx R"], tbl_rows))
        for key, lbl in [("am_lx_notes","Lumbar notes"),("am_tx_notes","Thoracic notes")]:
            v = act.get(key, "").strip()
            if v:
                sl.append(f"  {lbl}: {v}")
            elif not clean:
                sl.append(f"  {lbl}: (empty)")
        _flush_section("02 Active Movement", sl)

    # ── 03 Passive Movement ───────────────────────────────────────────────────
    if pas:
        sl = []
        op_def = [("Tx Flexion","op_tx_flex"),("Tx Extension","op_tx_ext"),
                  ("Tx Rot L","op_tx_rot_l"),("Tx Rot R","op_tx_rot_r"),
                  ("Lx Flexion","op_lx_flex"),("Lx Extension","op_lx_ext"),
                  ("Lx Lat Fl L","op_lx_lf_l"),("Lx Lat Fl R","op_lx_lf_r")]
        op_rows = [[lbl, pas.get(f"{p}_ef") or "-", pas.get(f"{p}_resp") or "-"]
                   for lbl, p in op_def]
        _maybe_table(sl, ["Overpressure", "End-feel", "Response"], op_rows)
        paivm_levels = ["L5","L4","L3","L2","L1","T12","T11","T10","T9","T8"]
        paivm_rows = [[lv, pas.get(f"pm_{lv}_c") or "-",
                          pas.get(f"pm_{lv}_ul_l") or "-",
                          pas.get(f"pm_{lv}_ul_r") or "-"]
                      for lv in paivm_levels]
        _maybe_table(sl, ["PAIVM", "Central", "UL Left", "UL Right"], paivm_rows)
        for key, lbl in [("pm_op_notes","OP notes"),("pm_paivm_notes","PAIVM notes")]:
            v = pas.get(key, "").strip()
            if v:
                sl.append(f"  {lbl}: {v}")
            elif not clean:
                sl.append(f"  {lbl}: (empty)")
        _flush_section("03 Passive Movement & Overpressure", sl)

    # ── 04 Neurological ───────────────────────────────────────────────────────
    if neu:
        sl = []
        neuro_def = [("Knee jerk L3/4","nr_knee"),("Ankle jerk S1","nr_ankle"),
                     ("Plantar","nr_plantar"),
                     ("L2 Hip flex","nr_l2"),("L3 Knee ext","nr_l3"),
                     ("L4 Ankle DF","nr_l4"),("L5 GT ext/EHL","nr_l5"),
                     ("S1 PF/evert","nr_s1"),("S2 Ham/KF","nr_s2")]
        neuro_rows = [[lbl, neu.get(f"{p}_l") or "-", neu.get(f"{p}_r") or "-"]
                      for lbl, p in neuro_def]
        _maybe_table(sl, ["Test", "Left", "Right"], neuro_rows)
        _derm_raw = [("L2 Ant thigh","sn_l2"),("L3 Med knee","sn_l3"),
                     ("L4 Med leg","sn_l4"),("L5 Lat leg/GT","sn_l5"),
                     ("S1 Lat foot","sn_s1"),("S2 Post thigh","sn_s2")]
        derm_raw_rows = [[lbl, neu.get(f"{p}_l") or "-", neu.get(f"{p}_r") or "-"]
                         for lbl, p in _derm_raw]
        _maybe_table(sl, ["Dermatome", "Left", "Right"], derm_raw_rows)
        nd_def = [("SLR","nr_slr"),("Slump","nr_slump"),("PKF","nr_pkf")]
        nd_rows = []
        for lbl, p in nd_def:
            ld = neu.get(f"{p}_l_deg","") or ""; lr = neu.get(f"{p}_l_resp","") or "-"
            rd = neu.get(f"{p}_r_deg","") or ""; rr = neu.get(f"{p}_r_resp","") or "-"
            nd_rows.append([lbl, f"{ld}°" if ld else "-", lr,
                                  f"{rd}°" if rd else "-", rr])
        _maybe_table(sl, ["Neurodynamics","L°","L Resp","R°","R Resp"], nd_rows)
        umn_items = [("Hyperreflexia","nr_umn_hyper"),("Babinski +","nr_umn_bab"),
                     ("Clonus","nr_umn_clonus"),("Romberg +","nr_umn_romberg"),
                     ("Coord impaired","nr_umn_coord")]
        for lbl, uid in umn_items:
            v = neu.get(uid)
            if clean and v is None:
                continue
            sl.append(f"  {lbl}: {'✓ Yes' if v is True else '✗ No' if v is False else '(not answered)'}")
        v = neu.get("nr_notes", "").strip()
        if v:
            sl.append(f"  Notes: {v}")
        elif not clean:
            sl.append("  Notes: (empty)")
        _flush_section("04 Neurological", sl)

    # ── 05 Sensory ────────────────────────────────────────────────────────────
    if sen:
        sl = []
        ppt_raw = (sen.get("sn_ppt") or "").strip()
        ppt_detail_raw = sen.get("sn_ppt_detail", "").strip()
        if ppt_raw:
            sl.append(f"  PPT (algometer): {ppt_raw}" + (f" — {ppt_detail_raw}" if ppt_detail_raw else ""))
        elif not clean:
            sl.append("  PPT (algometer): (not recorded)")
        hypo_items = [("Sharp/blunt","sn_sharp_blunt",True),
                      ("Two-point discrim","sn_tpd",True),
                      ("Light touch","sn_lt",True),
                      ("Body perception","sn_body",False)]
        hyper_items = [("Static allodynia","sn_static_allodynia",True),
                       ("Dynamic allodynia","sn_dynamic_allodynia",True),
                       ("2° hyperalgesia PPT","sn_secondary_hyper",True),
                       ("Pin prick hyper","sn_pin_prick",True),
                       ("Cold hyperalgesia","sn_cold",False),
                       ("Heat hyperalgesia","sn_heat",False),
                       ("Temporal summation","sn_temporal_sum",True)]
        for items in (hypo_items, hyper_items):
            for lbl, sid, has_detail in items:
                v = sen.get(sid)
                if clean and v is None:
                    continue
                detail = sen.get(f"{sid}_detail", "").strip() if has_detail else ""
                state = "✓ Yes" if v is True else "✗ No" if v is False else "(not answered)"
                sl.append(f"  {lbl}: {state}" + (f" — {detail}" if detail and v is True else ""))
        v = sen.get("sn_notes", "").strip()
        if v:
            sl.append(f"  Notes: {v}")
        elif not clean:
            sl.append("  Notes: (empty)")
        _flush_section("05 Sensory", sl)

    # ── 06 Muscle Testing ─────────────────────────────────────────────────────
    if mus:
        sl = []
        ml_def = [("QL (side sit)","ml_ql"),("Thomas test","ml_thomas"),
                  ("Hamstrings SLR","ml_ham")]
        ml_rows = [[lbl, mus.get(f"{p}_l") or "-", mus.get(f"{p}_r") or "-"]
                   for lbl, p in ml_def]
        _maybe_table(sl, ["Muscle Length", "Left", "Right"], ml_rows)
        ma_def = [("Tx erector spinae","ma_tx_es"),("Transversus abd","ma_tva"),
                  ("Lumbar multifidus","ma_lmf")]
        ma_rows = [[lbl, mus.get(mid) or "-"] for lbl, mid in ma_def]
        _maybe_table(sl, ["Activation", "Finding"], ma_rows)
        for key, lbl, unit in [("st_flex","Trunk flexion","reps/min"),
                                ("st_ext","Trunk extension","raises/min")]:
            v = (mus.get(key) or "").strip()
            if v:
                sl.append(f"  {lbl}: {v} {unit}")
            elif not clean:
                sl.append(f"  {lbl}: (not recorded) {unit}")
        hip_def = [("Hip flexion","sh_hip_flex"),("Hip extension","sh_hip_ext"),
                   ("Hip abduction","sh_hip_abd"),("Hip adduction","sh_hip_add"),
                   ("Hip int rotation","sh_hip_ir"),("Hip ext rotation","sh_hip_er")]
        hip_rows = [[lbl, mus.get(f"{p}_l") or "-", mus.get(f"{p}_r") or "-"]
                    for lbl, p in hip_def]
        _maybe_table(sl, ["Hip Strength (kg)", "Left", "Right"], hip_rows)
        sij_items = [("Sacral thrust","sij_sacral"),("Post thigh thrust","sij_ptt"),
                     ("Distraction supine","sij_dist"),("Compression s/l","sij_comp"),
                     ("Gaenslen","sij_gaenslen"),("ASLR compression","sij_aslr")]
        for lbl, sid in sij_items:
            v = mus.get(sid)
            if clean and v is None:
                continue
            sl.append(f"  SIJ {lbl}: {'✓ Yes' if v is True else '✗ No' if v is False else '(not answered)'}")
        v = mus.get("mu_notes", "").strip()
        if v:
            sl.append(f"  Notes: {v}")
        elif not clean:
            sl.append("  Notes: (empty)")
        _flush_section("06 Muscle Testing", sl)

    # ── 07 Functional ─────────────────────────────────────────────────────────
    if func:
        sl = []
        obs_def = [("Gait","ft_gait"),("Prone hip rot","ft_phr"),
                   ("Sit-to-stand","ft_sts_q"),("SLS Left","ft_sls_l"),
                   ("SLS Right","ft_sls_r")]
        obs_rows = [[lbl, func.get(fid) or "-"] for lbl, fid in obs_def]
        _maybe_table(sl, ["Movement Obs", "Finding"], obs_rows)
        bal_def = [("Both legs",["ft_bal_both"],"s"),("Feet together",["ft_bal_feet"],"s"),
                   ("Tandem",["ft_bal_tandem"],"s"),
                   ("SLS eyes open",["ft_sls_eo_l","ft_sls_eo_r"],"s"),
                   ("SLS eyes closed",["ft_sls_ec_l","ft_sls_ec_r"],"s"),
                   ("SLS foam 10cm",["ft_sls_foam_l","ft_sls_foam_r"],"s")]
        bal_rows = []
        for lbl, ids, _ in bal_def:
            vals = [func.get(i,"") or "-" for i in ids]
            if len(ids) == 1:
                vals = [vals[0], "-"]
            bal_rows.append([lbl] + vals)
        _maybe_table(sl, ["Balance (Steffen)", "Left s", "Right s"], bal_rows)
        cap_def = [("TUG (3m)","ft_tug","s"),("5× STS","ft_sts5","s"),
                   ("10m comfortable","ft_10m_e","m/s"),("10m fast","ft_10m_f","m/s"),
                   ("2 min walk","ft_2mw","m")]
        cap_rows = [[lbl, f"{func.get(fid,'') or '-'} {unit}".strip()]
                    for lbl, fid, unit in cap_def]
        _maybe_table(sl, ["Timed Capability", "Result"], cap_rows)
        v = func.get("ft_notes", "").strip()
        if v:
            sl.append(f"  Notes: {v}")
        elif not clean:
            sl.append("  Notes: (empty)")
        _flush_section("07 Functional", sl)



def export_session_report(session_file: str, clean: bool = False) -> str:  # noqa: C901
    """
    Write a Markdown report to the session directory.

    clean=False (default): writes *_report.md with all fields shown.
    clean=True: writes *_clean.md with only fields that have data.
    Returns the output path, or empty string on failure.
    """
    import time as _time

    try:
        data = json.loads(Path(session_file).read_text()) if Path(session_file).exists() else {}
    except Exception as e:
        logger.error(f"export_session_report: {e}")
        return ""

    # Overlay TUI assessment data from the separate _assessment.json
    assess_p = assessment_path(session_file)
    if assess_p.exists():
        try:
            assess_data = json.loads(assess_p.read_text())
            data["assessment"] = assess_data.get("assessment", data.get("assessment", {}))
            data.setdefault("sections_complete", assess_data.get("sections_complete", {}))
        except Exception:
            pass

    # Load objective sections from _objective.json
    obj_file_data = load_objective(session_file)
    obj_assessment = obj_file_data.get("assessment", {})

    session_dir  = Path(session_file).parent
    session_name = data.get("session_name", "session")
    out_name     = f"{session_name}_clean.md" if clean else f"{session_name}_report.md"
    out_path     = session_dir / out_name

    a = data.get("assessment", {})
    lines: list[str] = []
    _pending: list[str] = []  # buffered section/sub headers waiting for content

    # ── helpers ────────────────────────────────────────────────────────────
    def _v(val) -> str:
        if val is True:  return "Yes"
        if val is False: return "No"
        if val is None:  return "*(not answered)*"
        s = str(val).strip()
        return s if s else "*(empty)*"

    def _emit(*ls: str) -> None:
        if _pending:
            lines.extend(_pending)
            _pending.clear()
        lines.extend(ls)

    def sec(title):
        if clean:
            if title == "Body Chart Summary":
                _pending[:] = []  # suppress entirely in clean mode
                return
            # Strip "Section N: " prefix
            clean_title = re.sub(r'^Section \d+:\s*', '', title)
            if clean_title != title:
                # Section 1 (Consent) — emit only a divider, no heading
                if title.startswith("Section 1:"):
                    _pending[:] = ["\n---\n"]
                else:
                    _pending[:] = [f"\n---\n\n## {clean_title}\n"]
            else:
                _pending[:] = [f"\n---\n\n## {title}\n"]
        else:
            lines.append(f"\n---\n\n## {title}\n")

    def sub(title):
        clean_title = title.replace(" (ICE+)", "") if clean else title
        if clean:
            while _pending and _pending[-1].lstrip().startswith("### "):
                _pending.pop()
            _pending.append(f"\n### {clean_title}\n")
        else:
            lines.append(f"\n### {title}\n")

    def _empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, str) and not val.strip():
            return True
        return False

    def f(fid, d):
        val = d.get(fid)
        if clean and _empty(val):
            return
        _emit(f"**{_label(fid)}:** {_v(val)}")

    def txt(fid, d):
        val = (d.get(fid) or "").strip()
        if clean and not val:
            return
        label = _label(fid)
        if val and "\n" in val:
            _emit(f"**{label}:**  ")
            for row in val.split("\n"):
                _emit((row + "  ") if (clean and row.strip()) else row)
            _emit("")
        elif val:
            _emit(f"**{label}:** {val}")
        else:
            _emit(f"**{label}:** *(empty)*")

    # ── header ──────────────────────────────────────────────────────────────
    c_hdr = a.get("consent", {}) or {}
    preferred_name = c_hdr.get("preferred_name", "").strip() or "*(not set)*"
    created  = data.get("created", 0)
    date_str = _time.strftime("%d %b %Y %H:%M", _time.localtime(created)) if created else "*(unknown)*"
    regions  = ", ".join(data.get("regions", [])) or "*(not set)*"

    if clean:
        lines.extend([f"**Date:** {date_str}  ", ""])
    else:
        lines.extend(["# Physiotherapy Assessment — Full Record", "",
                      f"**Patient:** {preferred_name}  ",
                      f"**Date:** {date_str}  ",
                      f"**Region:** {regions}  ",
                      f"**Session ID:** {data.get('session_name', '')}  ",
                      ""])

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1: CONSENT & SETUP
    # ════════════════════════════════════════════════════════════════════════
    c = a.get("consent", {}) or {}
    sec("Section 1: Consent & Setup")

    sub("Consent")
    f("consent_to_proceed",       c)
    f("consent_sensitive_topics", c)
    f("preferred_name",           c)

    sub("Session Framing")
    f("pain_multifactorial_explained",    c)
    f("education_as_treatment_explained", c)
    txt("patient_expectations",           c)

    sub("Patient Perspective (ICE+)")
    txt("reason_for_attending",      c)
    f("cause_understanding",         c)
    txt("cause_understanding_detail", c)
    txt("prognosis_expectations",    c)
    txt("treatment_preference",      c)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2: SUBJECTIVE EXAMINATION
    # ════════════════════════════════════════════════════════════════════════
    s = a.get("subjective", {}) or {}
    sec("Section 2: Subjective Examination")

    sub("Symptoms")
    f("body_chart_completed", s)
    note_fields = s.get("note_fields") or {}
    for sid, nf in note_fields.items():
        if any(nf.get(k, "").strip() for k in ("loc", "nat", "agg", "ease")):
            _emit(f"**Note {sid}:**  ")
            if nf.get("loc", "").strip():
                _emit(f"  Location: {nf['loc'].strip()}  ")
            if nf.get("nat", "").strip():
                _emit(f"  Nature: {nf['nat'].strip()}  ")
            if nf.get("agg", "").strip():
                _emit(f"  Aggravating: {nf['agg'].strip()}  ")
            if nf.get("ease", "").strip():
                _emit(f"  Easing: {nf['ease'].strip()}  ")
            _emit("")
    if s.get("misc_loc", "").strip() or s.get("misc_nat", "").strip():
        _emit("**Misc symptoms (no note):**  ")
        if s.get("misc_loc", "").strip():
            _emit(f"  Location: {s['misc_loc'].strip()}  ")
        if s.get("misc_nat", "").strip():
            _emit(f"  Nature: {s['misc_nat'].strip()}  ")
        _emit("")

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
    f("flareup_rare",              s)
    f("flareup_occasional",        s)
    f("flareup_frequent",          s)
    txt("flareup_triggers",        s)
    txt("flareup_predictability",  s)
    txt("flareup_duration",        s)

    sub("Self-Management & Control")
    f("pain_control_score",       s)
    txt("flareup_prevention",     s)
    txt("management_strategies",  s)
    f("confidence_score",         s)

    sub("Activity & Exercise")
    txt("pre_activity_level",     s)
    txt("current_activity_level", s)
    txt("exercise_type",          s)
    txt("exercise_dose",          s)
    txt("exercise_response",      s)

    sub("Work")
    txt("pre_injury_role",     s)
    f("pre_injury_hours",      s)
    txt("pre_injury_duties",   s)
    txt("current_work_status", s)
    f("current_hours",         s)
    txt("current_duties",      s)

    sub("Sleep")
    txt("bed_description",          s)
    f("sleep_difficulty",           s)
    f("sleep_difficulty_severity",  s)
    f("sleep_onset_time",           s)
    txt("sleep_position",           s)
    f("total_sleep_hours",          s)
    f("night_waking",               s)
    txt("night_waking_frequency",   s)
    txt("night_waking_reason",      s)
    f("bed_exits_count",            s)
    f("night_waking_severity",      s)
    txt("morning_stiffness",        s)
    f("daytime_naps",               s)
    txt("nap_frequency",            s)
    f("nap_duration",               s)
    txt("energy_levels",            s)

    sub("Behaviour of Symptoms")
    txt("aggravating_factors",     s)
    txt("easing_factors",          s)
    f("mood_influences",           s)
    txt("daily_pattern_comments",  s)

    sub("Psychosocial")
    txt("social_situation",        s)
    txt("financial_status",        s)
    txt("cultural_considerations", s)
    txt("psychological_distress",  s)
    txt("screening_tool",          s)

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
    sec("Section 3: Medical Screening")

    sub("Comorbidities / PMH")
    f("no_previous_injuries",    m)
    txt("previous_injuries",     m)
    f("comorbid_cancer",         m)
    f("comorbid_mental_health",  m)
    f("comorbid_osteoporosis",   m)
    f("comorbid_inflammatory",   m)
    f("comorbid_fibromyalgia",   m)
    f("comorbid_cfs",            m)
    f("comorbid_ibs",            m)
    f("comorbid_whiplash",       m)
    f("comorbid_skin_rash",      m)
    f("comorbid_drug_alcohol",   m)
    f("comorbid_fatigue_memory", m)
    txt("comorbid_other",        m)

    sub("Cardiovascular Risk Factors")
    f("cvd_hypercholesterolaemia", m)
    f("cvd_cardiac",               m)
    f("cvd_vascular",              m)
    f("cvd_stroke_tia",            m)
    f("cvd_diabetes",              m)
    f("cvd_corticosteroids",       m)
    f("cvd_clotting",              m)
    f("cvd_ocp",                   m)
    f("cvd_smoker",                m)
    f("cvd_postpartum",            m)
    f("cvd_familial_history",      m)

    sub("Red Flags — Malignancy")
    f("rf_weight_loss",         m)
    f("rf_cancer_history",      m)
    f("rf_age_50_spinal",       m)
    f("rf_failed_conservative", m)

    sub("Red Flags — Fracture")
    f("rf_trauma",                   m)
    f("rf_corticosteroids_fracture", m)
    f("rf_osteoporosis_fracture",    m)

    sub("Red Flags — Infection")
    f("rf_fever",           m)
    f("rf_immunosuppressed", m)
    f("rf_spinal_procedure", m)

    sub("Red Flags — Cauda Equina (URGENT)")
    f("rf_saddle_anaesthesia",  m)
    f("rf_bladder_disturbance", m)
    f("rf_bowel_disturbance",   m)
    txt("cauda_equina_action",  m)

    sub("Red Flags — Spinal Cord (URGENT)")
    f("rf_bilateral_paraesthesia", m)
    f("rf_gait_disturbance",       m)
    txt("spinal_cord_action",      m)

    sub("Upper Motor Neurone Signs")
    f("umn_hyperreflexia",    m)
    f("umn_babinski",         m)
    f("umn_clonus",           m)
    f("umn_romberg",          m)
    f("umn_coordination",     m)
    txt("umn_interpretation", m)

    sub("Differential — Ankylosing Spondylitis")
    f("diff_as_insidious",          m)
    f("diff_as_lumbar_sij",         m)
    f("diff_as_inflammatory",       m)
    f("diff_as_breathing",          m)
    f("diff_as_fever_weight_loss",  m)
    f("diff_as_likelihood",         m)
    txt("diff_as_action",           m)

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
    meds_list = m.get("medications", [])
    if meds_list:
        med_rows = []
        for i, med in enumerate(meds_list, 1):
            name     = (med.get("name", "") or "").strip()
            dose     = (med.get("dose", "") or "").strip()
            timing   = (med.get("timing", "") or "").strip()
            comments = (med.get("comments", "") or "").strip()
            med_rows.append([str(i), name or "—", dose or "—", timing or "—", comments or "—"])
        _emit(*_md_table(["#", "Name", "Dose", "Timing", "Comments"], med_rows))
    elif not clean:
        _emit("*(none recorded)*")

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 4: PAIN CLASSIFICATION
    # ════════════════════════════════════════════════════════════════════════
    pc = a.get("pain_classification", {}) or {}
    sec("Section 4: Pain Classification")

    sub("Inflammatory Pain Features")
    f("infl_constant",   pc)
    f("infl_morning",    pc)
    f("infl_sleep",      pc)
    f("infl_activity",   pc)
    f("infl_likelihood", pc)

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
    f("noci_exam_mechanical",   pc)
    f("noci_exam_palpation",    pc)
    f("noci_exam_hyperalgesia", pc)
    f("noci_exam_antalgic",     pc)
    f("noci_likelihood",        pc)
    txt("noci_interpretation",  pc)

    sub("Neuropathic Pain — Subjective Features")
    f("neuro_subj_quality",         pc)
    f("neuro_subj_nerve_injury",    pc)
    f("neuro_subj_neurological",    pc)
    f("neuro_subj_dermatomal",      pc)
    f("neuro_subj_medication",      pc)
    f("neuro_subj_severity",        pc)
    f("neuro_subj_neural_loading",  pc)
    f("neuro_subj_dysaesthesia",    pc)
    f("neuro_subj_spontaneous",     pc)

    sub("Neuropathic Pain — Examination Features")
    f("neuro_exam_neurodynamic",     pc)
    f("neuro_exam_neural_palpation", pc)
    f("neuro_exam_neurology",        pc)
    f("neuro_exam_antalgic",         pc)
    f("neuro_exam_hyperalgesia",     pc)
    f("neuro_likelihood",            pc)
    txt("neuro_interpretation",      pc)

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
    f("summary_dominant",        pc)
    txt("summary_contributing",  pc)
    txt("summary_reasoning",     pc)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 5: OUTCOME MEASURES
    # ════════════════════════════════════════════════════════════════════════
    om = a.get("outcome_measures", {}) or {}
    sec("Section 5: Outcome Measures")

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
    f("pcl5_score",    om)
    f("pcl5_interp",   om)
    txt("pcl5_action", om)

    sub("Sleep Measures")
    f("isi_score",   om)
    f("isi_interp",  om)
    f("pbas_score",  om)
    f("pbas_interp", om)

    sub("Additional Measures")
    f("add_audit",  om)
    f("add_dudit",  om)
    txt("add_epoc", om)
    txt("add_other", om)

    sub("Hypothesis Testing")
    hyp_rows = []
    for i in range(3):
        measure   = (om.get(f"hyp_{i}_measure",   "") or "").strip()
        baseline  = (om.get(f"hyp_{i}_baseline",  "") or "").strip()
        interval  = (om.get(f"hyp_{i}_interval",  "") or "").strip()
        rationale = (om.get(f"hyp_{i}_rationale", "") or "").strip()
        if clean and not any([measure, baseline, interval, rationale]):
            continue
        hyp_rows.append([str(i + 1), measure or "—", baseline or "—", interval or "—", rationale or "—"])
    if hyp_rows:
        _emit(*_md_table(["#", "Measure", "Baseline", "Interval", "Rationale"], hyp_rows))

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 6: DIAGNOSIS
    # ════════════════════════════════════════════════════════════════════════
    dx = a.get("diagnosis", {}) or {}
    sec("Section 6: Diagnosis")

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
    f("mixed_dominant",    dx)
    txt("mixed_reasoning", dx)

    sub("SMART Goals")
    f("goal_1", dx)
    f("goal_2", dx)
    f("goal_3", dx)
    f("goal_4", dx)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 7: BARRIERS & TREATMENT PLAN
    # ════════════════════════════════════════════════════════════════════════
    br = a.get("barriers", {}) or {}
    sec("Section 7: Barriers & Treatment Plan")

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
    f("b_psych_depression",        br)
    f("bx_dep_severity",           br)
    f("bx_dep_psychiatry",         br)
    f("b_psych_anxiety",           br)
    f("bx_anx_severity",           br)
    f("bx_anx_psychiatry",         br)
    f("b_psych_stress",            br)
    f("bx_stress_severity",        br)
    f("bx_stress_psychiatry",      br)
    f("b_psych_catastrophising",   br)
    f("b_psych_self_efficacy",     br)
    f("b_psych_unhelpful_beliefs", br)
    f("bx_belief_expectations",    br)
    f("bx_belief_symptom_focus",   br)
    f("bx_belief_cure_focus",      br)
    f("bx_belief_further_tx",      br)
    f("b_psych_ptsd",              br)
    f("bx_ptsd_mechanism",         br)
    f("bx_ptsd_psychiatry",        br)
    f("b_psych_readiness",         br)

    sub("Sleep & Social / Contextual Barriers")
    f("b_sleep_disturbed",     br)
    f("b_social_home",         br)
    f("bx_soc_family_support", br)
    f("bx_soc_social_support", br)
    f("bx_soc_relationship",   br)
    f("bx_soc_personal_rel",   br)
    f("bx_soc_financial",      br)
    f("bx_soc_residential",    br)
    f("bx_soc_distance",       br)
    f("b_social_rtw",          br)

    sub("Medical / Systemic Barriers")
    f("b_med_red_flag",      br)
    f("bi_red_flag_detail",  br)
    f("b_med_substance",     br)
    f("bi_substance_detail", br)
    f("b_med_as",            br)
    f("b_med_aaa",           br)
    f("b_med_vascular",      br)
    f("b_med_cervical_ha",   br)
    f("b_med_medico_legal",  br)

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
    txt("fu_next_focus",   br)
    txt("fu_monitoring",   br)
    f("fu_om_schedule",    br)
    f("ps_questionnaires", br)
    f("ps_eppoc",          br)
    f("ps_ptsd_scored",    br)
    f("ps_isi_pbas",       br)
    f("ps_csi",            br)
    f("ps_audit_dudit",    br)

    # ════════════════════════════════════════════════════════════════════════
    # SCRATCHPAD
    # ════════════════════════════════════════════════════════════════════════
    sp = a.get("scratchpad", {}) or {}
    sec("Scratchpad Notes")
    notes = (sp.get("notes") or "").strip()
    if notes:
        for row in notes.split("\n"):
            _emit((row + "  ") if (clean and row.strip()) else row)
    elif not clean:
        _emit("*(empty)*")

    # ════════════════════════════════════════════════════════════════════════
    # BODY CHART SUMMARY — omitted in clean mode
    # ════════════════════════════════════════════════════════════════════════
    if not clean:
        subj_chart = data.get("subjective", {}) or {}
        obj_chart  = data.get("objective",  {}) or {}
        sec("Body Chart Summary")
        n_strokes = len(subj_chart.get("strokes", []))
        n_notes   = len(subj_chart.get("notes", []))
        n_arrows  = len(subj_chart.get("arrows", []))
        n_zones   = len(obj_chart.get("zones", []))
        n_points  = len(obj_chart.get("points", []))
        _emit(f"**Symptom strokes drawn:** {n_strokes}",
              f"**Note annotations:** {n_notes}",
              f"**Arrows:** {n_arrows}",
              f"**Objective zones:** {n_zones}",
              f"**Measurement points (PPT):** {n_points}")

    # ════════════════════════════════════════════════════════════════════════
    # OBJECTIVE EXAMINATION
    # ════════════════════════════════════════════════════════════════════════
    obj_lines = _render_objective_md(obj_assessment, clean=clean)
    if obj_lines:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.extend(obj_lines)

    # ── Write ──────────────────────────────────────────────────────────────
    try:
        out_path.write_text("\n".join(lines))
        logger.info(f"Report written to {out_path}")
        return str(out_path)
    except Exception as e:
        logger.error(f"export_session_report write failed: {e}")
        return ""


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
    # Write to TUI-owned _assessment.json — GTK never touches this file.
    path = assessment_path(session_file)
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

        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved all sections to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save all sections to {path}: {e}")
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


def export_raw_report(session_data: dict, clean: bool = False) -> str:  # noqa: C901
    """
    Generate a plain-text export of session fields.

    clean=False (default): every field shown; unanswered fields show "(not answered)".
    clean=True: only fields with real data; empty fields and their headers are omitted.
    """
    import time as _time

    SEP  = "═" * 60
    SEP2 = "─" * 60

    lines: list[str] = []
    _pending: list[str] = []  # buffered section/sub headers waiting for content
    a = session_data.get("assessment", {})

    # ── helpers ─────────────────────────────────────────────────────────────

    def _emit(*ls: str) -> None:
        if _pending:
            lines.extend(_pending)
            _pending.clear()
        lines.extend(ls)

    def sec(title: str) -> None:
        if clean:
            _pending[:] = ["", SEP, title, SEP]
        else:
            lines.extend(["", SEP, title, SEP])

    def sub(title: str) -> None:
        if clean:
            while _pending and _pending[-1].lstrip().startswith("— "):
                _pending.pop()
            _pending.append(f"  — {title} —")
        else:
            lines.append(f"  — {title} —")

    def _empty(val) -> bool:
        if val is None:
            return True
        if isinstance(val, str) and not val.strip():
            return True
        return False

    def f(fid: str, d: dict) -> None:
        val = d.get(fid)
        if clean and _empty(val):
            return
        label = _label(fid)
        if isinstance(val, str) and "\n" in val.strip():
            _emit(f"  {label}:")
            for row in val.strip().split("\n"):
                _emit(f"    {row}" if row.strip() else "")
        else:
            _emit(f"  {label}: {_val_raw(val)}")

    def txt(fid: str, d: dict) -> None:
        val = (d.get(fid) or "").strip()
        if clean and not val:
            return
        label = _label(fid)
        _emit(f"  {label}:")
        if val:
            for row in val.split("\n"):
                _emit(f"    {row}")
        else:
            _emit("    (empty)")

    # ── header ──────────────────────────────────────────────────────────────

    c_hdr = a.get("consent", {}) or {}
    preferred_name = c_hdr.get("preferred_name", "").strip() or "(not set)"
    session_name   = session_data.get("session_name", "")
    created        = session_data.get("created", 0)
    date_str       = _time.strftime("%d %b %Y %H:%M", _time.localtime(created)) if created else "(unknown)"
    regions        = ", ".join(session_data.get("regions", [])) or "(not set)"

    title = "PHYSIOTHERAPY ASSESSMENT — ENTERED DATA" if clean else "PHYSIOTHERAPY ASSESSMENT — FULL RAW DATA"
    lines.extend([SEP, title, f"Patient:    {preferred_name}", f"Date:       {date_str}",
                  f"Region:     {regions}", f"Session ID: {session_name}", SEP])

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
    note_fields_r = s.get("note_fields") or {}
    for sid, nf in note_fields_r.items():
        if any(nf.get(k, "").strip() for k in ("loc", "nat", "agg", "ease")):
            _emit(f"  Note {sid}:")
            for key, label in (("loc","Location"),("nat","Nature"),("agg","Aggravating"),("ease","Easing")):
                val = nf.get(key, "").strip()
                if val or not clean:
                    _emit(f"    {label}:")
                    for row in (val or "(empty)").split("\n"):
                        _emit(f"      {row}")
    if s.get("misc_loc","").strip() or s.get("misc_nat","").strip():
        _emit("  Misc symptoms (no note):")
        for key, label in (("misc_loc","Location"),("misc_nat","Nature")):
            val = s.get(key,"").strip()
            if val or not clean:
                _emit(f"    {label}:")
                for row in (val or "(empty)").split("\n"):
                    _emit(f"      {row}")

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
            _emit(f"  {i}. {med_str}")
    elif not clean:
        _emit("  (none recorded)")

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
        if clean and not any([measure, baseline, interval, rationale]):
            continue
        _emit(
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
            _emit(f"  {row}")
    elif not clean:
        _emit("  (empty)")

    # ════════════════════════════════════════════════════════════════════════
    # OBJECTIVE EXAMINATION
    # ════════════════════════════════════════════════════════════════════════
    obj_assessment = session_data.get("objective_assessment", {}) or {}
    _render_objective_raw(obj_assessment, lines, SEP, SEP2, clean=clean)

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
    if not clean or any([n_strokes, n_notes, n_arrows, n_zones, n_points]):
        _emit(f"  Symptom strokes drawn:    {n_strokes}",
              f"  Note annotations:         {n_notes}",
              f"  Arrows:                   {n_arrows}",
              f"  Objective zones:          {n_zones}",
              f"  Measurement points (PPT): {n_points}")

    # symptom types from the chart watcher summary (if present)
    body_chart = session_data.get("body_chart") or session_data.get("assessment", {}).get("body_chart")
    if isinstance(body_chart, dict):
        sym_types = body_chart.get("symptom_types_used", [])
        if sym_types:
            _emit(f"  Symptom types used: {', '.join(str(t) for t in sym_types)}")
        views = body_chart.get("views_drawn", [])
        if views:
            _emit(f"  Views drawn: {', '.join(str(v) for v in views)}")

    # ── footer ──────────────────────────────────────────────────────────────
    footer_title = "END OF ASSESSMENT DATA" if clean else "END OF RAW ASSESSMENT DATA"
    lines.extend(["", SEP, footer_title,
                  f"Generated: {_time.strftime('%d %b %Y %H:%M:%S')}",
                  "For clinical use only — verify all entries before use", SEP])

    return "\n".join(lines)


def save_raw_report(session_file: str) -> str:
    """
    Generate and save a raw plain-text report into the session directory.

    Output: <session_dir>/<session_name>_raw.txt  (same folder as all other
    session files — overwrites on each call so the file stays current).
    Returns the output path, or empty string on failure.
    """
    try:
        data = json.loads(Path(session_file).read_text()) if Path(session_file).exists() else {}
    except Exception as e:
        logger.error(f"save_raw_report: failed to read session: {e}")
        return ""

    # Overlay TUI assessment data from the separate _assessment.json
    assess_p = assessment_path(session_file)
    if assess_p.exists():
        try:
            assess_data = json.loads(assess_p.read_text())
            data["assessment"] = assess_data.get("assessment", data.get("assessment", {}))
            data.setdefault("sections_complete", assess_data.get("sections_complete", {}))
        except Exception:
            pass

    # Load objective sections from _objective.json
    obj_file_data = load_objective(session_file)
    data["objective_assessment"] = obj_file_data.get("assessment", {})

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


def save_clean_reports(session_file: str) -> None:
    """
    Generate and save *_clean.txt and *_clean.md containing only fields with data.

    Called from _do_save() alongside save_raw_report() and export_session_report().
    Errors are logged but never raised — clean reports are non-critical.
    """
    try:
        data = json.loads(Path(session_file).read_text()) if Path(session_file).exists() else {}
    except Exception as e:
        logger.error(f"save_clean_reports: failed to read session: {e}")
        return

    assess_p = assessment_path(session_file)
    if assess_p.exists():
        try:
            assess_data = json.loads(assess_p.read_text())
            data["assessment"] = assess_data.get("assessment", data.get("assessment", {}))
            data.setdefault("sections_complete", assess_data.get("sections_complete", {}))
        except Exception:
            pass

    obj_file_data = load_objective(session_file)
    data["objective_assessment"] = obj_file_data.get("assessment", {})

    session_name = data.get("session_name", "session")
    session_dir  = Path(session_file).parent

    try:
        content = export_raw_report(data, clean=True)
        clean_txt = session_dir / f"{session_name}_clean.txt"
        clean_txt.write_text(content, encoding="utf-8")
        logger.debug(f"Clean txt written to {clean_txt}")
    except Exception as e:
        logger.error(f"save_clean_reports: txt write failed: {e}")

    export_session_report(session_file, clean=True)


def save_docx_report(session_file: str) -> str:
    """
    Convert *_clean.md to *_clean.docx using pandoc.

    Requires pandoc on PATH. Silent no-op if pandoc is absent.
    Returns the output path on success, empty string on failure.
    """
    p = Path(session_file)
    session_name = p.stem.replace("_session", "")
    md_path   = p.parent / f"{session_name}_clean.md"
    docx_path = p.parent / f"{session_name}_clean.docx"

    if not md_path.exists():
        logger.warning(f"save_docx_report: {md_path} not found — run save_clean_reports first")
        return ""

    try:
        result = subprocess.run(
            ["pandoc", str(md_path), "-o", str(docx_path)],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            logger.debug(f"Docx written to {docx_path}")
            return str(docx_path)
        logger.error(f"pandoc failed: {result.stderr.decode().strip()}")
        return ""
    except FileNotFoundError:
        logger.warning("pandoc not found — skipping docx generation")
        return ""
    except Exception as e:
        logger.error(f"save_docx_report: {e}")
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
        "version": 3,
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
            "stroke_clusters": [],
            "misc_cluster_ids": [],
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
