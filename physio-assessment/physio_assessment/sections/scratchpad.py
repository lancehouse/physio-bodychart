"""Scratchpad section — freeform notes, differential diagnoses, reminders."""

import logging

from textual.app import ComposeResult, on
from textual.widgets import TextArea
from textual.message import Message

from .base import BaseSection

logger = logging.getLogger(__name__)


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
        height: auto;
        padding: 0;
    }

    #scratchpad_text {
        width: 100%;
        height: auto;
        min-height: 40;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Holds notes that couldn't be applied yet (section hidden on load).
        # collect() returns this as a fallback so saves from other sections
        # don't overwrite good data with an empty TextArea.
        self._pending_notes: str | None = None

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
        """Load scratchpad notes, deferring to on_show if the section is hidden."""
        notes = data.get("notes", "") if isinstance(data, dict) else ""
        self._pending_notes = notes
        self._loading = True
        try:
            self.query_one("#scratchpad_text", TextArea).text = notes
            self._pending_notes = None  # applied successfully
        except Exception as e:
            logger.debug(f"Scratchpad load deferred (will apply on show): {e}")
        finally:
            self._loading = False

    def on_show(self) -> None:
        """Apply any notes that couldn't be set while the section was hidden."""
        if self._pending_notes is None:
            return
        self._loading = True
        try:
            self.query_one("#scratchpad_text", TextArea).text = self._pending_notes
            self._pending_notes = None
        except Exception as e:
            logger.error(f"Scratchpad on_show load failed: {e}")
        finally:
            self._loading = False

    def collect(self) -> dict:
        """Return current notes. Falls back to _pending_notes so saves from
        other sections never overwrite good data with an empty TextArea."""
        try:
            text = self.query_one("#scratchpad_text", TextArea).text
            # If the TextArea is empty but we have pending notes, the TextArea
            # hasn't been populated yet — return pending to protect saved data.
            if not text and self._pending_notes:
                return {"notes": self._pending_notes}
            return {"notes": text}
        except Exception:
            return {"notes": self._pending_notes or ""}

    def is_complete(self) -> bool:
        return False  # never contributes to completion counter

    @on(TextArea.Changed)
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._pending_notes = None  # TextArea is now the source of truth
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
