"""Subjective Examination section (core/02)."""

from textual.app import ComposeResult, on
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Button
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton, FlagButton


# ---------------------------------------------------------------------------
# SubjectiveSection
# UI layout:  content scrolled by outer #section_content
#             subsection nav lives in the top chrome row (SubsectionNavBar)
# Data logic: collect() and load() are entirely independent of UI structure
# ---------------------------------------------------------------------------

class SubjectiveSection(BaseSection):
    """Subjective Examination section (core/02).

    UI and data are deliberately separated:
    - compose() / CSS control layout only
    - collect() / load() reference widget IDs, not layout structure
    - Rearranging the UI never requires touching collect() or load()

    Alt+S/H/F/M/A/W/L/B/P/R jump to subsections (active when this tab is showing).
    """

    DEFAULT_CSS = """
    SubjectiveSection {
        width: 100%;
        height: auto;
        layout: vertical;
        padding: 0;
    }

    #subj_nav { height: auto; }

    #subj_content {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title {
        text-style: bold;
        margin-bottom: 0;
    }

    .subsection_header {
        text-style: bold;
        color: $primary;
        padding-top: 1;
        margin-bottom: 0;
    }

    /* Label + field on one horizontal row */
    .field_row {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0;
    }

    .field_row Label {
        width: 28;
        height: auto;
        padding: 0 1 0 0;
    }

    .field_row Input {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    .field_row TextArea {
        width: 1fr;
        height: auto;
        min-height: 2;
        padding: 0 1;
    }

    /* Button grid rows — up to 4 across */
    .btn_row {
        height: auto;
        width: 100%;
        margin: 0;
        padding: 0;
    }

    CheckButton {
        width: auto;
        height: 3;
        min-width: 16;
        margin: 0 1 0 0;
    }

    .solo_btn {
        margin: 0 0 0 0;
    }
    """

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical(id="subj_content"):
            yield Label("Subjective Examination", classes="section_title")

            # ── Symptoms ──────────────────────────────────────────────
            yield Label("— Symptoms —", classes="subsection_header", id="subj_symptoms")
            yield CheckButton("Body chart completed", id="body_chart_completed", classes="solo_btn")
            with Horizontal(classes="field_row"):
                yield Label("Location\n& distribution:")
                yield TextArea(id="symptom_location", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Nature of symptoms\n(quality / type):")
                yield TextArea(id="symptom_nature", language="plain")

            # ── History ───────────────────────────────────────────────
            yield Label("— History —", classes="subsection_header", id="subj_history")
            with Horizontal(classes="field_row"):
                yield Label("Onset\n(mechanism / date):")
                yield TextArea(id="onset", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Duration:")
                yield TextArea(id="duration", language="plain")
            yield Label("Course:")
            with Horizontal(classes="btn_row"):
                yield CheckButton("Improving",   id="course_improving")
                yield FlagButton( "Worsening",   id="course_worsening")
                yield CheckButton("Stable",      id="course_stable")
                yield CheckButton("Fluctuating", id="course_fluctuating")
            with Horizontal(classes="field_row"):
                yield Label("Context at onset\n(stress / life events):")
                yield TextArea(id="context_at_onset", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Previous similar\nepisodes:")
                yield TextArea(id="previous_episodes", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Previous treatment\n& response:")
                yield TextArea(id="previous_treatment", language="plain")

            # ── Flare-ups ─────────────────────────────────────────────
            yield Label("— Flare-ups —", classes="subsection_header", id="subj_flareups")
            yield Label("Frequency:")
            with Horizontal(classes="btn_row"):
                yield CheckButton("Rare",       id="flareup_rare")
                yield CheckButton("Occasional", id="flareup_occasional")
                yield FlagButton( "Frequent",   id="flareup_frequent")
            with Horizontal(classes="field_row"):
                yield Label("Triggers:")
                yield TextArea(id="flareup_triggers", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Predictability:")
                yield TextArea(id="flareup_predictability", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Duration of flare:")
                yield TextArea(id="flareup_duration", language="plain")

            # ── Self-Management ───────────────────────────────────────
            yield Label("— Self-Management & Control —", classes="subsection_header", id="subj_management")
            with Horizontal(classes="field_row"):
                yield Label("Perceived control\nover pain (0–10):")
                yield Input(id="pain_control_score", placeholder="0–10")
            with Horizontal(classes="field_row"):
                yield Label("Ability to prevent\nflare-ups:")
                yield TextArea(id="flareup_prevention", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Management\nstrategies used:")
                yield TextArea(id="management_strategies", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Confidence managing\ncondition (0–10):")
                yield Input(id="confidence_score", placeholder="0–10")

            # ── Activity & Exercise ───────────────────────────────────
            yield Label("— Activity & Exercise —", classes="subsection_header", id="subj_activity")
            with Horizontal(classes="field_row"):
                yield Label("Pre-injury\nactivity level:")
                yield TextArea(id="pre_activity_level", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Current\nactivity level:")
                yield TextArea(id="current_activity_level", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Exercise type:")
                yield TextArea(id="exercise_type", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Exercise dose\n(frequency / duration):")
                yield TextArea(id="exercise_dose", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Response\nto exercise:")
                yield TextArea(id="exercise_response", language="plain")

            # ── Work ──────────────────────────────────────────────────
            yield Label("— Work —", classes="subsection_header", id="subj_work")
            with Horizontal(classes="field_row"):
                yield Label("Pre-injury role:")
                yield TextArea(id="pre_injury_role", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Pre-injury hours\nper week:")
                yield Input(id="pre_injury_hours", placeholder="hours")
            with Horizontal(classes="field_row"):
                yield Label("Pre-injury duties:")
                yield TextArea(id="pre_injury_duties", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Current work status:")
                yield TextArea(id="current_work_status", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Current hours\nper week:")
                yield Input(id="current_hours", placeholder="hours")
            with Horizontal(classes="field_row"):
                yield Label("Current duties\n& restrictions:")
                yield TextArea(id="current_duties", language="plain")

            # ── Sleep ─────────────────────────────────────────────────
            yield Label("— Sleep —", classes="subsection_header", id="subj_sleep")
            with Horizontal(classes="field_row"):
                yield Label("Bed & pillow\n(age / description):")
                yield TextArea(id="bed_description", language="plain")
            yield Label("Sleep problems:")
            with Horizontal(classes="btn_row"):
                yield FlagButton("Difficulty falling asleep", id="sleep_difficulty")
                yield FlagButton("Night waking",             id="night_waking")
                yield CheckButton("Daytime naps",            id="daytime_naps")
            with Horizontal(classes="field_row"):
                yield Label("Difficulty severity\n(0–10):")
                yield Input(id="sleep_difficulty_severity", placeholder="0–10")
            with Horizontal(classes="field_row"):
                yield Label("Time to fall asleep\n(minutes):")
                yield Input(id="sleep_onset_time", placeholder="minutes")
            with Horizontal(classes="field_row"):
                yield Label("Sleep position:")
                yield TextArea(id="sleep_position", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Total sleep hours:")
                yield Input(id="total_sleep_hours", placeholder="hours")
            with Horizontal(classes="field_row"):
                yield Label("Night waking\nfrequency:")
                yield TextArea(id="night_waking_frequency", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Night waking\nreason:")
                yield TextArea(id="night_waking_reason", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Times out of bed\nat night:")
                yield Input(id="bed_exits_count", placeholder="number")
            with Horizontal(classes="field_row"):
                yield Label("Night waking\nseverity (0–10):")
                yield Input(id="night_waking_severity", placeholder="0–10")
            with Horizontal(classes="field_row"):
                yield Label("Morning pain\n& stiffness:")
                yield TextArea(id="morning_stiffness", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Nap frequency:")
                yield TextArea(id="nap_frequency", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Nap duration\n(minutes):")
                yield Input(id="nap_duration", placeholder="minutes")
            with Horizontal(classes="field_row"):
                yield Label("Energy levels\nby end of day:")
                yield TextArea(id="energy_levels", language="plain")

            # ── Behaviour ─────────────────────────────────────────────
            yield Label("— Behaviour of Symptoms —", classes="subsection_header", id="subj_behaviour")
            with Horizontal(classes="field_row"):
                yield Label("Aggravating factors:")
                yield TextArea(id="aggravating_factors", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Easing factors:")
                yield TextArea(id="easing_factors", language="plain")
            yield CheckButton("Mood influences pain", id="mood_influences", classes="solo_btn")
            with Horizontal(classes="field_row"):
                yield Label("Daily pattern\ncomments:")
                yield TextArea(id="daily_pattern_comments", language="plain")

            # ── Psychosocial ──────────────────────────────────────────
            yield Label("— Psychosocial —", classes="subsection_header", id="subj_psychosocial")
            with Horizontal(classes="field_row"):
                yield Label("Social situation\n(home / family):")
                yield TextArea(id="social_situation", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Financial &\nresidential stability:")
                yield TextArea(id="financial_status", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Cultural / language\n/ religious:")
                yield TextArea(id="cultural_considerations", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Psychological distress\nobserved / volunteered:")
                yield TextArea(id="psychological_distress", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Formal screening\ntool used:")
                yield TextArea(id="screening_tool", language="plain")

            # ── Suicide / Self-Harm Risk ──────────────────────────────
            yield Label("— Suicide / Self-Harm Risk —", classes="subsection_header", id="subj_suicide")
            yield FlagButton("Thoughts of self-harm or suicide", id="self_harm_risk", classes="solo_btn")
            with Horizontal(classes="field_row"):
                yield Label("Plan (if yes):")
                yield TextArea(id="harm_plan", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Means (if yes):")
                yield TextArea(id="harm_means", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Intent (if yes):")
                yield TextArea(id="harm_intent", language="plain")
            with Horizontal(classes="field_row"):
                yield Label("Action taken\n(if yes):")
                yield TextArea(id="harm_action", language="plain")

    def _jump_to(self, anchor_id: str) -> None:
        """Scroll to subsection header and focus its first interactive widget."""
        try:
            target = self.query_one(f"#{anchor_id}")
            self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(
                target, top=True
            )
            # Focus the first interactive widget that follows the anchor in the DOM
            all_interactive = list(self.query("Input, TextArea, CheckButton, Button"))
            all_nodes = list(self.query("*"))
            anchor_idx = all_nodes.index(target)
            for widget in all_interactive:
                if all_nodes.index(widget) > anchor_idx:
                    widget.focus()
                    break
        except Exception:
            pass

    def action_jump(self, anchor_id: str) -> None:
        self._jump_to(anchor_id)

    # ------------------------------------------------------------------
    # Data — independent of UI structure
    # ------------------------------------------------------------------

    _TOGGLE_FIELDS = [
        "body_chart_completed",
        "course_improving", "course_worsening", "course_stable", "course_fluctuating",
        "flareup_rare", "flareup_occasional", "flareup_frequent",
        "sleep_difficulty", "night_waking", "daytime_naps",
        "mood_influences", "self_harm_risk",
    ]

    _TEXT_FIELDS = [
        "symptom_location", "symptom_nature",
        "onset", "duration", "context_at_onset", "previous_episodes", "previous_treatment",
        "flareup_triggers", "flareup_predictability", "flareup_duration",
        "flareup_prevention", "management_strategies",
        "pre_activity_level", "current_activity_level",
        "exercise_type", "exercise_dose", "exercise_response",
        "pre_injury_role", "pre_injury_duties",
        "current_work_status", "current_duties",
        "bed_description", "sleep_position",
        "night_waking_frequency", "night_waking_reason", "morning_stiffness",
        "nap_frequency", "energy_levels",
        "aggravating_factors", "easing_factors", "daily_pattern_comments",
        "social_situation", "financial_status", "cultural_considerations",
        "psychological_distress", "screening_tool",
        "harm_plan", "harm_means", "harm_intent", "harm_action",
    ]

    _INPUT_FIELDS = [
        "pain_control_score", "confidence_score",
        "pre_injury_hours", "current_hours",
        "sleep_difficulty_severity", "sleep_onset_time", "total_sleep_hours",
        "bed_exits_count", "night_waking_severity", "nap_duration",
    ]

    def collect(self) -> dict:
        data = {}
        for fid in self._TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
            except Exception:
                data[fid] = None
        for fid in self._TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        for fid in self._INPUT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", Input).value
            except Exception:
                data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            subjective = data if isinstance(data, dict) else {}
            for fid in self._TOGGLE_FIELDS:
                if fid in subjective:
                    try:
                        self.query_one(f"#{fid}", CheckButton).set_value(subjective[fid])
                    except Exception:
                        pass
            for fid in self._TEXT_FIELDS:
                if fid in subjective:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = subjective[fid]
                    except Exception:
                        pass
            for fid in self._INPUT_FIELDS:
                if fid in subjective:
                    try:
                        self.query_one(f"#{fid}", Input).value = subjective[fid]
                    except Exception:
                        pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        return self.collect().get("self_harm_risk") is not None

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    @on(CheckButton.Changed)
    @on(Input.Changed)
    @on(TextArea.Changed)
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
