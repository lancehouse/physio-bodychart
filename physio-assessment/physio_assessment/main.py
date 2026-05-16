"""Textual TUI main entry point."""

import sys
import asyncio
from pathlib import Path
from textual.app import ComposeResult, App
from textual.binding import Binding
from textual.widgets import Header, Footer
from textual.containers import Container
from .tui import PhysioAssessmentTUI, SessionListScreen
from .assessment_view import AssessmentView
from .storage import load_assessment, load_session_current


class PhysioAssessment(App):
    """Main Textual application for PhysioChart assessment system."""

    TITLE = "PhysioChart Assessment System"
    SUB_TITLE = "Specialist Physiotherapy Assessment & Report Generator"
    ANIMATION_SPEED = 2.0

    BINDINGS = [
        ("ctrl+q", "quit",              "Quit"),
        ("ctrl+l", "show_session_list", "Sessions"),
        # Section tab navigation — F1-F9 (priority=True overrides any focused widget)
        Binding("f1", "section_consent",          show=False, priority=True),
        Binding("f2", "section_subjective",       show=False, priority=True),
        Binding("f3", "section_medical",          show=False, priority=True),
        Binding("f4", "section_objective",        show=False, priority=True),
        Binding("f5", "section_pain",             show=False, priority=True),
        Binding("f6", "section_outcomes",         show=False, priority=True),
        Binding("f7", "section_diagnosis",        show=False, priority=True),
        Binding("f8", "section_barriers",         show=False, priority=True),
        Binding("f9", "section_scratchpad",       show=False, priority=True),
        # Subjective subsection jump — Alt+letter (priority=True overrides TextArea)
        Binding("alt+s", "sub_symptoms",             show=False, priority=True),
        Binding("alt+h", "sub_history",              show=False, priority=True),
        Binding("alt+u", "sub_flareups",             show=False, priority=True),
        Binding("alt+m", "sub_management",           show=False, priority=True),
        Binding("alt+a", "sub_activity",             show=False, priority=True),
        Binding("alt+w", "sub_work",                 show=False, priority=True),
        Binding("alt+e", "sub_sleep",                show=False, priority=True),
        Binding("alt+v", "sub_behaviour",            show=False, priority=True),
        Binding("alt+p", "sub_psychosocial",         show=False, priority=True),
        Binding("alt+r", "sub_risk",                 show=False, priority=True),
    ]

    CSS = """
    Screen { background: $surface; }
    """

    def __init__(self, session_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self.current_session_path = session_path
        self.assessment_screen = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container()
        yield Footer()

    def on_mount(self) -> None:
        if self.current_session_path:
            asyncio.create_task(self.show_assessment_form())
            return

        current_data = load_session_current()
        if current_data and current_data.get("session_file"):
            self.current_session_path = current_data["session_file"]
            asyncio.create_task(self.show_assessment_form())
        else:
            self.show_session_list()

    def show_session_list(self) -> None:
        main = self.query_one(Container)
        main.remove_children()
        session_list = SessionListScreen(on_session_selected=self.on_session_selected)
        main.mount(session_list)

    async def on_session_selected(self, session_path: str) -> None:
        self.current_session_path = session_path
        await self.show_assessment_form()

    async def show_assessment_form(self) -> None:
        main = self.query_one(Container)
        main.remove_children()
        assessment = PhysioAssessmentTUI(session_path=self.current_session_path)
        self.assessment_screen = assessment
        main.mount(assessment)

    def on_session_list_screen_new_session_requested(self) -> None:
        # New session creation requires a patient-ID dialog (not yet implemented).
        # For now, just refresh the session list so the button doesn't crash.
        self.show_session_list()

    async def action_show_session_list(self) -> None:
        if self.assessment_screen:
            try:
                await self.assessment_screen.save_if_pending()
            except Exception:
                pass
        self.show_session_list()

    # ------------------------------------------------------------------
    # Section navigation (Alt+1-7, Alt+N) — on App so they're global
    # ------------------------------------------------------------------

    def _goto_section(self, section_id: str) -> None:
        try:
            av = self.query_one("#assessment_view", AssessmentView)
            av._show_section(section_id)
            section = av.sections.get(section_id)
            if section:
                section.focus_first_field()
        except Exception:
            pass

    def action_section_consent(self):    self._goto_section("01_consent")
    def action_section_subjective(self): self._goto_section("02_subjective")
    def action_section_medical(self):    self._goto_section("03_medical")
    def action_section_objective(self):  self._goto_section("04_objective")
    def action_section_pain(self):       self._goto_section("04_pain_classification")
    def action_section_outcomes(self):   self._goto_section("05_outcome_measures")
    def action_section_diagnosis(self):  self._goto_section("06_diagnosis")
    def action_section_barriers(self):   self._goto_section("07_barriers")
    def action_section_scratchpad(self): self._goto_section("scratchpad")

    # ------------------------------------------------------------------
    # Subjective subsection jump (Alt+S/H/F/M/A/W/E/B/P/R) — global
    # ------------------------------------------------------------------

    def _goto_subjective_sub(self, anchor_id: str) -> None:
        try:
            self.query_one("#section_02_subjective")._jump_to(anchor_id)
        except Exception:
            pass

    def action_sub_symptoms(self):     self._goto_subjective_sub("subj_symptoms")
    def action_sub_history(self):      self._goto_subjective_sub("subj_history")
    def action_sub_flareups(self):     self._goto_subjective_sub("subj_flareups")
    def action_sub_management(self):   self._goto_subjective_sub("subj_management")
    def action_sub_activity(self):     self._goto_subjective_sub("subj_activity")
    def action_sub_work(self):         self._goto_subjective_sub("subj_work")
    def action_sub_sleep(self):        self._goto_subjective_sub("subj_sleep")
    def action_sub_behaviour(self):    self._goto_subjective_sub("subj_behaviour")
    def action_sub_psychosocial(self): self._goto_subjective_sub("subj_psychosocial")
    def action_sub_risk(self):         self._goto_subjective_sub("subj_suicide")


def main():
    """Entry point — accepts optional --session <path> argument."""
    session_path = ""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--session" and i + 1 < len(args):
            session_path = args[i + 1]
            break

    app = PhysioAssessment(session_path=session_path)
    app.run()


if __name__ == "__main__":
    main()
