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

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
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

    def __init__(self, session: dict, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.patient_id = session["patient_id"]
        self.session_label = session["session_label"]
        self.session_path = session["path"]
        self.sections_complete = session["sections_complete"]
        self.body_chart_data = session["body_chart_data"]
        self.date = session["date"]

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
        top_line = f"{self.patient_id}   {date_str}   {body_chart_indicator}   {self.sections_complete}/7"
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
        yield Button("+ New Session", id="new_session_btn", variant="primary")
        yield Button("Quit", id="quit_btn", variant="error")

    def on_mount(self) -> None:
        self.load_sessions()
        self.query_one("#session_search", Input).focus()
        self.query_one("#session_search").watch("value", self._on_search_change)

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
                row.on_click = lambda p=session["path"]: self.on_session_selected(p)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new_session_btn":
            self.post_message(self.NewSessionRequested())
        elif event.button.id == "quit_btn":
            self.app.exit()

    class NewSessionRequested:
        pass


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

class PhysioAssessmentTUI(Container):
    """Assessment form container — owns the watcher and all keyboard actions."""

    BINDINGS = [
        Binding("ctrl+s", "save",          "Save",       show=True),
        Binding("ctrl+b", "open_bodychart","Body Chart", show=True),
        Binding("ctrl+e", "export",        "Export MD",  show=True),
        Binding("ctrl+r", "export_raw",    "Raw Report", show=True),
        Binding("ctrl+n", "scratchpad",    "Notes",      show=True),
    ]

    DEFAULT_CSS = """
    PhysioAssessmentTUI { height: 100%; width: 100%; layout: vertical; }
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
        yield SessionHeader(id="session_header")
        yield BodyChartPanel(id="chart_panel")
        yield AssessmentView(id="assessment_view")
        yield Static("", id="tui_status")  # sits naturally at bottom of vertical layout

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
            full_data = json.loads(Path(self.current_session_file).read_text())
            assessment_view = self.query_one("#assessment_view", AssessmentView)
            assessment_view.load_session(self.current_session_file, full_data)
            from .storage import write_tui_pid
            write_tui_pid(os.getpid())

    async def on_chart_update(self, data: dict) -> None:
        body_chart = data.get("body_chart", {})
        chart_panel = self.query_one("#chart_panel", BodyChartPanel)
        chart_panel.symptom_types_used = body_chart.get("symptom_types_used", [])
        chart_panel.views_drawn        = body_chart.get("views_drawn", [])

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
