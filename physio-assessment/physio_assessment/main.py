"""Textual TUI main entry point."""

from textual.app import ComposeResult, App
from textual.widgets import Header, Footer
from .tui import PhysioAssessmentTUI


class PhysioAssessment(App):
    """Main Textual application for PhysioChart assessment system."""

    TITLE = "PhysioChart Assessment System"
    SUB_TITLE = "Specialist Physiotherapy Assessment & Report Generator"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield PhysioAssessmentTUI()
        yield Footer()


def main():
    """Entry point."""
    app = PhysioAssessment()
    app.run()


if __name__ == "__main__":
    main()
