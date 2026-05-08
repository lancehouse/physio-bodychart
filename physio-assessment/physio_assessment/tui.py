"""
Physiotherapy Assessment TUI using Textual framework.

Integrates with GTK body chart via session JSON file watcher.
Allows editing of assessment narrative while monitoring chart updates.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Label, Input, TextArea, Button, ListItem, ListView
from textual.binding import Binding

from .watcher import BodyChartWatcher
from .storage import load_assessment, save_assessment, list_sessions, create_new_session


logger = logging.getLogger(__name__)


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
        # Format date
        if isinstance(self.date, str):
            try:
                dt = datetime.fromisoformat(self.date.replace("Z", "+00:00"))
                date_str = dt.strftime("%d %b %H:%M")
            except:
                date_str = self.date[:10] if self.date else ""
        else:
            date_str = datetime.fromtimestamp(self.date).strftime("%d %b %H:%M")

        # Status indicator
        body_chart_indicator = "●" if self.body_chart_data else "○"

        # Build row text
        top_line = f"{self.patient_id}   {date_str}   {body_chart_indicator}   {self.sections_complete}/7"
        lines = [top_line]

        if self.session_label:
            lines.append(f"  {self.session_label}")

        return "\n".join(lines)


class SessionListScreen(Container):
    """Session list screen - primary entry point."""

    DEFAULT_CSS = """
    SessionListScreen {
        height: 100%;
        width: 100%;
        layout: vertical;
        padding: 1 2;
    }

    #session_list_title {
        width: 100%;
        height: auto;
    }

    #session_search {
        width: 100%;
        height: 1;
        margin-bottom: 1;
    }

    #sessions_view {
        width: 100%;
        height: 1fr;
        margin-bottom: 1;
    }

    #session_actions {
        width: 100%;
        height: auto;
        layout: horizontal;
    }

    Button {
        margin-right: 1;
    }
    """

    def __init__(self, on_session_selected: callable, **kwargs):
        super().__init__(**kwargs)
        self.on_session_selected = on_session_selected
        self.sessions = []
        self.filtered_sessions = []

    def compose(self) -> ComposeResult:
        yield Label("PhysioChart Assessment", id="session_list_title")
        yield Input(placeholder="Search patients...", id="session_search")

        # Sessions list
        sessions_container = ScrollableContainer(id="sessions_view")
        yield sessions_container

        # Action buttons
        action_box = Horizontal(id="session_actions")
        action_box.border_title = "Actions"
        yield Button("+ New Session", id="new_session_btn", variant="primary")
        yield Button("Quit", id="quit_btn", variant="error")

    def on_mount(self) -> None:
        """Load and display sessions on startup."""
        self.load_sessions()
        self.query_one("#session_search", Input).focus()

        # Connect input change to filtering
        self.query_one("#session_search").watch("value", self._on_search_change)

    def load_sessions(self) -> None:
        """Load sessions from storage and populate list."""
        self.sessions = list_sessions()
        self.refresh_list()

    def _on_search_change(self, value: str) -> None:
        """Filter sessions as user types."""
        if not value:
            self.filtered_sessions = self.sessions
        else:
            search_lower = value.lower()
            self.filtered_sessions = [
                s for s in self.sessions
                if search_lower in s["patient_id"].lower() or
                   search_lower in s["session_label"].lower()
            ]
        self.refresh_list()

    def refresh_list(self) -> None:
        """Refresh the displayed session list."""
        container = self.query_one("#sessions_view", ScrollableContainer)
        container.remove_children()

        if not self.filtered_sessions:
            container.mount(Label("No sessions found"))
            return

        # Group by date (today, this week, older)
        today = datetime.now().date()
        today_sessions = []
        week_sessions = []
        older_sessions = []

        for session in self.filtered_sessions:
            if isinstance(session["date"], str):
                try:
                    dt = datetime.fromisoformat(session["date"].replace("Z", "+00:00")).date()
                except:
                    dt = None
            else:
                dt = datetime.fromtimestamp(session["date"]).date()

            if dt and dt == today:
                today_sessions.append(session)
            elif dt and (today - dt).days < 7:
                week_sessions.append(session)
            else:
                older_sessions.append(session)

        # Display grouped sessions
        if today_sessions:
            container.mount(Label("Today", classes="section_header"))
            for session in today_sessions:
                row = SessionListRow(session)
                row.styles.border = ("solid", "blue")
                row.styles.height = "auto"
                container.mount(row)
                row.on_click = lambda: self.on_session_selected(session["path"])

        if week_sessions:
            container.mount(Label("This week", classes="section_header"))
            for session in week_sessions:
                row = SessionListRow(session)
                row.styles.height = "auto"
                container.mount(row)
                row.on_click = lambda: self.on_session_selected(session["path"])

        if older_sessions:
            container.mount(Label("Older", classes="section_header"))
            for session in older_sessions:
                row = SessionListRow(session)
                row.styles.height = "auto"
                container.mount(row)
                row.on_click = lambda: self.on_session_selected(session["path"])

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        if button_id == "new_session_btn":
            self.post_message(self.NewSessionRequested())
        elif button_id == "quit_btn":
            self.app.exit()

    class NewSessionRequested:
        """Message indicating user wants to create new session."""
        pass


class SessionHeader(Static):
    """Display current session info."""

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
    """Display body chart summary (symptoms, views drawn)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.symptom_types_used = []
        self.views_drawn = []

    def render(self) -> str:
        if not self.symptom_types_used:
            return "No body chart data"

        lines = ["Body Chart Summary:"]
        if self.views_drawn:
            lines.append(f"Views: {', '.join(str(v) for v in self.views_drawn)}")
        if self.symptom_types_used:
            lines.append(f"Symptoms: {', '.join(str(s) for s in self.symptom_types_used)}")

        return "\n".join(lines)


class AssessmentForm(Container):
    """Form for editing assessment narrative fields."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_file = ""
        self._save_task: asyncio.Task | None = None

    def compose(self) -> ComposeResult:
        yield Label("Clinical History:")
        yield TextArea(id="history", language="markdown")
        yield Label("Aggravating Factors:")
        yield Input(id="agg_factors", placeholder="What makes it worse?")
        yield Label("Easing Factors:")
        yield Input(id="ease_factors", placeholder="What helps?")
        yield Label("24-Hour Pattern:")
        yield Input(id="behaviour_24hr", placeholder="How does it change throughout the day?")
        yield Label("Diagnosis:")
        yield TextArea(id="diagnosis", language="markdown")
        yield Label("Plan:")
        yield TextArea(id="plan", language="markdown")
        yield Label("Clinical Notes:")
        yield TextArea(id="clinical_notes", language="markdown")

    def load_assessment(self, assessment: dict):
        """Load assessment data into form fields."""
        if history := assessment.get("history"):
            self.query_one("#history", TextArea).text = history
        if agg := assessment.get("agg_factors"):
            self.query_one("#agg_factors", Input).value = agg
        if ease := assessment.get("ease_factors"):
            self.query_one("#ease_factors", Input).value = ease
        if behav := assessment.get("behaviour_24hr"):
            self.query_one("#behaviour_24hr", Input).value = behav
        if diag := assessment.get("diagnosis"):
            self.query_one("#diagnosis", TextArea).text = diag
        if plan := assessment.get("plan"):
            self.query_one("#plan", TextArea).text = plan
        if notes := assessment.get("clinical_notes"):
            self.query_one("#clinical_notes", TextArea).text = notes

    async def save_current_assessment(self):
        """Collect form data and save to session JSON (debounced)."""
        if not self.session_file:
            return

        assessment = {
            "history": self.query_one("#history", TextArea).text,
            "agg_factors": self.query_one("#agg_factors", Input).value,
            "ease_factors": self.query_one("#ease_factors", Input).value,
            "behaviour_24hr": self.query_one("#behaviour_24hr", Input).value,
            "diagnosis": self.query_one("#diagnosis", TextArea).text,
            "plan": self.query_one("#plan", TextArea).text,
            "clinical_notes": self.query_one("#clinical_notes", TextArea).text,
        }

        save_assessment(self.session_file, assessment)

    def _schedule_save(self):
        """Schedule a debounced save after 2 seconds of inactivity."""
        if self._save_task:
            self._save_task.cancel()

        async def delayed_save():
            await asyncio.sleep(2.0)
            await self.save_current_assessment()

        self._save_task = asyncio.create_task(delayed_save())

    @on(Input.Changed)
    @on(TextArea.Changed)
    def _on_field_changed(self):
        """Save assessment when any field changes (debounced)."""
        self._schedule_save()


class PhysioAssessmentTUI(Container):
    """Assessment form container for physiotherapy assessment."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+b", "open_bodychart", "Body Chart", show=True),
    ]

    def __init__(self, session_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self.watcher: BodyChartWatcher | None = None
        self.current_session_file = session_path

    def compose(self) -> ComposeResult:
        yield SessionHeader(id="session_header")
        yield BodyChartPanel(id="chart_panel")
        yield AssessmentForm(id="assessment_form")

    def on_mount(self) -> None:
        """Initialize watcher and load session."""
        # Create and start watcher
        self.watcher = BodyChartWatcher(self.on_session_switch, self.on_chart_update)
        self.watcher.start()

        # Load the specified session or current session
        if self.current_session_file:
            # Load from provided path
            asyncio.create_task(self.load_session_from_path(self.current_session_file))
        else:
            # Try to load current session from file
            from .storage import load_session_current
            current_data = load_session_current()
            if current_data:
                asyncio.create_task(self.on_session_switch(current_data))

    def on_unmount(self) -> None:
        """Clean up watcher on exit."""
        if self.watcher:
            self.watcher.stop()

    async def load_session_from_path(self, session_file: str) -> None:
        """Load session data from a file path."""
        try:
            data = json.loads(Path(session_file).read_text())
            self.current_session_file = session_file

            # Update header
            header = self.query_one("#session_header", SessionHeader)
            header.patient_id = data.get("patient_id", "")
            header.session_label = data.get("session_label", "")
            header.session_file = session_file

            # Update chart panel
            subjective = data.get("subjective", {})
            chart_panel = self.query_one("#chart_panel", BodyChartPanel)
            chart_panel.symptom_types_used = []  # Not tracked in new schema
            chart_panel.views_drawn = []  # Not tracked in new schema

            # Load assessment data into form
            assessment = data.get("assessment", {})
            form = self.query_one("#assessment_form", AssessmentForm)
            form.session_file = session_file
            form.load_assessment(assessment)
        except Exception as e:
            logger.error(f"Failed to load session from {session_file}: {e}")

    async def on_session_switch(self, data: dict) -> None:
        """Handle active session change from GTK."""
        self.current_session_file = data.get("session_file", "")

        # Update header
        header = self.query_one("#session_header", SessionHeader)
        header.patient_id = data.get("session_id", "")
        header.session_label = data.get("session_label", "")
        header.session_file = self.current_session_file

        # Update chart panel
        body_chart = data.get("body_chart", {})
        chart_panel = self.query_one("#chart_panel", BodyChartPanel)
        chart_panel.symptom_types_used = body_chart.get("symptom_types_used", [])
        chart_panel.views_drawn = body_chart.get("views_drawn", [])

        # Load assessment data into form
        if self.current_session_file:
            assessment = load_assessment(self.current_session_file)
            form = self.query_one("#assessment_form", AssessmentForm)
            form.session_file = self.current_session_file
            form.load_assessment(assessment)

    async def on_chart_update(self, data: dict) -> None:
        """Handle GTK chart update (don't overwrite user edits)."""
        # Update body chart panel with new symptom/view info
        body_chart = data.get("body_chart", {})
        chart_panel = self.query_one("#chart_panel", BodyChartPanel)
        chart_panel.symptom_types_used = body_chart.get("symptom_types_used", [])
        chart_panel.views_drawn = body_chart.get("views_drawn", [])

    def action_save(self) -> None:
        """Manual save action."""
        form = self.query_one("#assessment_form", AssessmentForm)
        asyncio.create_task(form.save_current_assessment())

    def action_open_bodychart(self) -> None:
        """Launch GTK body chart (Ctrl+B)."""
        if not self.current_session_file:
            logger.warning("No session loaded; cannot open body chart")
            return

        import subprocess
        from .logic import get_bodychart_command

        # Update session to mark body chart as requested
        try:
            path = Path(self.current_session_file)
            data = json.loads(path.read_text())
            data["body_chart_requested"] = True
            data["launched_by"] = "tui"
            data["workflow_stage"] = data.get("workflow_stage", "02_subjective")
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(path)
        except Exception as e:
            logger.warning(f"Failed to update session JSON: {e}")

        # Launch GTK
        cmd = get_bodychart_command(Path(self.current_session_file))
        try:
            subprocess.Popen(cmd)
            logger.info(f"Launched body chart for {self.current_session_file}")
        except Exception as e:
            logger.error(f"Failed to launch body chart: {e}")
