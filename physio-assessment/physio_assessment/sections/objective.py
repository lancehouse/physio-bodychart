"""Objective section stub — navigation is handled by sidebar swap in AssessmentView."""

from textual.app import ComposeResult
from textual.widgets import Label, Static

from .base import BaseSection


class ObjectiveSection(BaseSection):
    """Unused stub — kept for backward compatibility."""

    DEFAULT_CSS = """
    ObjectiveSection { height: auto; padding: 1 2; }
    """

    def compose(self) -> ComposeResult:
        yield Label("Objective Examination", classes="section-heading")
        yield Static("Use '04 Objective →' in the sidebar.", classes="coming-soon")

    def load(self, data: dict) -> None:
        pass

    def collect(self) -> dict:
        return {}

    def is_complete(self) -> bool:
        return False
