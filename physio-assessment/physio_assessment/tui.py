"""
Physiotherapy Assessment TUI using Textual framework.

Integrates with GTK body chart via session JSON file watcher.
Ctrl+B  — focus body chart (signal file → GTK raises its own window)
Ctrl+E  — export session report to Markdown
Ctrl+S  — manual save
Ctrl+L  — return to session list
"""

import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from datetime import datetime

from rich.text import Text

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Header, Footer, Static, Label, Input, TextArea, Button, ListItem, ListView
from textual.binding import Binding

from .watcher import BodyChartWatcher
from .storage import (
    load_assessment, save_assessment, list_sessions, create_new_session,
    read_gtk_pid, read_tui_socket, write_focus_signal, export_session_report,
    save_raw_report,
)
from .assessment_view import AssessmentView



logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Window-focus helpers
# ---------------------------------------------------------------------------

def _process_alive(pid: int | None) -> bool:
    """Return True if a process with this PID is currently running."""
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _focus_tui_window() -> None:
    """Focus the kitty terminal window containing this TUI process (non-blocking)."""
    tui_socket = read_tui_socket()
    if tui_socket:
        # kitty remote control: focus the kitty window listening on this socket
        subprocess.Popen(
            ["kitty", "@", "--to", tui_socket, "focus-window"],
            close_fds=True,
            stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------------------
# Session list screen
# ---------------------------------------------------------------------------

class SessionListRow(Static):
    """Single session row in the session list."""

    class Selected(Message):
        def __init__(self, session_path: str) -> None:
            super().__init__()
            self.session_path = session_path

    def __init__(self, session: dict, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.patient_id = session["patient_id"]
        self.session_label = session["session_label"]
        self.session_path = session["path"]
        self.sections_complete = session["sections_complete"]
        self.obj_sections_complete = session.get("obj_sections_complete", 0)
        self.body_chart_data = session["body_chart_data"]
        self.date = session["date"]

    def on_click(self) -> None:
        self.post_message(self.Selected(self.session_path))

    def render(self) -> str:
        if isinstance(self.date, str):
            try:
                dt = datetime.fromisoformat(self.date.replace("Z", "+00:00"))
                date_str = dt.strftime("%d %b %H:%M")
            except Exception:
                date_str = self.date[:10] if self.date else ""
        else:
            date_str = datetime.fromtimestamp(self.date).strftime("%d %b %H:%M")

        body_chart_indicator = "●" if self.body_chart_data else "○"
        top_line = f"{self.patient_id}   {date_str}   {body_chart_indicator}   S {self.sections_complete}/7  O {self.obj_sections_complete}/7"
        lines = [top_line]
        if self.session_label:
            lines.append(f"  {self.session_label}")
        return "\n".join(lines)


class SessionListScreen(Container):
    """Session list screen — primary entry point."""

    DEFAULT_CSS = """
    SessionListScreen {
        height: 100%; width: 100%;
        layout: vertical; padding: 1 2;
    }
    #session_list_title { width: 100%; height: auto; }
    #session_search { width: 100%; height: 1; margin-bottom: 1; }
    #sessions_view { width: 100%; height: 1fr; margin-bottom: 1; }
    #session_actions { width: 100%; height: auto; layout: horizontal; }
    Button { margin-right: 1; }
    """

    def __init__(self, on_session_selected: callable, **kwargs):
        super().__init__(**kwargs)
        self.on_session_selected = on_session_selected
        self.sessions = []
        self.filtered_sessions = []

    def compose(self) -> ComposeResult:
        yield Label("PhysioChart Assessment", id="session_list_title")
        yield Input(placeholder="Search patients...", id="session_search")
        yield ScrollableContainer(id="sessions_view")
        yield Button("Quit", id="quit_btn", variant="error")

    def on_mount(self) -> None:
        self.load_sessions()
        self.query_one("#session_search", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "session_search":
            self._on_search_change(event.value)

    def load_sessions(self) -> None:
        self.sessions = list_sessions()
        self.filtered_sessions = self.sessions
        self.refresh_list()

    def _on_search_change(self, value: str) -> None:
        if not value:
            self.filtered_sessions = self.sessions
        else:
            q = value.lower()
            self.filtered_sessions = [
                s for s in self.sessions
                if q in s["patient_id"].lower() or q in s["session_label"].lower()
            ]
        self.refresh_list()

    def refresh_list(self) -> None:
        container = self.query_one("#sessions_view", ScrollableContainer)
        container.remove_children()
        if not self.filtered_sessions:
            container.mount(Label("No sessions found"))
            return

        today = datetime.now().date()
        buckets: dict[str, list] = {"Today": [], "This week": [], "Older": []}
        for session in self.filtered_sessions:
            d = session["date"]
            try:
                dt = (datetime.fromisoformat(d.replace("Z", "+00:00")) if isinstance(d, str)
                      else datetime.fromtimestamp(d)).date()
            except Exception:
                dt = None
            if dt == today:
                buckets["Today"].append(session)
            elif dt and (today - dt).days < 7:
                buckets["This week"].append(session)
            else:
                buckets["Older"].append(session)

        for label_text, group in buckets.items():
            if not group:
                continue
            container.mount(Label(label_text, classes="section_header"))
            for session in group:
                row = SessionListRow(session)
                row.styles.height = "auto"
                container.mount(row)

    def on_session_list_row_selected(self, event: SessionListRow.Selected) -> None:
        self.on_session_selected(event.session_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit_btn":
            self.app.exit()


# ---------------------------------------------------------------------------
# Session header + body chart panel
# ---------------------------------------------------------------------------

class SessionHeader(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.patient_id = ""
        self.session_label = ""
        self.session_file = ""

    def render(self) -> str:
        if not self.session_file:
            return "No active session"
        return f"{self.patient_id} · {self.session_label}"


class BodyChartPanel(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.symptom_types_used = []
        self.views_drawn = []

    def render(self) -> str:
        if not self.symptom_types_used:
            return "No body chart data"
        lines = ["Body Chart:"]
        if self.views_drawn:
            lines.append(f"Views: {', '.join(str(v) for v in self.views_drawn)}")
        if self.symptom_types_used:
            lines.append(f"Symptoms: {', '.join(str(s) for s in self.symptom_types_used)}")
        return "  ".join(lines)


# ---------------------------------------------------------------------------
# Main assessment container
# ---------------------------------------------------------------------------

class _NavChip(Static):
    """Clickable nav chip — plain Static avoids Button's unoverrideable CSS."""

    DEFAULT_CSS = """
    _NavChip {
        width: auto;
        height: 1;
        padding: 0 1;
        background: #2a4060;
        color: white;
    }
    _NavChip:hover {
        background: #4a7090;
    }
    """

    def __init__(self, label, anchor_id: str, section_widget_id: str, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self._anchor_id = anchor_id
        self._section_widget_id = section_widget_id

    def on_click(self) -> None:
        try:
            self.app.query_one(self._section_widget_id)._jump_to(self._anchor_id)
        except Exception:
            pass


class SubsectionNavBar(Static):
    """Context-sensitive subsection jump bar — lives in the top chrome row.

    Hidden by default; shown when a section with sub-navigation is active.
    Call set_context(section_id) when switching sections to swap chips.
    Underlined character in Subjective chips shows the Alt+key shortcut.
    """

    # (before, underlined_key, after, anchor_id)  — Subjective has Alt+key shortcuts
    SUBJECTIVE_SUBS = [
        ("",      "S", "ymptoms",     "subj_symptoms"),
        ("",      "H", "istory",      "subj_history"),
        ("Flare-","U", "ps",          "subj_flareups"),
        ("",      "M", "gmt",         "subj_management"),
        ("",      "A", "ctivity",     "subj_activity"),
        ("",      "W", "ork",         "subj_work"),
        ("sl",    "E", "ep",          "subj_sleep"),
        ("",      "2", "4Hr",         "subj_24hr"),
        ("",      "P", "sychosocial", "subj_psychosocial"),
        ("",      "R", "isk",         "subj_suicide"),
    ]

    MEDICAL_SUBS = [
        ("Comorbid",     "med_comorbidities"),
        ("CVD Risk",     "med_cardiovascular"),
        ("Red Flags",    "med_red_flags"),
        ("Differential", "med_differential"),
        ("Medications",  "med_medications"),
    ]

    PAIN_CLASS_SUBS = [
        ("Inflamm",      "pc_inflammatory"),
        ("Nociceptive",  "pc_nociceptive"),
        ("Neuropathic",  "pc_neuropathic"),
        ("Nociplastic",  "pc_nociplastic"),
        ("Central Sens", "pc_central"),
        ("Summary",      "pc_summary"),
    ]

    OM_SUBS = [
        ("PSFS",       "om_psfs"),
        ("BPI",        "om_bpi"),
        ("DASS",       "om_dass"),
        ("PCS",        "om_pcs"),
        ("PSEQ/PCL",   "om_pseq"),
        ("Sleep",      "om_sleep"),
        ("Additional", "om_additional"),
        ("Hypothesis", "om_hypothesis"),
    ]

    DX_SUBS = [
        ("Overview",    "dx_overview"),
        ("Primary",     "dx_primary"),
        ("Post-Surg",   "dx_surgical"),
        ("Post-Trauma", "dx_traumatic"),
        ("MSK",         "dx_msk"),
        ("Neuro",       "dx_neuropathic"),
        ("Mixed",       "dx_mixed"),
        ("Goals",       "dx_goals"),
    ]

    BR_SUBS = [
        ("Physical",   "br_physical"),
        ("Neuro",      "br_neuro"),
        ("Nocip",      "br_nocip"),
        ("Psych",      "br_psych"),
        ("Sleep/Soc",  "br_sleep"),
        ("Medical",    "br_medical"),
        ("Custom",     "br_custom"),
    ]

    RX_PLAN_SUBS = [
        ("Treatment",  "rp_treatment"),
        ("Session 1",  "rp_session1"),
        ("Day 1",      "rp_day1"),
        ("Follow-Up",  "rp_followup"),
    ]

    DEFAULT_CSS = """
    SubsectionNavBar {
        height: 1;
        width: 1fr;
        layout: horizontal;
        background: #1a2a3a;
        padding: 0;
    }
    """

    def _make_label(self, before: str, key: str, after: str) -> Text:
        t = Text()
        if before:
            t.append(before)
        t.append(key, style="underline bold")
        t.append(after)
        return t

    def compose(self) -> ComposeResult:
        # Intentionally empty — set_context() mounts chips on first navigation.
        # Composing chips here would register their IDs, then set_context's
        # remove_children() + mount() with the same IDs causes a silent collision.
        return
        yield  # make this a generator

    def set_context(self, section_id: str) -> None:
        """Swap chips to match the newly active section."""
        self.remove_children()
        if section_id == "02_subjective":
            for before, key, after, anchor_id in self.SUBJECTIVE_SUBS:
                self.mount(_NavChip(
                    self._make_label(before, key, after),
                    anchor_id=anchor_id,
                    section_widget_id="#section_02_subjective",
                ))
        elif section_id == "03_medical":
            for label, anchor_id in self.MEDICAL_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_03_medical",
                ))
        elif section_id == "04_pain_classification":
            for label, anchor_id in self.PAIN_CLASS_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_04_pain_classification",
                ))
        elif section_id == "05_outcome_measures":
            for label, anchor_id in self.OM_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_05_outcome_measures",
                ))
        elif section_id == "06_diagnosis":
            for label, anchor_id in self.DX_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_06_diagnosis",
                ))
        elif section_id == "07_barriers":
            for label, anchor_id in self.BR_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_07_barriers",
                ))
        elif section_id == "08_rx_plan":
            for label, anchor_id in self.RX_PLAN_SUBS:
                self.mount(_NavChip(
                    label,
                    anchor_id=anchor_id,
                    section_widget_id="#section_08_rx_plan",
                ))


class PhysioAssessmentTUI(Container):
    """Assessment form container — owns the watcher and all keyboard actions."""

    BINDINGS = [
        Binding("ctrl+s", "save",          "Save",       show=True),
        Binding("ctrl+b", "open_bodychart","Body Chart", show=True),
        Binding("ctrl+u", "reload_chart",  "Reload Chart", show=True),
        Binding("ctrl+e", "export",        "Export MD",  show=True),
        Binding("ctrl+r", "export_raw",    "Raw Report", show=True),
        Binding("ctrl+n", "scratchpad",    "Notes",      show=True),
    ]

    DEFAULT_CSS = """
    PhysioAssessmentTUI { height: 100%; width: 100%; layout: vertical; }

    #top_bar {
        height: 1;
        width: 100%;
        background: $boost;
        padding: 0 1;
    }
    #session_header {
        width: 19;
        height: 1;
        color: $text;
        padding: 0 1 0 0;
    }
    #chart_panel {
        width: auto;
        height: 1;
        color: $text-muted;
    }
    #subsection_nav_bar {
        display: none;
    }

    #tui_status {
        height: 1; width: 100%;
        background: $boost; color: $text-muted;
        padding: 0 1;
    }
    AssessmentView { height: 1fr; }
    """

    def __init__(self, session_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self.watcher: BodyChartWatcher | None = None
        self.current_session_file = session_path
        self._status_timer = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="top_bar"):
            yield SessionHeader(id="session_header")
            yield SubsectionNavBar(id="subsection_nav_bar")
            yield BodyChartPanel(id="chart_panel")
        yield AssessmentView(id="assessment_view")
        yield Static("", id="tui_status")

    def on_mount(self) -> None:
        self.watcher = BodyChartWatcher(
            on_session_switch=self.on_session_switch,
            on_chart_update=self.on_chart_update,
            on_focus_request=self._on_focus_request,
        )
        self.watcher.start()

        if self.current_session_file:
            asyncio.create_task(self.load_session_from_path(self.current_session_file))
        else:
            from .storage import load_session_current
            current_data = load_session_current()
            if current_data and current_data.get("session_file"):
                self.current_session_file = current_data["session_file"]
                asyncio.create_task(self.load_session_from_path(self.current_session_file))

    def on_unmount(self) -> None:
        if self.watcher:
            self.watcher.stop()

    # ------------------------------------------------------------------
    # Session loading
    # ------------------------------------------------------------------

    async def load_session_from_path(self, session_file: str) -> None:
        try:
            p = Path(session_file)
            # File may not exist yet if GTK spawned us before its first save.
            # Use empty data so we can still set session_file and accept saves.
            data = json.loads(p.read_text()) if p.exists() else {}

            self.current_session_file = session_file

            header = self.query_one("#session_header", SessionHeader)
            header.patient_id    = data.get("patient_id", "")
            header.session_label = data.get("session_label", "")
            header.session_file  = session_file

            chart_panel = self.query_one("#chart_panel", BodyChartPanel)
            chart_panel.symptom_types_used = []
            chart_panel.views_drawn = []

            assessment_view = self.query_one("#assessment_view", AssessmentView)
            assessment_view.load_session(session_file, data)

            from .storage import write_tui_pid
            write_tui_pid(os.getpid())

        except Exception as e:
            logger.error(f"Failed to load session from {session_file}: {e}")

    async def on_session_switch(self, data: dict) -> None:
        self.current_session_file = data.get("session_file", "")
        header = self.query_one("#session_header", SessionHeader)
        header.patient_id    = data.get("session_id", "")
        header.session_label = data.get("session_label", "")
        header.session_file  = self.current_session_file

        body_chart = data.get("body_chart", {})
        chart_panel = self.query_one("#chart_panel", BodyChartPanel)
        chart_panel.symptom_types_used = body_chart.get("symptom_types_used", [])
        chart_panel.views_drawn        = body_chart.get("views_drawn", [])

        if self.current_session_file:
            try:
                p = Path(self.current_session_file)
                full_data = json.loads(p.read_text()) if p.exists() else {}
            except Exception as e:
                logger.error(f"on_session_switch: failed to read {self.current_session_file}: {e}")
                full_data = {}
            assessment_view = self.query_one("#assessment_view", AssessmentView)
            assessment_view.load_session(self.current_session_file, full_data)
            from .storage import write_tui_pid
            write_tui_pid(os.getpid())

    async def on_chart_update(self, data: dict) -> None:
        # Derive chart panel indicators from raw session JSON strokes (type 5 = tick/clear)
        strokes = data.get("subjective", {}).get("strokes", [])
        seen_types = sorted({s["type"] for s in strokes if "type" in s and s["type"] != 5})

        chart_panel = self.query_one("#chart_panel", BodyChartPanel)
        chart_panel.symptom_types_used = seen_types
        chart_panel.views_drawn        = sorted({s["view"] for s in strokes if "view" in s})
        chart_panel.refresh()

        # Refresh subjective note slots from updated body chart
        try:
            av = self.query_one("#assessment_view", AssessmentView)
            subj = av.sections.get("02_subjective")
            if subj is not None:
                subj.refresh_from_chart(data)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Focus signal — GTK wrote .focus_tui, raise our kitty window
    # ------------------------------------------------------------------

    async def _on_focus_request(self) -> None:
        _focus_tui_window()

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _show_status(self, message: str, seconds: float = 2.5) -> None:
        try:
            self.query_one("#tui_status", Static).update(message)
            if self._status_timer:
                self._status_timer.cancel()
            self._status_timer = self.set_timer(seconds, self._clear_status)
        except Exception:
            pass

    def _clear_status(self) -> None:
        try:
            self.query_one("#tui_status", Static).update("")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    async def save_if_pending(self) -> None:
        """Flush pending debounced save before navigating away. Only saves if a save is queued."""
        assessment_view = self.query_one("#assessment_view", AssessmentView)
        task = assessment_view._save_task
        if task and not task.done():
            task.cancel()
            await assessment_view._do_save()

    def action_save(self) -> None:
        assessment_view = self.query_one("#assessment_view", AssessmentView)

        async def _save_and_notify():
            await assessment_view._do_save()
            self._show_status("Saved")

        asyncio.create_task(_save_and_notify())

    def action_open_bodychart(self) -> None:
        """Ctrl+B — focus GTK body chart (or launch it if not running)."""
        if not self.current_session_file:
            self._show_status("No session loaded")
            return

        gtk_pid = read_gtk_pid()
        if _process_alive(gtk_pid):
            # GTK is running — send signal file; GTK will call gtk_window_present()
            write_focus_signal(self.current_session_file, "gtk")
            self._show_status("Switching to Body Chart…")
        else:
            # GTK not running — launch it
            try:
                subprocess.Popen(
                    ["physio-bodychart", "--session", self.current_session_file],
                    close_fds=True,
                )
                self._show_status("Launching Body Chart…")
            except Exception as e:
                self._show_status(f"Launch failed: {e}")
                logger.error(f"Failed to launch body chart: {e}")

    def action_reload_chart(self) -> None:
        """Ctrl+U — force-reload body chart data from _session.json and refresh note slots."""
        if not self.current_session_file:
            self._show_status("No session loaded")
            return
        try:
            p = Path(self.current_session_file)
            if not p.exists():
                self._show_status("Session file not found")
                return
            data = json.loads(p.read_text())
            av = self.query_one("#assessment_view", AssessmentView)
            subj = av.sections.get("02_subjective")
            if subj is not None:
                subj.refresh_from_chart(data)
            self._show_status("Body chart reloaded")
        except Exception as e:
            self._show_status(f"Reload failed: {e}")

    def action_export(self) -> None:
        """Ctrl+E — export session report to Markdown."""
        if not self.current_session_file:
            self._show_status("No session loaded")
            return
        out = export_session_report(self.current_session_file)
        if out:
            name = Path(out).name
            self._show_status(f"Exported → {name}", seconds=4.0)
        else:
            self._show_status("Export failed — check logs")

    def action_export_raw(self) -> None:
        """Ctrl+R — flush active section and regenerate raw report in session folder."""
        if not self.current_session_file:
            self._show_status("No session loaded")
            return

        async def _save_then_notify():
            assessment_view = self.query_one("#assessment_view", AssessmentView)
            await assessment_view._do_save()
            out = save_raw_report(self.current_session_file)
            if out:
                self._show_status(f"Raw report → {Path(out).name}", seconds=4.0)
            else:
                self._show_status("Raw report write failed — check logs")

        asyncio.create_task(_save_then_notify())

    def action_scratchpad(self) -> None:
        """Ctrl+N — jump to the scratchpad section."""
        if not self.current_session_file:
            self._show_status("No session loaded")
            return
        assessment_view = self.query_one("#assessment_view", AssessmentView)
        assessment_view._show_section("scratchpad")

    # ------------------------------------------------------------------
    # Arrow-key scroll fallback — only when no widget is focused
    # ------------------------------------------------------------------

    def on_key(self, event) -> None:
        """Scroll section_content with arrow keys when nothing is focused.

        Field-to-field navigation is handled in BaseSection.on_key, which fires
        earlier in the bubble chain (before ScrollableContainer).  This handler
        only acts when app.focused is None so unfocused arrow presses still scroll.
        """
        if event.key not in ("up", "down"):
            return
        if self.app.focused is not None:
            return
        try:
            sc = self.query_one("#section_content", ScrollableContainer)
            if event.key == "up":
                sc.scroll_up(animate=False)
            else:
                sc.scroll_down(animate=False)
            event.stop()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Save state indicator
    # ------------------------------------------------------------------

    def on_assessment_view_save_state_changed(
        self, event: AssessmentView.SaveStateChanged
    ) -> None:
        """Update status bar to reflect auto-save state."""
        if event.state == "pending":
            try:
                self.query_one("#tui_status", Static).update("Unsaved changes")
                if self._status_timer:
                    self._status_timer.cancel()
                    self._status_timer = None
            except Exception:
                pass
        elif event.state == "saving":
            try:
                self.query_one("#tui_status", Static).update("Saving…")
                if self._status_timer:
                    self._status_timer.cancel()
                    self._status_timer = None
            except Exception:
                pass
        elif event.state == "saved":
            now = datetime.now().strftime("%H:%M")
            self._show_status(f"Saved {now}", seconds=8.0)
