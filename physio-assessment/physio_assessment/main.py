"""Textual TUI main entry point."""

import asyncio
from pathlib import Path
from textual.app import ComposeResult, App
from textual.widgets import Header, Footer
from textual.containers import Container
from .tui import PhysioAssessmentTUI, SessionListScreen
from .storage import load_assessment, load_session_current


class PhysioAssessment(App):
    """Main Textual application for PhysioChart assessment system."""

    TITLE = "PhysioChart Assessment System"
    SUB_TITLE = "Specialist Physiotherapy Assessment & Report Generator"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "show_session_list", "Sessions"),
    ]

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_session_path = ""
        self.assessment_screen = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        # Create the main container
        main = Container()
        yield main

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app - check for existing session or show list."""
        # Try loading current session from file
        current_data = load_session_current()
        if current_data and current_data.get("session_file"):
            # Show assessment form for current session
            self.current_session_path = current_data["session_file"]
            asyncio.create_task(self.show_assessment_form())
        else:
            # Show session list
            self.show_session_list()

    def show_session_list(self) -> None:
        """Show the session list screen."""
        main = self.query_one(Container)
        main.remove_children()
        session_list = SessionListScreen(on_session_selected=self.on_session_selected)
        main.mount(session_list)

    async def on_session_selected(self, session_path: str) -> None:
        """Handle session selection from list."""
        self.current_session_path = session_path
        await self.show_assessment_form()

    async def show_assessment_form(self) -> None:
        """Show the assessment form for current session."""
        main = self.query_one(Container)
        main.remove_children()

        assessment = PhysioAssessmentTUI(session_path=self.current_session_path)
        self.assessment_screen = assessment
        main.mount(assessment)

    def on_session_list_screen_new_session_requested(self) -> None:
        """Handle new session request from session list."""
        # For now, just show the session list again to reload
        self.show_session_list()

    def action_show_session_list(self) -> None:
        """Return to session list (Ctrl+L)."""
        self.show_session_list()


def main():
    """Entry point."""
    app = PhysioAssessment()
    app.run()


if __name__ == "__main__":
    main()
