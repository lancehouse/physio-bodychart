"""Rx & Treatment Plan — F9 (split from Barriers)."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal, ScrollableContainer
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from .base import BaseSection
from ..widgets import CheckButton
from .outcome_measures import CycleField


# ---------------------------------------------------------------------------
# Option lists
# ---------------------------------------------------------------------------

_PAIN_TYPE_OPTIONS = [
    ("1 — Nociceptive / Neuropathic", "primary"),
    ("2 — Nociplastic",               "warning"),
]

_DEBUNK_OPTIONS = [
    ("Yes", "success"),
    ("No",  "error"),
    ("N/A", "default"),
]


# ---------------------------------------------------------------------------
# Field lists for collect / load
# ---------------------------------------------------------------------------

# Toggle fields: all CheckButton IDs in this section
_TOGGLE_FIELDS = [
    "tx_consent_explanation", "s1_consent_content", "tx_email_obtained", "tx_display_book",
    "hw_online_module", "hw_mindfulness", "hw_goal_sheet", "hw_activity_diary", "hw_sleep_diary",
    "d1_explanation", "d1_session2", "d1_hypothesis", "d1_diagnosis", "d1_values",
    "d1_evidence", "d1_plan", "d1_prognosis", "d1_stakeholders", "d1_confidence_tested",
    "d1_questionnaires",
    "ps_questionnaires", "ps_eppoc", "ps_ptsd_scored", "ps_isi_pbas", "ps_csi", "ps_audit_dudit",
]

# Note Input IDs — one per toggle field, same order
_NOTE_FIELDS = [f"{fid}_note" for fid in _TOGGLE_FIELDS]

_CYCLE_FIELDS = ["tx_pain_type", "tx_debunk_radiology"]

_INPUT_FIELDS = ["s1_confidence_nrs", "fu_om_schedule"]

_TEXT_FIELDS = [
    "tx_goal_orientation", "tx_formulation",
    "tx_program", "tx_home_program",
    "tx_psychosocial", "tx_medical", "tx_rtw",
    "s1_education", "s1_experiential", "s1_hw_other",
    "fu_next_focus", "fu_monitoring",
]

# Row definitions — (CheckButton label, field_id)
_CONSENT_ITEMS = [
    ("Consent to discuss explanation", "tx_consent_explanation"),
    ("Consent to discuss content",     "s1_consent_content"),
    ("Email obtained for resources",   "tx_email_obtained"),
    ("Patient display book provided",  "tx_display_book"),
]

_HW_ITEMS = [
    ("Online module — questions / reflections",  "hw_online_module"),
    ("Mindfulness / experiential practice",      "hw_mindfulness"),
    ("Goal sheet",                               "hw_goal_sheet"),
    ("Activity diary",                           "hw_activity_diary"),
    ("Sleep diary",                              "hw_sleep_diary"),
]

_D1_ITEMS = [
    ("Clear and simple explanation delivered",                  "d1_explanation"),
    ("Importance of Session 2 communicated",                    "d1_session2"),
    ("Complexity and hypothesis testing articulated",           "d1_hypothesis"),
    ("Diagnosis and formulation provided (implies pain type)",  "d1_diagnosis"),
    ("Patient values / preferences / goals articulated",       "d1_values"),
    ("Evidence discussed (ePPOC and RCTs referenced)",         "d1_evidence"),
    ("Short and long term plan provided",                       "d1_plan"),
    ("Prognosis and prevention discussed",                      "d1_prognosis"),
    ("Other stakeholders identified",                           "d1_stakeholders"),
    ("Confidence / understanding tested",                       "d1_confidence_tested"),
    ("Questionnaires administered (individualised set)",        "d1_questionnaires"),
]

_PS_ITEMS = [
    ("Questionnaires scored",                          "ps_questionnaires"),
    ("ePPOC components completed",                     "ps_eppoc"),
    ("PTSD screen scored (if administered)",           "ps_ptsd_scored"),
    ("ISI and PBAS scored (if sleep primary problem)", "ps_isi_pbas"),
    ("CSI scored",                                     "ps_csi"),
    ("AUDIT / DUDIT scored (if administered)",         "ps_audit_dudit"),
]


# ---------------------------------------------------------------------------
# RxPlanSection
# ---------------------------------------------------------------------------

class RxPlanSection(BaseSection):
    """09 Rx & Plan — treatment plan, session 1, day 1 checklist, follow-up."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    RxPlanSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    RxPlanSection .section_title  { text-style: bold; margin-bottom: 0; }
    RxPlanSection .reference_note { color: $text-muted; margin-bottom: 0; }

    /* field_row: fixed label left + TextArea / Input right */
    RxPlanSection .field_row { layout: horizontal; height: auto; width: 100%; margin-bottom: 0; }
    RxPlanSection .field_lbl { width: 28; height: auto; content-align: left top; padding-top: 1; }
    RxPlanSection .field_inp { width: 1fr; height: auto; }

    /* stmt_row: CheckButton (statement label, text-fitted left) + Input note (1fr right).
       Width is set per-widget in on_mount() — intentionally breaks the 25% rule here. */
    RxPlanSection .stmt_row  { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    RxPlanSection .stmt_btn  { height: 3; min-width: 0; padding: 0 1; }
    RxPlanSection .stmt_note { width: 1fr; height: 3; }

    RxPlanSection TextArea { height: auto; min-height: 3; padding: 0 1; }
    RxPlanSection Input    { height: 3; }
    RxPlanSection Label    { height: auto; margin-top: 0; }
    """

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("09 Rx & Plan", classes="section_title")

        # ── Treatment Plan Summary ─────────────────────────────────────────────
        yield Label("— Treatment Plan Summary —", classes="subsection_header", id="rp_treatment")

        with Horizontal(classes="field_row"):
            yield Label("Education — pain type:", classes="field_lbl")
            yield CycleField("tx_pain_type", _PAIN_TYPE_OPTIONS)
        with Horizontal(classes="field_row"):
            yield Label("Debunk radiology (nociplastic):", classes="field_lbl")
            yield CycleField("tx_debunk_radiology", _DEBUNK_OPTIONS)
        with Horizontal(classes="field_row"):
            yield Label("Goal orientation:", classes="field_lbl")
            yield TextArea(id="tx_goal_orientation", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Formulation:", classes="field_lbl")
            yield TextArea(id="tx_formulation", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Exercise / Rehab program:", classes="field_lbl")
            yield TextArea(id="tx_program", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Home program:", classes="field_lbl")
            yield TextArea(id="tx_home_program", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Psychosocial strategies:", classes="field_lbl")
            yield TextArea(id="tx_psychosocial", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Medical / Referral:", classes="field_lbl")
            yield TextArea(id="tx_medical", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("RTW plan:", classes="field_lbl")
            yield TextArea(id="tx_rtw", language="plain", classes="field_inp")

        # Consent / admin toggles
        for label, fid in _CONSENT_ITEMS[:2]:
            with Horizontal(classes="stmt_row"):
                yield CheckButton(label, id=fid, classes="stmt_btn")
                yield Input(placeholder="notes", id=f"{fid}_note", classes="stmt_note")

        # ── Session 1 Treatment ────────────────────────────────────────────────
        yield Label("— Session 1 Treatment —", classes="subsection_header", id="rp_session1")
        yield Label(
            "(Consider: (1) Specialist treatment; (2) Monitor by others; (3) Referral)",
            classes="reference_note",
        )

        with Horizontal(classes="field_row"):
            yield Label("Education provided:", classes="field_lbl")
            yield TextArea(id="s1_education", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Experiential treatment:", classes="field_lbl")
            yield TextArea(id="s1_experiential", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Confidence NRS (0–10):", classes="field_lbl")
            yield Input(id="s1_confidence_nrs", placeholder="0–10", classes="field_inp")

        yield Label("Homework set:")
        for label, fid in _HW_ITEMS:
            with Horizontal(classes="stmt_row"):
                yield CheckButton(label, id=fid, classes="stmt_btn")
                yield Input(placeholder="notes", id=f"{fid}_note", classes="stmt_note")
        with Horizontal(classes="field_row"):
            yield Label("Other homework:", classes="field_lbl")
            yield TextArea(id="s1_hw_other", language="plain", classes="field_inp")

        for label, fid in _CONSENT_ITEMS[2:]:
            with Horizontal(classes="stmt_row"):
                yield CheckButton(label, id=fid, classes="stmt_btn")
                yield Input(placeholder="notes", id=f"{fid}_note", classes="stmt_note")

        # ── Day 1 Checklist ────────────────────────────────────────────────────
        yield Label("— Day 1 Checklist —", classes="subsection_header", id="rp_day1")

        for label, fid in _D1_ITEMS:
            with Horizontal(classes="stmt_row"):
                yield CheckButton(label, id=fid, classes="stmt_btn")
                yield Input(placeholder="notes", id=f"{fid}_note", classes="stmt_note")

        # ── Follow-Up Plan ─────────────────────────────────────────────────────
        yield Label("— Follow-Up Plan —", classes="subsection_header", id="rp_followup")

        with Horizontal(classes="field_row"):
            yield Label("Next session focus:", classes="field_lbl")
            yield TextArea(id="fu_next_focus", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("Monitoring:", classes="field_lbl")
            yield TextArea(id="fu_monitoring", language="plain", classes="field_inp")
        with Horizontal(classes="field_row"):
            yield Label("OM re-testing schedule:", classes="field_lbl")
            yield Input(id="fu_om_schedule", placeholder="schedule", classes="field_inp")

        yield Label("Post-Session Admin:")
        for label, fid in _PS_ITEMS:
            with Horizontal(classes="stmt_row"):
                yield CheckButton(label, id=fid, classes="stmt_btn")
                yield Input(placeholder="notes", id=f"{fid}_note", classes="stmt_note")

    # ------------------------------------------------------------------
    # Dynamic button sizing
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Set each statement CheckButton to exactly fit its label + ' Yes' + padding."""
        all_stmt = _CONSENT_ITEMS + _HW_ITEMS + _D1_ITEMS + _PS_ITEMS
        for label, fid in all_stmt:
            try:
                btn = self.query_one(f"#{fid}", CheckButton)
                # len(label) + len(" Yes") + 1 cell padding each side
                btn.styles.width = len(label) + 6
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(
                target, top=True, animate=False
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(CheckButton.Changed)
    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if not self._loading:
            self.post_message(self.FieldChanged())

    # ------------------------------------------------------------------
    # collect / load / is_complete
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data: dict = {}
        for fid in _TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
            except Exception:
                data[fid] = None
        for nid in _NOTE_FIELDS:
            try:
                data[nid] = self.query_one(f"#{nid}", Input).value
            except Exception:
                data[nid] = ""
        for fid in _CYCLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CycleField).get_value()
            except Exception:
                data[fid] = None
        for fid in _INPUT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", Input).value
            except Exception:
                data[fid] = ""
        for fid in _TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            rp = data if isinstance(data, dict) else {}
            for fid in _TOGGLE_FIELDS:
                if fid in rp:
                    try:
                        self.query_one(f"#{fid}", CheckButton).set_value(rp[fid])
                    except Exception:
                        pass
            for nid in _NOTE_FIELDS:
                if nid in rp:
                    try:
                        self.query_one(f"#{nid}", Input).value = rp[nid]
                    except Exception:
                        pass
            for fid in _CYCLE_FIELDS:
                if fid in rp:
                    try:
                        self.query_one(f"#{fid}", CycleField).set_value(rp[fid])
                    except Exception:
                        pass
            for fid in _INPUT_FIELDS:
                if fid in rp:
                    try:
                        self.query_one(f"#{fid}", Input).value = rp[fid]
                    except Exception:
                        pass
            for fid in _TEXT_FIELDS:
                if fid in rp:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = rp[fid]
                    except Exception:
                        pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#tx_pain_type", CycleField).get_value() is not None
        except Exception:
            return False
