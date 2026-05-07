"""
Physiotherapy Assessment TUI using Textual framework.

Integrates with GTK body chart via session JSON file watcher.
Allows editing of assessment narrative while monitoring chart updates.
"""

import asyncio
import json
import logging
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Input, TextArea
from textual.binding import Binding

from watcher import BodyChartWatcher
from storage import load_assessment, save_assessment


logger = logging.getLogger(__name__)


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
    """Main TUI container for physiotherapy assessment."""

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.watcher: BodyChartWatcher | None = None
        self.current_session_file = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield SessionHeader(id="session_header")
        yield BodyChartPanel(id="chart_panel")
        yield AssessmentForm(id="assessment_form")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize watcher and load current session if available."""
        # Create and start watcher
        self.watcher = BodyChartWatcher(self.on_session_switch, self.on_chart_update)
        self.watcher.start()

        # Try to load current session on startup
        from storage import load_session_current
        current_data = load_session_current()
        if current_data:
            asyncio.create_task(self.on_session_switch(current_data))

    def on_unmount(self) -> None:
        """Clean up watcher on exit."""
        if self.watcher:
            self.watcher.stop()

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
