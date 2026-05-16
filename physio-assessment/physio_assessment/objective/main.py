"""Objective Examination TUI — standalone Textual app."""

import os
import sys
import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer

from ..storage import (
    load_session_current,
    write_objective_pid,
    write_focus_signal,
    load_objective,
)
from ..watcher import BodyChartWatcher
from .objective_view import ObjectiveAssessmentView


class PhysioObjective(App):
    """Standalone Objective Examination TUI."""

    TITLE = "PhysioChart Objective"
    SUB_TITLE = "Objective Examination"
    ANIMATION_SPEED = 2.0

    BINDINGS = [
        ("ctrl+q", "quit",               "Quit"),
        ("ctrl+b", "focus_bodychart",    "Body Chart"),
        ("ctrl+s", "manual_save",        "Save"),
        Binding("f1", "section_1", show=False, priority=True),
        Binding("f2", "section_2", show=False, priority=True),
        Binding("f3", "section_3", show=False, priority=True),
        Binding("f4", "section_4", show=False, priority=True),
        Binding("f5", "section_5", show=False, priority=True),
        Binding("f6", "section_6", show=False, priority=True),
        Binding("f7", "section_7", show=False, priority=True),
    ]

    CSS = """
    Screen { background: $surface; }
    """

    def __init__(self, session_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self.current_session_path = session_path
        self._objective_view: ObjectiveAssessmentView | None = None
        self._watcher: BodyChartWatcher | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(id="main_content")
        yield Footer()

    def on_mount(self) -> None:
        write_objective_pid(os.getpid())

        if not self.current_session_path:
            current = load_session_current()
            if current and current.get("session_file"):
                self.current_session_path = current["session_file"]

        if self.current_session_path:
            asyncio.create_task(self._load_session())

        self._watcher = BodyChartWatcher(
            on_session_switch=self._on_session_switch,
            on_chart_update=self._on_chart_update,
            on_focus_request=self._on_focus_request,
            focus_signal=".focus_objective",
        )
        self._watcher.start()

    def on_unmount(self) -> None:
        if self._watcher:
            self._watcher.stop()

    async def _load_session(self) -> None:
        main = self.query_one("#main_content", Container)
        main.remove_children()
        ov = ObjectiveAssessmentView(session_file=self.current_session_path)
        self._objective_view = ov
        await main.mount(ov)
        data = load_objective(self.current_session_path)
        ov.load_session(self.current_session_path, data)

    async def _on_session_switch(self, data: dict) -> None:
        session_file = data.get("session_file", "")
        if session_file and session_file != self.current_session_path:
            self.current_session_path = session_file
            await self._load_session()

    async def _on_chart_update(self, data: dict) -> None:
        pass

    async def _on_focus_request(self) -> None:
        self.refresh()

    def _goto_section(self, section_id: str) -> None:
        if self._objective_view is None:
            return
        try:
            self._objective_view._show_section(section_id)
            section = self._objective_view.sections.get(section_id)
            if section:
                section.focus_first_field()
        except Exception:
            pass

    def action_section_1(self): self._goto_section("01_general")
    def action_section_2(self): self._goto_section("02_active")
    def action_section_3(self): self._goto_section("03_passive")
    def action_section_4(self): self._goto_section("04_neurological")
    def action_section_5(self): self._goto_section("05_sensory")
    def action_section_6(self): self._goto_section("06_muscle")
    def action_section_7(self): self._goto_section("07_functional")

    def action_focus_bodychart(self) -> None:
        if self.current_session_path:
            write_focus_signal(self.current_session_path, "gtk")

    async def action_manual_save(self) -> None:
        if self._objective_view:
            await self._objective_view._do_save()


def main():
    """Entry point — accepts optional --session <path> argument."""
    session_path = ""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--session" and i + 1 < len(args):
            session_path = args[i + 1]
            break

    app = PhysioObjective(session_path=session_path)
    app.run()


if __name__ == "__main__":
    main()
