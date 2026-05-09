"""Consent & Session Setup section (core/01)."""

from textual.app import ComposeResult, on
from textual.containers import Container, Vertical
from textual.widgets import Label, Input, TextArea, Button
from textual.message import Message

from .base import BaseSection


class YesNoField(Container):
    """Helper widget: label + toggle button showing YES/NO."""

    DEFAULT_CSS = """
    YesNoField {
        height: auto;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    YesNoField > Label {
        width: 1fr;
        margin-bottom: 0;
        padding-right: 1;
    }
    YesNoField Button {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 2;
    }
    """

    def __init__(self, label: str, field_id: str, **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._label = label
        self._field_id = field_id
        self._value = None

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Button("?", id=f"{self._field_id}_toggle", variant="primary")

    def get_value(self) -> bool | None:
        """Return True (Yes), False (No), or None (not selected)."""
        return self._value

    def set_value(self, value: bool | None) -> None:
        """Set the toggle state without triggering a save."""
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_toggle", Button)
            if value is True:
                btn.label = "YES"
                btn.variant = "success"
            elif value is False:
                btn.label = "NO"
                btn.variant = "error"
            else:
                btn.label = "?"
                btn.variant = "primary"
        except:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Cycle through YES -> NO -> unselected."""
        if event.button.id == f"{self._field_id}_toggle":
            if self._value is True:
                self.set_value(False)
            elif self._value is False:
                self.set_value(None)
            else:
                self.set_value(True)
            self.post_message(YesNoField.Changed())
            event.stop()

    class Changed(Message):
        pass


class ConsentSection(BaseSection):
    """Consent & Session Setup section.

    Includes: consent checkboxes, preferred name, session framing,
    and ICE+ (patient perspective) fields.
    """

    DEFAULT_CSS = """
    ConsentSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title {
        text-style: bold;
        color: $text;
        padding-bottom: 0;
        margin-bottom: 0;
    }

    .subsection_header {
        text-style: bold;
        color: $primary;
        margin-top: 0;
        margin-bottom: 0;
        padding-top: 1;
    }

    #preferred_name_input {
        width: 100%;
        margin-bottom: 0;
        height: auto;
    }

    #patient_expectations {
        height: auto;
        margin-bottom: 0;
        min-height: 1;
    }

    #reason_for_attending {
        height: auto;
        margin-bottom: 0;
        min-height: 1;
    }

    #cause_understanding_detail {
        height: auto;
        margin-bottom: 0;
        min-height: 1;
    }

    #prognosis_expectations {
        height: auto;
        margin-bottom: 0;
        min-height: 1;
    }

    #treatment_preference {
        height: auto;
        margin-bottom: 0;
        min-height: 1;
    }

    #consent_status {
        color: $success;
        text-style: bold;
        margin-top: 0;
        padding-top: 1;
    }

    Label {
        margin-bottom: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Consent & Session Setup", classes="section_title")

        # Consent section
        yield Label("— Consent —", classes="subsection_header")
        yield YesNoField("Consent to proceed", field_id="consent_to_proceed")
        yield YesNoField("Consent to discuss sensitive topics", field_id="consent_sensitive_topics")

        # Preferred name (required)
        yield Label("Preferred name (required for completion):")
        yield Input(id="preferred_name_input", placeholder="Patient's preferred name")

        # Session Framing (collapsible)
        yield Label("Session Framing (scripted prompts):", classes="subsection_header")
        yield Label("Remind yourself to explain:")
        yield YesNoField("Pain as multifactorial explained", field_id="framing_pain_multifactorial")
        yield YesNoField("Education as part of treatment explained", field_id="framing_education_treatment")
        yield Label("Patient expectations for this session:")
        yield TextArea(id="patient_expectations", language="plain")

        # ICE+ (Patient Perspective)
        yield Label("— Patient Perspective (ICE+) —", classes="subsection_header")

        yield Label("Reason for attending (patient's own words):")
        yield TextArea(id="reason_for_attending", language="plain")

        yield YesNoField("Has understanding of cause", field_id="cause_understanding")

        yield Label("Understanding of cause (patient's explanation):")
        yield TextArea(id="cause_understanding_detail", language="plain")

        yield Label("Prognosis expectations (how long, how hopeful):")
        yield TextArea(id="prognosis_expectations", language="plain")

        yield Label("Treatment preference (what they expect will help):")
        yield TextArea(id="treatment_preference", language="plain")

        # Status indicator
        yield Label("", id="consent_status")

    def load(self, data: dict) -> None:
        """Load consent data into form fields."""
        self._loading = True

        try:
            # Cancel any pending save task
            # (not applicable here since we just created the section)

            # Load consent fields
            consent = data.get("consent", {}) if isinstance(data, dict) else {}

            # Consent checkboxes
            if "consent_to_proceed" in consent:
                yesno = self.query_one("#consent_to_proceed", YesNoField)
                yesno.set_value(consent["consent_to_proceed"])

            if "consent_sensitive_topics" in consent:
                yesno = self.query_one("#consent_sensitive_topics", YesNoField)
                yesno.set_value(consent["consent_sensitive_topics"])

            # Preferred name
            if "preferred_name" in consent:
                inp = self.query_one("#preferred_name_input", Input)
                inp.value = consent.get("preferred_name", "")

            # Session framing
            if "pain_multifactorial_explained" in consent:
                yesno = self.query_one("#framing_pain_multifactorial", YesNoField)
                yesno.set_value(consent["pain_multifactorial_explained"])

            if "education_as_treatment_explained" in consent:
                yesno = self.query_one("#framing_education_treatment", YesNoField)
                yesno.set_value(consent["education_as_treatment_explained"])

            if "patient_expectations" in consent:
                inp = self.query_one("#patient_expectations", Input)
                inp.value = consent.get("patient_expectations", "")

            # ICE+ fields
            if "reason_for_attending" in consent:
                ta = self.query_one("#reason_for_attending", TextArea)
                ta.text = consent.get("reason_for_attending", "")

            if "cause_understanding" in consent:
                yesno = self.query_one("#cause_understanding", YesNoField)
                yesno.set_value(consent["cause_understanding"])

            if "cause_understanding_detail" in consent:
                inp = self.query_one("#cause_understanding_detail", Input)
                inp.value = consent.get("cause_understanding_detail", "")

            if "prognosis_expectations" in consent:
                ta = self.query_one("#prognosis_expectations", TextArea)
                ta.text = consent.get("prognosis_expectations", "")

            if "treatment_preference" in consent:
                ta = self.query_one("#treatment_preference", TextArea)
                ta.text = consent.get("treatment_preference", "")

        finally:
            self._loading = False
            self._update_status()

    def collect(self) -> dict:
        """Collect all field values into a consent dict."""
        try:
            return {
                "consent_to_proceed": self.query_one("#consent_to_proceed", YesNoField).get_value(),
                "consent_sensitive_topics": self.query_one("#consent_sensitive_topics", YesNoField).get_value(),
                "preferred_name": self.query_one("#preferred_name_input", Input).value,
                "pain_multifactorial_explained": self.query_one("#framing_pain_multifactorial", YesNoField).get_value(),
                "education_as_treatment_explained": self.query_one("#framing_education_treatment", YesNoField).get_value(),
                "patient_expectations": self.query_one("#patient_expectations", Input).value,
                "reason_for_attending": self.query_one("#reason_for_attending", TextArea).text,
                "cause_understanding": self.query_one("#cause_understanding", YesNoField).get_value(),
                "cause_understanding_detail": self.query_one("#cause_understanding_detail", Input).value,
                "prognosis_expectations": self.query_one("#prognosis_expectations", TextArea).text,
                "treatment_preference": self.query_one("#treatment_preference", TextArea).text,
            }
        except Exception:
            # Widget not yet mounted, return empty dict
            return {}

    def is_complete(self) -> bool:
        """Section complete when: consent_to_proceed is True AND preferred_name is non-empty."""
        data = self.collect()
        return (
            data.get("consent_to_proceed") is True
            and bool(data.get("preferred_name", "").strip())
        )

    def _update_status(self) -> None:
        """Update the status label."""
        try:
            label = self.query_one("#consent_status", Label)
            if self.is_complete():
                label.update("✓ Consent section complete")
            else:
                label.update("")
        except Exception:
            # Widget not yet mounted
            pass

    @on(YesNoField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        """Handle field changes — update status and signal parent to save."""
        if self._loading:
            return

        self._update_status()

        # Emit a message for the parent view to handle saving
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        """Message emitted when a field changes."""
        pass
