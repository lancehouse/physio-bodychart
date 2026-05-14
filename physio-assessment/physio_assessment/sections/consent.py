"""Consent & Session Setup section (core/01)."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Input, TextArea

from .base import BaseSection
from ..widgets import CheckButton


class ConsentSection(BaseSection):
    """Consent & Session Setup."""

    DEFAULT_CSS = """
    ConsentSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title {
        text-style: bold;
        color: $text;
        margin-bottom: 0;
    }

    .subsection_header {
        text-style: bold;
        color: $primary;
        margin-top: 1;
        margin-bottom: 0;
    }

    /* Paired toggle button rows */
    .btn_row {
        height: auto;
        width: 100%;
        margin-bottom: 1;
    }

    CheckButton {
        width: auto;
        height: 3;
        min-width: 18;
        margin: 0 1 0 0;
    }

    .solo_btn {
        margin-bottom: 0;
    }

    /* Label + field on one horizontal row — no gap between rows */
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

    #consent_status {
        color: $success;
        text-style: bold;
        margin-top: 0;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Consent & Session Setup", classes="section_title")

        yield Label("— Consent —", classes="subsection_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Consent to proceed", id="consent_to_proceed")
            yield CheckButton("Consent to sensitive topics", id="consent_sensitive_topics")

        with Horizontal(classes="field_row"):
            yield Label("Preferred name\n(required):")
            yield Input(id="preferred_name_input", placeholder="patient's preferred name")

        yield Label("— Session Framing —", classes="subsection_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Pain multifactorial explained", id="framing_pain_multifactorial")
            yield CheckButton("Education as treatment explained", id="framing_education_treatment")

        with Horizontal(classes="field_row"):
            yield Label("Patient expectations\nof this session:")
            yield TextArea(id="patient_expectations", language="plain")

        yield Label("— Patient Perspective (ICE+) —", classes="subsection_header")

        with Horizontal(classes="field_row"):
            yield Label("Reason for attending\n(patient's own words):")
            yield TextArea(id="reason_for_attending", language="plain")

        yield CheckButton("Has understanding of cause", id="cause_understanding", classes="solo_btn")

        with Horizontal(classes="field_row"):
            yield Label("Patient's understanding\nof cause:")
            yield TextArea(id="cause_understanding_detail", language="plain")

        with Horizontal(classes="field_row"):
            yield Label("Prognosis expectations\n(timeline & hope):")
            yield TextArea(id="prognosis_expectations", language="plain")

        with Horizontal(classes="field_row"):
            yield Label("Treatment preference\n(what will help them):")
            yield TextArea(id="treatment_preference", language="plain")

        yield Label("", id="consent_status")

    def load(self, data: dict) -> None:
        """Load consent data into form fields."""
        self._loading = True
        try:
            consent = data if isinstance(data, dict) else {}

            if "consent_to_proceed" in consent:
                self.query_one("#consent_to_proceed", CheckButton).set_value(consent["consent_to_proceed"])
            if "consent_sensitive_topics" in consent:
                self.query_one("#consent_sensitive_topics", CheckButton).set_value(consent["consent_sensitive_topics"])
            if "preferred_name" in consent:
                self.query_one("#preferred_name_input", Input).value = consent.get("preferred_name", "")
            if "pain_multifactorial_explained" in consent:
                self.query_one("#framing_pain_multifactorial", CheckButton).set_value(consent["pain_multifactorial_explained"])
            if "education_as_treatment_explained" in consent:
                self.query_one("#framing_education_treatment", CheckButton).set_value(consent["education_as_treatment_explained"])
            if "patient_expectations" in consent:
                self.query_one("#patient_expectations", TextArea).text = consent.get("patient_expectations", "")
            if "reason_for_attending" in consent:
                self.query_one("#reason_for_attending", TextArea).text = consent.get("reason_for_attending", "")
            if "cause_understanding" in consent:
                self.query_one("#cause_understanding", CheckButton).set_value(consent["cause_understanding"])
            if "cause_understanding_detail" in consent:
                self.query_one("#cause_understanding_detail", TextArea).text = consent.get("cause_understanding_detail", "")
            if "prognosis_expectations" in consent:
                self.query_one("#prognosis_expectations", TextArea).text = consent.get("prognosis_expectations", "")
            if "treatment_preference" in consent:
                self.query_one("#treatment_preference", TextArea).text = consent.get("treatment_preference", "")
        finally:
            self._loading = False
            self._update_status()

    def collect(self) -> dict:
        """Collect all field values — keys must match _assessment.json schema."""
        try:
            return {
                "consent_to_proceed": self.query_one("#consent_to_proceed", CheckButton).value,
                "consent_sensitive_topics": self.query_one("#consent_sensitive_topics", CheckButton).value,
                "preferred_name": self.query_one("#preferred_name_input", Input).value,
                "pain_multifactorial_explained": self.query_one("#framing_pain_multifactorial", CheckButton).value,
                "education_as_treatment_explained": self.query_one("#framing_education_treatment", CheckButton).value,
                "patient_expectations": self.query_one("#patient_expectations", TextArea).text,
                "reason_for_attending": self.query_one("#reason_for_attending", TextArea).text,
                "cause_understanding": self.query_one("#cause_understanding", CheckButton).value,
                "cause_understanding_detail": self.query_one("#cause_understanding_detail", TextArea).text,
                "prognosis_expectations": self.query_one("#prognosis_expectations", TextArea).text,
                "treatment_preference": self.query_one("#treatment_preference", TextArea).text,
            }
        except Exception:
            return {}

    def is_complete(self) -> bool:
        data = self.collect()
        return (
            data.get("consent_to_proceed") is True
            and bool(data.get("preferred_name", "").strip())
        )

    def _update_status(self) -> None:
        try:
            label = self.query_one("#consent_status", Label)
            label.update("✓ Consent section complete" if self.is_complete() else "")
        except Exception:
            pass

    @on(CheckButton.Changed)
    @on(Input.Changed)
    @on(TextArea.Changed)
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._update_status()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
