"""Search modal for the ctrl+f / click jump-search feature.

Uses ModalScreen so it floats over the existing content without any
layer/offset tricks. Pre-mounts 10 result rows so there is no
remove_children()+mount() cycle on every keystroke.
"""
from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from .search import SearchEntry, filter_entries


class SearchResultRow(Static):
    """One result row — hidden until a result is assigned."""

    DEFAULT_CSS = """
    SearchResultRow {
        width: 100%;
        height: 1;
        padding: 0 1;
        color: $text;
        display: none;
    }
    SearchResultRow.--selected {
        height: 3;
        border: solid $accent;
        color: $accent;
        background: transparent;
        padding: 0 1;
    }
    SearchResultRow:hover {
        color: $text;
        background: $surface;
    }
    SearchResultRow.--selected:hover {
        border: solid $accent;
        color: $accent;
        background: transparent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)
        self._entry: SearchEntry | None = None

    def on_click(self) -> None:
        if self._entry is not None:
            self.screen.dismiss(self._entry)


class SearchModal(ModalScreen):
    """Transparent overlay search. Appears top-right, dismissed on Enter/Escape."""

    DEFAULT_CSS = """
    SearchModal {
        background: transparent;
        align: center middle;
    }
    #modal_box {
        width: 55;
        height: auto;
        max-height: 22;
        background: $boost;
        border: solid $primary;
    }
    #modal_input {
        width: 100%;
        height: 1;
        padding: 0 1;
        background: $accent 30%;
        border: none;
        color: $text;
    }
    #modal_input:focus {
        border: none;
        background: $accent 45%;
    }
    """

    def __init__(self, index: list[SearchEntry], **kwargs) -> None:
        super().__init__(**kwargs)
        self._index = index
        self._entries: list[SearchEntry] = []
        self._selected_idx: int = -1

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Input(placeholder="⌕ type to search…", id="modal_input")
            for _ in range(10):
                yield SearchResultRow()

    def on_mount(self) -> None:
        self.query_one("#modal_input", Input).focus()

    # ------------------------------------------------------------------
    # Input handler
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value
        results = filter_entries(query, self._index) if query.strip() else []
        self._update_results(results)

    def _update_results(self, entries: list[SearchEntry]) -> None:
        self._entries = entries
        self._selected_idx = 0 if entries else -1
        rows = list(self.query(SearchResultRow))
        for i, row in enumerate(rows):
            if i < len(entries):
                row._entry = entries[i]
                row.update(entries[i].display)
                row.display = True
                row.set_class(i == 0, "--selected")
            else:
                row._entry = None
                row.update("")
                row.display = False

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        if event.key == "down":
            if self._selected_idx < len(self._entries) - 1:
                self._move_selection(self._selected_idx + 1)
            event.stop()
        elif event.key == "up":
            if self._selected_idx > 0:
                self._move_selection(self._selected_idx - 1)
            event.stop()
        elif event.key == "enter":
            if 0 <= self._selected_idx < len(self._entries):
                self.dismiss(self._entries[self._selected_idx])
            event.stop()
        elif event.key == "escape":
            self.dismiss(None)
            event.stop()

    def _move_selection(self, idx: int) -> None:
        rows = list(self.query(SearchResultRow))
        if 0 <= self._selected_idx < len(rows):
            rows[self._selected_idx].remove_class("--selected")
        self._selected_idx = idx
        if 0 <= idx < len(rows):
            rows[idx].add_class("--selected")
