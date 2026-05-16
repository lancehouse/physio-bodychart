"""Objective TUI: sidebar navigation + section content area."""

import asyncio
import logging

from textual.app import ComposeResult, on
from textual.containers import Container, Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Button, Static

from .sections.general import GeneralSection
from .sections.active_movement import ActiveMovementSection
from .sections.passive_movement import PassiveMovementSection
from .sections.neurological import NeurologicalSection
from .sections.sensory import SensorySection
from .sections.muscle import MuscleSection
from .sections.functional import FunctionalSection
from ..storage import objective_path, save_objective, write_focus_signal, save_raw_report, export_session_report


logger = logging.getLogger(__name__)


class ObjectiveSidebar(Static):
    """Left sidebar navigation for Objective TUI."""

    DEFAULT_CSS = """
    ObjectiveSidebar {
        width: 22;
        height: 100%;
        border-right: solid $border;
        background: $panel;
        layout: vertical;
        padding: 1 0;
    }
    ObjectiveSidebar Button {
        width: 100%;
        height: auto;
        border: none;
        background: $panel;
        margin: 0;
        padding: 0 1;
    }
    ObjectiveSidebar Button:hover { background: $boost; }
    ObjectiveSidebar Button.active { background: $accent; text-style: bold; }
    ObjectiveSidebar .back {
        background: $panel-darken-1;
        color: $text-muted;
        margin-top: 1;
    }
    ObjectiveSidebar .back:hover { background: $boost; color: $text; }
    """

    SECTION_LABELS = {
        "01_general":      "01 General Obs",
        "02_active":       "02 Active Mvmt",
        "03_passive":      "03 Passive/OP",
        "04_neurological": "04 Neurological",
        "05_sensory":      "05 Sensory",
        "06_muscle":       "06 Muscle Test",
        "07_functional":   "07 Functional",
    }

    def __init__(self, on_section_selected: callable, on_back: callable, **kwargs):
        super().__init__(**kwargs)
        self._on_section_selected = on_section_selected
        self._on_back = on_back
        self.active_section = "01_general"

    def compose(self) -> ComposeResult:
        for section_id, label in self.SECTION_LABELS.items():
            btn = Button(label, id=f"objnav_{section_id}")
            if section_id == "01_general":
                btn.add_class("active")
            yield btn
        yield Button("← Subjective", id="objnav_back", classes="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "objnav_back":
            self._on_back()
        elif bid and bid.startswith("objnav_"):
            section_id = bid[7:]
            self.set_active(section_id)
            self._on_section_selected(section_id)

    def set_active(self, section_id: str) -> None:
        for btn in self.query(Button):
            btn.remove_class("active")
        try:
            self.query_one(f"#objnav_{section_id}", Button).add_class("active")
            self.active_section = section_id
        except Exception:
            pass


class ObjectiveAssessmentView(Container):
    """Main content area for Objective TUI: sidebar + section panels."""

    DEFAULT_CSS = """
    ObjectiveAssessmentView {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }
    #obj_section_content {
        width: 1fr;
        height: 100%;
    }
    #obj_section_content_inner {
        width: 100%;
        height: auto;
    }
    """

    class SaveStateChanged(Message):
        def __init__(self, state: str) -> None:
            super().__init__()
            self.state = state

    def __init__(self, session_file: str = "", **kwargs):
        super().__init__(**kwargs)
        self.session_file = session_file
        self.sections: dict = {}
        self.active_section_id = "01_general"
        self._save_task: asyncio.Task | None = None
        self._mounted = False
        self._pending_load: dict | None = None

    def compose(self) -> ComposeResult:
        yield ObjectiveSidebar(
            on_section_selected=self._show_section,
            on_back=self._go_back,
            id="obj_sidebar",
        )
        yield ScrollableContainer(
            Vertical(id="obj_section_content_inner"),
            id="obj_section_content",
        )

    def on_mount(self) -> None:
        self.sections = {
            "01_general":      GeneralSection(id="obj_section_01_general"),
            "02_active":       ActiveMovementSection(id="obj_section_02_active"),
            "03_passive":      PassiveMovementSection(id="obj_section_03_passive"),
            "04_neurological": NeurologicalSection(id="obj_section_04_neurological"),
            "05_sensory":      SensorySection(id="obj_section_05_sensory"),
            "06_muscle":       MuscleSection(id="obj_section_06_muscle"),
            "07_functional":   FunctionalSection(id="obj_section_07_functional"),
        }
        content = self.query_one("#obj_section_content_inner", Vertical)
        for section_id, section in self.sections.items():
            if section_id != self.active_section_id:
                section.display = False
            content.mount(section)

        self._mounted = True
        if self._pending_load is not None:
            data = self._pending_load
            self._pending_load = None
            self.load_session(self.session_file, data)

    def on_unmount(self) -> None:
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

    def load_session(self, session_file: str, data: dict) -> None:
        if not self._mounted:
            self._pending_load = data
            self.session_file = session_file
            return

        self.session_file = session_file
        assessment = data.get("assessment", {})

        _SEC_KEYS = [
            ("01_general",      "general"),
            ("02_active",       "active"),
            ("03_passive",      "passive"),
            ("04_neurological", "neurological"),
            ("05_sensory",      "sensory"),
            ("06_muscle",       "muscle"),
            ("07_functional",   "functional"),
        ]
        for section_id, json_key in _SEC_KEYS:
            section = self.sections.get(section_id)
            if section is None:
                continue
            section.session_file = session_file
            section_data = assessment.get(json_key, {})
            if isinstance(section_data, dict):
                section.load(section_data)

    def _show_section(self, section_id: str) -> None:
        if section_id == self.active_section_id:
            return
        current = self.sections.get(self.active_section_id)
        if current:
            current.display = False
        new = self.sections.get(section_id)
        if new:
            new.display = True
            self.active_section_id = section_id
        try:
            sidebar = self.query_one("#obj_sidebar", ObjectiveSidebar)
            sidebar.set_active(section_id)
        except Exception:
            pass

    def _go_back(self) -> None:
        """Write .focus_tui signal — Subjective TUI watcher raises its window."""
        if self.session_file:
            write_focus_signal(self.session_file, "tui")

    @on(GeneralSection.FieldChanged)
    @on(ActiveMovementSection.FieldChanged)
    @on(PassiveMovementSection.FieldChanged)
    @on(NeurologicalSection.FieldChanged)
    @on(SensorySection.FieldChanged)
    @on(MuscleSection.FieldChanged)
    @on(FunctionalSection.FieldChanged)
    def _on_section_field_changed(self) -> None:
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._save_task:
            self._save_task.cancel()
        self.post_message(self.SaveStateChanged("pending"))

        async def delayed_save():
            await asyncio.sleep(2.0)
            await self._do_save()

        self._save_task = asyncio.create_task(delayed_save())

    async def _do_save(self) -> None:
        if not self.session_file:
            return
        self.post_message(self.SaveStateChanged("saving"))

        _SEC_KEYS = [
            ("01_general",      "general"),
            ("02_active",       "active"),
            ("03_passive",      "passive"),
            ("04_neurological", "neurological"),
            ("05_sensory",      "sensory"),
            ("06_muscle",       "muscle"),
            ("07_functional",   "functional"),
        ]
        assessment_data: dict = {}
        sections_complete: dict[str, bool] = {}

        for section_id, json_key in _SEC_KEYS:
            section = self.sections.get(section_id)
            if section is None:
                continue
            assessment_data[json_key] = section.collect()
            sections_complete[section_id] = section.is_complete()

        save_objective(self.session_file, assessment_data, sections_complete)
        save_raw_report(self.session_file)
        export_session_report(self.session_file)
        self.post_message(self.SaveStateChanged("saved"))
