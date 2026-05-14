"""Assessment view with section navigation."""

import asyncio
import json
import logging
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Button, Label, Static

from .sections.consent import ConsentSection
from .sections.subjective import SubjectiveSection
from .sections.medical import MedicalSection
from .sections.pain_classification import PainClassificationSection
from .sections.outcome_measures import OutcomeMeasuresSection
from .sections.diagnosis import DiagnosisSection
from .sections.barriers import BarriersSection
from .sections.placeholder import PlaceholderSection
from .sections.scratchpad import ScratchpadSection
from .storage import (
    load_consent,
    load_subjective,
    load_medical,
    load_pain_classification,
    load_outcome_measures,
    load_diagnosis,
    load_barriers,
    load_scratchpad,
    save_all_sections,
    save_raw_report,
    assessment_path,
)


logger = logging.getLogger(__name__)


class SectionNav(Static):
    """Left sidebar with section navigation buttons."""

    DEFAULT_CSS = """
    SectionNav {
        width: 20;
        height: 100%;
        border-right: solid $border;
        background: $panel;
        layout: vertical;
        padding: 1 0;
    }

    SectionNav Button {
        width: 100%;
        height: auto;
        border: none;
        background: $panel;
        margin: 0;
        padding: 0 1;
    }

    SectionNav Button:hover {
        background: $boost;
    }

    SectionNav Button.active {
        background: $accent;
        text-style: bold;
    }

    """

    SECTION_LABELS = {
        "01_consent": "01 Consent",
        "02_subjective": "02 Subjective",
        "03_medical": "03 Medical",
        "04_pain_classification": "04 Classification",
        "05_outcome_measures": "05 Outcomes",
        "06_diagnosis": "06 Diagnosis",
        "07_barriers": "07 Barriers",
        "scratchpad": "📝 Notes",
    }

    def __init__(self, on_section_selected: callable, **kwargs):
        super().__init__(**kwargs)
        self.on_section_selected = on_section_selected
        self.active_section = "01_consent"
        self.section_indicators = {}  # section_id -> completion bool

    def compose(self) -> ComposeResult:
        """Create navigation buttons for all sections."""
        for section_id in [
            "01_consent",
            "02_subjective",
            "03_medical",
            "04_pain_classification",
            "05_outcome_measures",
            "06_diagnosis",
            "07_barriers",
            "scratchpad",
        ]:
            label = self.SECTION_LABELS.get(section_id, section_id)
            btn = Button(label, id=f"nav_{section_id}")
            if section_id == "01_consent":
                btn.add_class("active")
            yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle section button clicks."""
        button_id = event.button.id
        if button_id.startswith("nav_"):
            section_id = button_id[4:]  # Remove "nav_" prefix
            self.set_active(section_id)
            self.on_section_selected(section_id)

    def set_active(self, section_id: str) -> None:
        """Highlight the active section button."""
        # Remove active class from all buttons
        for btn in self.query(Button):
            btn.remove_class("active")

        # Add active class to the selected button
        try:
            active_btn = self.query_one(f"#nav_{section_id}", Button)
            active_btn.add_class("active")
            self.active_section = section_id
        except:
            pass

    def set_indicator(self, section_id: str, complete: bool) -> None:
        """Update the completion indicator (●/○) for a section.

        Currently just marks in our dict; rendering happens via button label.
        """
        self.section_indicators[section_id] = complete

    def refresh_indicators(self, sections: dict[str, bool]) -> None:
        """Update all section indicators based on completion dict."""
        for section_id, complete in sections.items():
            self.set_indicator(section_id, complete)

    def set_tab_status(self, section_id: str, status: str) -> None:
        """Set visual status on a section button via variant: 'pending', 'clear', or 'positive'."""
        variant_map = {"pending": "warning", "positive": "error", "clear": "success"}
        try:
            btn = self.query_one(f"#nav_{section_id}", Button)
            btn.variant = variant_map.get(status, "default")
        except Exception:
            pass


class AssessmentView(Container):
    """Main assessment view with section navigation and content area."""

    DEFAULT_CSS = """
    AssessmentView {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    #section_content {
        width: 1fr;
        height: 100%;
    }

    #section_content_inner {
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, session_file: str = "", **kwargs):
        super().__init__(**kwargs)
        self.session_file = session_file
        self.sections = {}
        self.active_section_id = "01_consent"
        self._save_task: asyncio.Task | None = None
        self._mounted = False
        self._pending_load: dict | None = None

    def compose(self) -> ComposeResult:
        """Create sidebar nav + content area."""
        # Navigation sidebar
        yield SectionNav(on_section_selected=self._show_section, id="section_nav")

        # Content area (sections will be mounted in on_mount)
        yield ScrollableContainer(Vertical(id="section_content_inner"), id="section_content")

    def on_mount(self) -> None:
        """Initialize after mounting."""
        # Create all section instances
        self.sections = {
            "01_consent": ConsentSection(id="section_01_consent"),
            "02_subjective": SubjectiveSection(id="section_02_subjective"),
            "03_medical": MedicalSection(id="section_03_medical"),
            "04_pain_classification": PainClassificationSection(id="section_04_pain_classification"),
            "05_outcome_measures": OutcomeMeasuresSection(id="section_05_outcome_measures"),
            "06_diagnosis": DiagnosisSection(id="section_06_diagnosis"),
            "07_barriers": BarriersSection(id="section_07_barriers"),
            "scratchpad": ScratchpadSection(id="section_scratchpad"),
        }

        # Mount all sections to content area
        content = self.query_one("#section_content_inner", Vertical)
        for section_id, section in self.sections.items():
            if section_id != self.active_section_id:
                section.display = False
            content.mount(section)

        # Mark as mounted and process any pending load
        self._mounted = True
        if self._pending_load:
            data = self._pending_load
            self._pending_load = None
            self.load_session(self.session_file, data)

    def on_unmount(self) -> None:
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

    def load_session(self, session_file: str, data: dict) -> None:
        """Load session data into all sections."""
        if not self._mounted:
            # Defer load until mounted
            self._pending_load = data
            self.session_file = session_file
            return

        self.session_file = session_file

        # Prefer TUI-owned _assessment.json; fall back to embedded assessment block
        # for old sessions that predate the split architecture.
        assess_p = assessment_path(session_file)
        if assess_p.exists():
            try:
                assess_file = json.loads(assess_p.read_text())
                assessment = assess_file.get("assessment", {})
                nav_data = assess_file  # sections_complete lives here
            except Exception:
                assessment = data.get("assessment", {})
                nav_data = data
        else:
            assessment = data.get("assessment", {})
            nav_data = data

        # Load consent section
        consent_data = assessment.get("consent", {})
        if "01_consent" in self.sections:
            consent_section = self.sections["01_consent"]
            consent_section.session_file = session_file
            consent_section.load(consent_data)

        # Load subjective section
        subjective_data = assessment.get("subjective", {})
        if "02_subjective" in self.sections:
            subjective_section = self.sections["02_subjective"]
            subjective_section.session_file = session_file
            subjective_section.load(subjective_data)

        # Load medical section
        medical_data = assessment.get("medical", {})
        if "03_medical" in self.sections:
            medical_section = self.sections["03_medical"]
            medical_section.session_file = session_file
            medical_section.load(medical_data)

        # Load pain classification section
        pain_data = assessment.get("pain_classification", {})
        if "04_pain_classification" in self.sections:
            pain_section = self.sections["04_pain_classification"]
            pain_section.session_file = session_file
            pain_section.load(pain_data)

        # Load outcome measures section
        om_data = assessment.get("outcome_measures", {})
        if "05_outcome_measures" in self.sections:
            om_section = self.sections["05_outcome_measures"]
            om_section.session_file = session_file
            om_section.load(om_data)

        # Load barriers section
        br_data = assessment.get("barriers", {})
        if "07_barriers" in self.sections:
            br_section = self.sections["07_barriers"]
            br_section.session_file = session_file
            if isinstance(br_data, dict):
                br_section.load(br_data)

        # Load diagnosis section
        dx_data = assessment.get("diagnosis", {})
        if "06_diagnosis" in self.sections:
            dx_section = self.sections["06_diagnosis"]
            dx_section.session_file = session_file
            if isinstance(dx_data, dict):
                dx_section.load(dx_data)

        # Load scratchpad section
        sp_data = assessment.get("scratchpad", {})
        if "scratchpad" in self.sections:
            sp_section = self.sections["scratchpad"]
            sp_section.session_file = session_file
            if isinstance(sp_data, dict):
                sp_section.load(sp_data)

        # Update nav indicators and medical tab color
        self._refresh_nav_indicators(nav_data)
        self._update_medical_tab_color()

    def _show_section(self, section_id: str) -> None:
        """Switch to a different section."""
        if section_id == self.active_section_id:
            return

        # Capture medical tab status when leaving the medical section
        if self.active_section_id == "03_medical":
            self._update_medical_tab_color()

        # Hide current section
        current = self.sections.get(self.active_section_id)
        if current:
            current.display = False

        # Show new section
        new = self.sections.get(section_id)
        if new:
            new.display = True
            self.active_section_id = section_id

        # Refresh cross-reference badges when entering pain classification or outcome measures
        if section_id == "04_pain_classification":
            pain_section = self.sections.get("04_pain_classification")
            if pain_section:
                pain_section.update_cross_refs()
        elif section_id == "05_outcome_measures":
            om_section = self.sections.get("05_outcome_measures")
            if om_section:
                om_section.update_cross_refs()
        elif section_id == "06_diagnosis":
            dx_section = self.sections.get("06_diagnosis")
            if dx_section:
                dx_section.update_cross_refs()
        elif section_id == "07_barriers":
            br_section = self.sections.get("07_barriers")
            if br_section:
                br_section.update_cross_refs()

        # Update nav highlight
        nav = self.query_one("#section_nav", SectionNav)
        nav.set_active(section_id)

        # Show subsection nav bar for sections that have one; swap chips to match
        has_subnav = section_id in ("02_subjective", "03_medical", "04_pain_classification", "05_outcome_measures", "06_diagnosis", "07_barriers")
        try:
            nav_bar = self.app.query_one("#subsection_nav_bar")
            nav_bar.display = has_subnav
            if has_subnav:
                nav_bar.set_context(section_id)
        except Exception:
            pass

    def _update_medical_tab_color(self) -> None:
        """Update the 03 Medical nav button to orange/green/red based on urgent red flag review."""
        try:
            medical_section = self.sections.get("03_medical")
            if medical_section is None:
                return
            status = medical_section.urgent_red_flag_status()
            nav = self.query_one("#section_nav", SectionNav)
            nav.set_tab_status("03_medical", status)
        except Exception:
            pass

    def _refresh_nav_indicators(self, data: dict) -> None:
        """Update all section completion indicators from stored sections_complete dict."""
        sections_complete = data.get("sections_complete", {})
        nav = self.query_one("#section_nav", SectionNav)
        nav.refresh_indicators(sections_complete)

    def _schedule_save(self) -> None:
        """Schedule a debounced save after 2 seconds of inactivity."""
        if self._save_task:
            self._save_task.cancel()
        self.post_message(self.SaveStateChanged("pending"))

        async def delayed_save():
            await asyncio.sleep(2.0)
            await self._do_save()

        self._save_task = asyncio.create_task(delayed_save())

    async def _do_save(self) -> None:
        """Collect ALL sections and write the complete assessment in one atomic pass."""
        if not self.session_file:
            return

        self.post_message(self.SaveStateChanged("saving"))

        # Section ID → key used in assessment JSON block
        _SEC_KEYS = [
            ("01_consent",           "consent"),
            ("02_subjective",        "subjective"),
            ("03_medical",           "medical"),
            ("04_pain_classification", "pain_classification"),
            ("05_outcome_measures",  "outcome_measures"),
            ("06_diagnosis",         "diagnosis"),
            ("07_barriers",          "barriers"),
            ("scratchpad",           "scratchpad"),
        ]

        assessment_data: dict = {}
        sections_complete: dict[str, bool] = {}

        for section_id, json_key in _SEC_KEYS:
            section = self.sections.get(section_id)
            if section is None:
                continue
            assessment_data[json_key] = section.collect()
            if section_id != "scratchpad":
                sections_complete[section_id] = section.is_complete()

        save_all_sections(self.session_file, assessment_data, sections_complete)

        # Update nav indicators from freshly written _assessment.json
        assess_p = assessment_path(self.session_file)
        nav_data = json.loads(assess_p.read_text()) if assess_p.exists() else {}
        self._refresh_nav_indicators(nav_data)
        self._update_medical_tab_color()

        # Regenerate raw report (obsidian-style continuous write)
        save_raw_report(self.session_file)

        self.post_message(self.SaveStateChanged("saved"))

    class SaveStateChanged(Message):
        """Posted when save state changes: 'pending', 'saving', or 'saved'."""
        def __init__(self, state: str) -> None:
            super().__init__()
            self.state = state

    def on_consent_section_field_changed(self) -> None:
        self._schedule_save()

    def on_subjective_section_field_changed(self) -> None:
        self._schedule_save()

    def on_medical_section_field_changed(self) -> None:
        self._schedule_save()
        self._update_medical_tab_color()

    def on_pain_classification_section_field_changed(self) -> None:
        self._schedule_save()

    def on_outcome_measures_section_field_changed(self) -> None:
        self._schedule_save()

    def on_diagnosis_section_field_changed(self) -> None:
        self._schedule_save()

    def on_barriers_section_field_changed(self) -> None:
        self._schedule_save()

    def on_scratchpad_section_field_changed(self) -> None:
        self._schedule_save()
