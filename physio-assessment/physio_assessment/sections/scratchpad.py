"""Scratchpad section — freeform notes, differential diagnoses, reminders."""

from textual.app import ComposeResult, on
from textual.widgets import TextArea
from textual.message import Message

from .base import BaseSection


class ScratchpadSection(BaseSection):
    """Freeform text area for clinical notes, differentials, reminders.

    No structured fields, no completion tracking.
    Saved under assessment.scratchpad.notes in the session JSON.
    """

    SECTION_ID = "scratchpad"
    SECTION_TITLE = "📝 Scratchpad"

    DEFAULT_CSS = """
    ScratchpadSection {
        width: 100%;
        height: 100%;
        padding: 0;
    }

    #scratchpad_text {
        width: 100%;
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield TextArea(
            "",
            id="scratchpad_text",
            language="plain",
            soft_wrap=True,
        )

    def on_mount(self) -> None:
        ta = self.query_one("#scratchpad_text", TextArea)
        ta.show_line_numbers = False

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            notes = data.get("notes", "") if isinstance(data, dict) else ""
            self.query_one("#scratchpad_text", TextArea).text = notes
        except Exception:
            pass
        finally:
            self._loading = False

    def collect(self) -> dict:
        try:
            return {"notes": self.query_one("#scratchpad_text", TextArea).text}
        except Exception:
            return {"notes": ""}

    def is_complete(self) -> bool:
        return False  # never contributes to completion counter

    @on(TextArea.Changed)
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
