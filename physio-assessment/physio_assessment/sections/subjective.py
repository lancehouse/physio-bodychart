"""Subjective Examination section (core/02)."""

from textual.app import ComposeResult, on
from textual.containers import Vertical, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from .consent import YesNoField


class SubsectionNav(Static):
    """Fixed top navigation bar — yields jump buttons only."""

    SUBSECTIONS = [
        ("Symptoms",    "subj_symptoms"),
        ("History",     "subj_history"),
        ("Flare-ups",   "subj_flareups"),
        ("Mgmt",        "subj_management"),
        ("Activity",    "subj_activity"),
        ("Work",        "subj_work"),
        ("Sleep",       "subj_sleep"),
        ("Behaviour",   "subj_behaviour"),
        ("Psychosocial","subj_psychosocial"),
        ("Risk",        "subj_suicide"),
    ]

    DEFAULT_CSS = """
    SubsectionNav {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    SubsectionNav Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    SubsectionNav Button:hover {
        background: $accent;
    }
    """

    def __init__(self, on_jump_to: callable, **kwargs):
        super().__init__(**kwargs)
        self._on_jump_to = on_jump_to

    def compose(self) -> ComposeResult:
        for label, anchor_id in self.SUBSECTIONS:
            yield Button(label, id=f"nav_{anchor_id}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid and bid.startswith("nav_"):
            self._on_jump_to(bid[4:])
        event.stop()


# ---------------------------------------------------------------------------
# SubjectiveSection
# UI layout:  SubsectionNav (fixed) / ScrollableContainer (scrolls)
# Data logic: collect() and load() are entirely independent of UI structure
# ---------------------------------------------------------------------------

class SubjectiveSection(BaseSection):
    """Subjective Examination section (core/02).

    UI and data are deliberately separated:
    - compose() / CSS control layout only
    - collect() / load() reference widget IDs, not layout structure
    - Rearranging the UI never requires touching collect() or load()
    """

    DEFAULT_CSS = """
    SubjectiveSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #subj_nav {
        height: auto;
    }

    #subj_scroll {
        width: 100%;
        height: 1fr;
    }

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

    TextArea, Input {
        height: auto;
        min-height: 1;
        margin-bottom: 0;
    }

    Label {
        margin-bottom: 0;
    }
    """

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield SubsectionNav(on_jump_to=self._jump_to, id="subj_nav")

        with ScrollableContainer(id="subj_scroll"):
            with Vertical(id="subj_content"):
                yield Label("Subjective Examination", classes="section_title")

                # ── Symptoms ──────────────────────────────────────────
                yield Label("— Symptoms —", classes="subsection_header", id="subj_symptoms")
                yield YesNoField("Body chart completed", field_id="body_chart_completed")
                yield Label("Location:")
                yield TextArea(id="symptom_location", language="plain")
                yield Label("Nature:")
                yield TextArea(id="symptom_nature", language="plain")

                # ── History ───────────────────────────────────────────
                yield Label("— History —", classes="subsection_header", id="subj_history")
                yield Label("Onset (mechanism / date / context):")
                yield TextArea(id="onset", language="plain")
                yield Label("Duration:")
                yield TextArea(id="duration", language="plain")
                yield Label("Course:")
                yield YesNoField("Improving",   field_id="course_improving")
                yield YesNoField("Worsening",   field_id="course_worsening")
                yield YesNoField("Stable",      field_id="course_stable")
                yield YesNoField("Fluctuating", field_id="course_fluctuating")
                yield Label("Context at onset (stress / illness / life events):")
                yield TextArea(id="context_at_onset", language="plain")
                yield Label("Previous similar episodes:")
                yield TextArea(id="previous_episodes", language="plain")
                yield Label("Previous treatment and response:")
                yield TextArea(id="previous_treatment", language="plain")

                # ── Flare-ups ─────────────────────────────────────────
                yield Label("— Flare-ups —", classes="subsection_header", id="subj_flareups")
                yield Label("Frequency:")
                yield YesNoField("Rare",       field_id="flareup_rare")
                yield YesNoField("Occasional", field_id="flareup_occasional")
                yield YesNoField("Frequent",   field_id="flareup_frequent")
                yield Label("Triggers:")
                yield TextArea(id="flareup_triggers", language="plain")
                yield Label("Predictability:")
                yield TextArea(id="flareup_predictability", language="plain")
                yield Label("Duration:")
                yield TextArea(id="flareup_duration", language="plain")

                # ── Self-Management ───────────────────────────────────
                yield Label("— Self-Management & Control —", classes="subsection_header", id="subj_management")
                yield Label("Perceived control over pain (0–10):")
                yield Input(id="pain_control_score", placeholder="0–10")
                yield Label("Ability to prevent flare-ups:")
                yield TextArea(id="flareup_prevention", language="plain")
                yield Label("Strategies used to manage:")
                yield TextArea(id="management_strategies", language="plain")
                yield Label("Confidence managing condition (0–10):")
                yield Input(id="confidence_score", placeholder="0–10")

                # ── Activity & Exercise ───────────────────────────────
                yield Label("— Activity & Exercise —", classes="subsection_header", id="subj_activity")
                yield Label("Pre-injury activity level:")
                yield TextArea(id="pre_activity_level", language="plain")
                yield Label("Current activity level:")
                yield TextArea(id="current_activity_level", language="plain")
                yield Label("Exercise type:")
                yield TextArea(id="exercise_type", language="plain")
                yield Label("Exercise dose (frequency / duration):")
                yield TextArea(id="exercise_dose", language="plain")
                yield Label("Response to exercise:")
                yield TextArea(id="exercise_response", language="plain")

                # ── Work ──────────────────────────────────────────────
                yield Label("— Work —", classes="subsection_header", id="subj_work")
                yield Label("Pre-injury role:")
                yield TextArea(id="pre_injury_role", language="plain")
                yield Label("Pre-injury hours per week:")
                yield Input(id="pre_injury_hours", placeholder="hours")
                yield Label("Pre-injury duties:")
                yield TextArea(id="pre_injury_duties", language="plain")
                yield Label("Current work status:")
                yield TextArea(id="current_work_status", language="plain")
                yield Label("Current hours:")
                yield Input(id="current_hours", placeholder="hours")
                yield Label("Current duties / restrictions:")
                yield TextArea(id="current_duties", language="plain")

                # ── Sleep ─────────────────────────────────────────────
                yield Label("— Sleep —", classes="subsection_header", id="subj_sleep")
                yield Label("Bed/pillow age and description:")
                yield TextArea(id="bed_description", language="plain")
                yield YesNoField("Difficulty falling asleep", field_id="sleep_difficulty")
                yield Label("Severity if difficult (0–10):")
                yield Input(id="sleep_difficulty_severity", placeholder="0–10")
                yield Label("Time to fall asleep (minutes):")
                yield Input(id="sleep_onset_time", placeholder="minutes")
                yield Label("Sleep position:")
                yield TextArea(id="sleep_position", language="plain")
                yield Label("Total sleep hours:")
                yield Input(id="total_sleep_hours", placeholder="hours")
                yield YesNoField("Night waking", field_id="night_waking")
                yield Label("Night waking frequency:")
                yield TextArea(id="night_waking_frequency", language="plain")
                yield Label("Night waking reason:")
                yield TextArea(id="night_waking_reason", language="plain")
                yield Label("Times out of bed at night:")
                yield Input(id="bed_exits_count", placeholder="number")
                yield Label("Severity of night waking (0–10):")
                yield Input(id="night_waking_severity", placeholder="0–10")
                yield Label("Morning pain / stiffness duration:")
                yield TextArea(id="morning_stiffness", language="plain")
                yield YesNoField("Daytime naps", field_id="daytime_naps")
                yield Label("Nap frequency:")
                yield TextArea(id="nap_frequency", language="plain")
                yield Label("Nap duration (minutes):")
                yield Input(id="nap_duration", placeholder="minutes")
                yield Label("Energy levels by end of day:")
                yield TextArea(id="energy_levels", language="plain")

                # ── Behaviour ─────────────────────────────────────────
                yield Label("— Behaviour of Symptoms —", classes="subsection_header", id="subj_behaviour")
                yield Label("Aggravating factors:")
                yield TextArea(id="aggravating_factors", language="plain")
                yield Label("Easing factors:")
                yield TextArea(id="easing_factors", language="plain")
                yield YesNoField("Mood influences pain", field_id="mood_influences")
                yield Label("Comments on daily pattern:")
                yield TextArea(id="daily_pattern_comments", language="plain")

                # ── Psychosocial ──────────────────────────────────────
                yield Label("— Psychosocial —", classes="subsection_header", id="subj_psychosocial")
                yield Label("Social situation (home / partner / family / friends):")
                yield TextArea(id="social_situation", language="plain")
                yield Label("Financial / residential stability:")
                yield TextArea(id="financial_status", language="plain")
                yield Label("Cultural / language / religious considerations:")
                yield TextArea(id="cultural_considerations", language="plain")
                yield Label("Psychological distress observed or volunteered:")
                yield TextArea(id="psychological_distress", language="plain")
                yield Label("Formal screening tool used:")
                yield TextArea(id="screening_tool", language="plain")

                # ── Suicide Risk ──────────────────────────────────────
                yield Label("— Suicide / Self-Harm Risk —", classes="subsection_header", id="subj_suicide")
                yield YesNoField("Thoughts of self-harm or suicide", field_id="self_harm_risk")
                yield Label("Plan (if yes):")
                yield TextArea(id="harm_plan", language="plain")
                yield Label("Means (if yes):")
                yield TextArea(id="harm_means", language="plain")
                yield Label("Intent (if yes):")
                yield TextArea(id="harm_intent", language="plain")
                yield Label("Action taken (if yes):")
                yield TextArea(id="harm_action", language="plain")

    def _jump_to(self, anchor_id: str) -> None:
        """Scroll #subj_scroll to the target subsection header."""
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#subj_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
        except Exception:
            pass

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
                data[fid] = self.query_one(f"#{fid}", YesNoField).get_value()
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
            subjective = data.get("subjective", {}) if isinstance(data, dict) else {}
            for fid in self._TOGGLE_FIELDS:
                if fid in subjective:
                    try:
                        self.query_one(f"#{fid}", YesNoField).set_value(subjective[fid])
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

    @on(YesNoField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
