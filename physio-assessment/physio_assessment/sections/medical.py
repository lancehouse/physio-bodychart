"""Medical Screening section (core/03)."""

from textual.app import ComposeResult, on
from textual.containers import Vertical, ScrollableContainer, Horizontal
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from .consent import YesNoField


# ---------------------------------------------------------------------------
# Module-level medication column definitions (shared by MedRow + MedicalSection)
# ---------------------------------------------------------------------------

_MED_COLS        = ["name",          "dose",  "timing",             "comments"]
_MED_COL_LABELS  = ["Name / brand",  "Dose",  "Timing / frequency", "Comments"]
_MED_COL_CLASSES = ["med_col_name",  "med_col_dose", "med_col_timing", "med_col_comments"]


class MedRow(Horizontal):
    """One row in the medications table — composed on mount."""

    def __init__(self, row_idx: int, **kwargs):
        super().__init__(**kwargs)
        self._row_idx = row_idx

    def compose(self) -> ComposeResult:
        for col, css_class in zip(_MED_COLS, _MED_COL_CLASSES):
            yield Input(id=f"med_{self._row_idx}_{col}", classes=css_class, placeholder="")


# ---------------------------------------------------------------------------
# YesNoField with CLINICAL colour logic: YES=red (bad), NO=green (safe)
# This subclass is for red flag / screening fields only.
# ---------------------------------------------------------------------------

class RedFlagField(YesNoField):
    """YES/NO toggle where YES is danger (red) and NO is safe (green)."""

    def set_value(self, value: bool | None) -> None:
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_toggle", Button)
            if value is True:
                btn.label = "YES"
                btn.variant = "error"      # red — positive finding
            elif value is False:
                btn.label = "NO"
                btn.variant = "success"    # green — cleared
            else:
                btn.label = "?"
                btn.variant = "primary"
        except Exception:
            pass


# ---------------------------------------------------------------------------
# LikelihoodField
# ---------------------------------------------------------------------------

class LikelihoodField(Static):
    """Label + cycling button: None → Low → Moderate → High → None."""

    DEFAULT_CSS = """
    LikelihoodField {
        height: auto;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    LikelihoodField > Label {
        width: 1fr;
        margin-bottom: 0;
        padding-right: 1;
    }
    LikelihoodField Button {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 2;
    }
    """

    _CYCLE = [None, "Low", "Moderate", "High"]
    _VARIANTS = {None: "primary", "Low": "success", "Moderate": "warning", "High": "error"}

    def __init__(self, label: str, field_id: str, **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._label = label
        self._field_id = field_id
        self._value = None

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Button("?", id=f"{self._field_id}_btn", variant="primary")

    def get_value(self) -> str | None:
        return self._value

    def set_value(self, value: str | None) -> None:
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_btn", Button)
            btn.label = value if value else "?"
            btn.variant = self._VARIANTS.get(value, "primary")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_btn":
            idx = self._CYCLE.index(self._value)
            self.set_value(self._CYCLE[(idx + 1) % len(self._CYCLE)])
            self.post_message(LikelihoodField.Changed())
            event.stop()

    class Changed(Message):
        pass


# ---------------------------------------------------------------------------
# MedNavBar
# ---------------------------------------------------------------------------

class MedNavBar(Static):
    """Fixed top navigation bar for Medical Screening section."""

    SUBSECTIONS = [
        ("Comorbid",     "med_comorbidities"),
        ("CVD Risk",     "med_cardiovascular"),
        ("Red Flags",    "med_red_flags"),
        ("Differential", "med_differential"),
        ("Medications",  "med_medications"),
    ]

    DEFAULT_CSS = """
    MedNavBar {
        width: 100%;
        height: auto;
        background: $boost;
        border-bottom: solid $primary;
        padding: 0;
        layout: horizontal;
    }
    MedNavBar Button {
        width: auto;
        height: auto;
        min-width: 0;
        padding: 0 1;
        border: none;
        background: $boost;
    }
    MedNavBar Button:hover {
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
# MedicalSection
# ---------------------------------------------------------------------------

class MedicalSection(BaseSection):
    """Medical Screening section (core/03).

    UI and data are deliberately separated:
    - compose() / CSS control layout only
    - collect() / load() reference widget IDs, not layout structure
    """

    DEFAULT_CSS = """
    MedicalSection {
        width: 100%;
        height: 100%;
        layout: vertical;
        padding: 0;
    }

    #med_nav {
        height: auto;
    }

    #med_scroll {
        width: 100%;
        height: 1fr;
    }

    #med_content {
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

    .subgroup_header {
        color: $text-muted;
        padding-top: 1;
        margin-bottom: 0;
        text-style: italic;
    }

    TextArea, Input {
        height: auto;
        min-height: 1;
        margin-bottom: 0;
    }

    Label {
        margin-bottom: 0;
    }

    #med_rf_alert {
        width: 100%;
        padding: 0 1;
        text-style: bold;
        margin-bottom: 0;
    }

    #med_rf_alert.rf_warning {
        color: $warning;
        background: $warning 20%;
    }

    #med_rf_alert.rf_urgent {
        color: $error;
        background: $error 20%;
    }

    /* Medications table */
    .med_header_row {
        height: auto;
        padding-top: 1;
        margin-bottom: 0;
    }

    .med_header_row Label {
        text-style: bold;
        color: $text-muted;
        margin-bottom: 0;
        padding: 0 1;
    }

    .med_row {
        height: auto;
        margin-bottom: 0;
    }

    .med_row Input {
        height: auto;
        min-height: 1;
        margin-bottom: 0;
    }

    .med_col_name     { width: 3fr; }
    .med_col_dose     { width: 2fr; }
    .med_col_timing   { width: 2fr; }
    .med_col_comments { width: 5fr; }
    """

    _RF_GENERAL = [
        "rf_weight_loss", "rf_cancer_history", "rf_age_50_spinal", "rf_failed_conservative",
        "rf_trauma", "rf_corticosteroids_fracture", "rf_osteoporosis_fracture",
        "rf_fever", "rf_immunosuppressed", "rf_spinal_procedure",
        "umn_hyperreflexia", "umn_babinski", "umn_clonus", "umn_romberg", "umn_coordination",
    ]
    _RF_URGENT_CAUDA = ["rf_saddle_anaesthesia", "rf_bladder_disturbance", "rf_bowel_disturbance"]
    _RF_URGENT_CORD  = ["rf_bilateral_paraesthesia", "rf_gait_disturbance"]

    # All red-flag fields use RedFlagField (YES=red, NO=green)
    _RED_FLAG_TOGGLE_FIELDS = (
        _RF_GENERAL + _RF_URGENT_CAUDA + _RF_URGENT_CORD
    )

    _TOGGLE_FIELDS = [
        "no_previous_injuries",
        "comorbid_cancer", "comorbid_mental_health", "comorbid_osteoporosis",
        "comorbid_inflammatory", "comorbid_fibromyalgia", "comorbid_cfs",
        "comorbid_ibs", "comorbid_whiplash", "comorbid_skin_rash",
        "comorbid_drug_alcohol", "comorbid_fatigue_memory",
        "cvd_hypercholesterolaemia", "cvd_cardiac", "cvd_vascular",
        "cvd_stroke_tia", "cvd_diabetes", "cvd_corticosteroids",
        "cvd_clotting", "cvd_ocp", "cvd_smoker", "cvd_postpartum",
        "cvd_familial_history",
        # red flags (use RedFlagField in compose, but same save/load logic)
        "rf_weight_loss", "rf_cancer_history", "rf_age_50_spinal", "rf_failed_conservative",
        "rf_trauma", "rf_corticosteroids_fracture", "rf_osteoporosis_fracture",
        "rf_fever", "rf_immunosuppressed", "rf_spinal_procedure",
        "rf_saddle_anaesthesia", "rf_bladder_disturbance", "rf_bowel_disturbance",
        "rf_bilateral_paraesthesia", "rf_gait_disturbance",
        "umn_hyperreflexia", "umn_babinski", "umn_clonus", "umn_romberg", "umn_coordination",
        "diff_as_insidious", "diff_as_lumbar_sij", "diff_as_inflammatory",
        "diff_as_breathing", "diff_as_fever_weight_loss",
        "diff_aaa_pulsating", "diff_aaa_age_50", "diff_aaa_cvd_risk", "diff_aaa_ruptured",
        "diff_vc_non_dermatomal", "diff_vc_age_50", "diff_vc_cvd_risk",
        "diff_vc_walking_pain", "diff_vc_pvd_signs", "diff_vc_impotence", "diff_vc_night_pain",
    ]

    _LIKELIHOOD_FIELDS = ["diff_as_likelihood", "diff_aaa_likelihood", "diff_vc_likelihood"]

    _TEXT_FIELDS = [
        "previous_injuries", "comorbid_other",
        "cauda_equina_action", "spinal_cord_action", "umn_interpretation",
        "diff_as_action", "diff_aaa_action", "diff_vc_action",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._med_row_count = 4

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _rf(self, label: str, field_id: str) -> RedFlagField:
        """Shorthand: yield a RedFlagField (YES=red, NO=green)."""
        return RedFlagField(label, field_id=field_id)

    def compose(self) -> ComposeResult:
        yield MedNavBar(on_jump_to=self._jump_to, id="med_nav")

        with ScrollableContainer(id="med_scroll"):
            with Vertical(id="med_content"):
                yield Label("Medical Screening", classes="section_title")

                # ── Comorbidities / PMH ──────────────────────────────────
                yield Label("— Comorbidities / PMH —", classes="subsection_header", id="med_comorbidities")
                yield YesNoField("No previous injuries or general health issues: Confirmed", field_id="no_previous_injuries")
                yield Label("Previous injuries:")
                yield TextArea(id="previous_injuries", language="plain")
                yield Label("Comorbidities present:")
                yield YesNoField("Cancer (current or history)",               field_id="comorbid_cancer")
                yield YesNoField("Mental health condition",                   field_id="comorbid_mental_health")
                yield YesNoField("Osteoporosis",                              field_id="comorbid_osteoporosis")
                yield YesNoField("Systemic inflammatory condition",           field_id="comorbid_inflammatory")
                yield YesNoField("Fibromyalgia",                              field_id="comorbid_fibromyalgia")
                yield YesNoField("Chronic fatigue syndrome",                  field_id="comorbid_cfs")
                yield YesNoField("Irritable bowel syndrome",                  field_id="comorbid_ibs")
                yield YesNoField("Chronic whiplash",                          field_id="comorbid_whiplash")
                yield YesNoField("Painful skin rash",                         field_id="comorbid_skin_rash")
                yield YesNoField("Drug or alcohol issues",                    field_id="comorbid_drug_alcohol")
                yield YesNoField("Fatigue / concentration / memory issues",   field_id="comorbid_fatigue_memory")
                yield Label("Other:")
                yield TextArea(id="comorbid_other", language="plain")

                # ── Cardiovascular Risk Factors ─────────────────────────
                yield Label("— Cardiovascular Risk Factors —", classes="subsection_header", id="med_cardiovascular")
                yield YesNoField("Hypercholesterolaemia / hyperlipidaemia",   field_id="cvd_hypercholesterolaemia")
                yield YesNoField("Cardiac disease",                           field_id="cvd_cardiac")
                yield YesNoField("Vascular disease",                          field_id="cvd_vascular")
                yield YesNoField("Previous stroke / TIA",                     field_id="cvd_stroke_tia")
                yield YesNoField("Diabetes",                                  field_id="cvd_diabetes")
                yield YesNoField("Prolonged corticosteroid use",              field_id="cvd_corticosteroids")
                yield YesNoField("Blood clotting disorders",                  field_id="cvd_clotting")
                yield YesNoField("Oral contraceptives",                       field_id="cvd_ocp")
                yield YesNoField("Smoker",                                    field_id="cvd_smoker")
                yield YesNoField("Immediately post-partum",                   field_id="cvd_postpartum")
                yield YesNoField("Familial history of presenting condition",  field_id="cvd_familial_history")

                # ── Red Flags ────────────────────────────────────────────
                yield Label("— Red Flags —", classes="subsection_header", id="med_red_flags")
                yield Static("", id="med_rf_alert")

                yield Label("Malignancy:", classes="subgroup_header")
                yield self._rf("Unexplained weight loss",                         "rf_weight_loss")
                yield self._rf("History of cancer",                               "rf_cancer_history")
                yield self._rf("Age >50 with new spinal pain",                    "rf_age_50_spinal")
                yield self._rf("Failure to improve with conservative treatment",  "rf_failed_conservative")

                yield Label("Fracture:", classes="subgroup_header")
                yield self._rf("Significant trauma",            "rf_trauma")
                yield self._rf("Prolonged corticosteroid use",  "rf_corticosteroids_fracture")
                yield self._rf("Osteoporosis confirmed",        "rf_osteoporosis_fracture")

                yield Label("Infection:", classes="subgroup_header")
                yield self._rf("Fever",                                        "rf_fever")
                yield self._rf("Immunosuppressive disease or medication",      "rf_immunosuppressed")
                yield self._rf("Recent spinal procedure",                      "rf_spinal_procedure")

                yield Label("Cauda Equina Compression (URGENT):", classes="subgroup_header")
                yield self._rf("Saddle anaesthesia / perineal symptoms",  "rf_saddle_anaesthesia")
                yield self._rf("Disturbance of bladder function",         "rf_bladder_disturbance")
                yield self._rf("Disturbance of bowel function",           "rf_bowel_disturbance")
                yield Label("Action taken if positive:")
                yield TextArea(id="cauda_equina_action", language="plain")

                yield Label("Spinal Cord Compression (URGENT):", classes="subgroup_header")
                yield self._rf("Bilateral paraesthesia / weakness / sensation changes",  "rf_bilateral_paraesthesia")
                yield self._rf("Gait or balance disturbance",                           "rf_gait_disturbance")
                yield Label("Action taken if positive:")
                yield TextArea(id="spinal_cord_action", language="plain")

                yield Label("Upper Motor Neurone Signs:", classes="subgroup_header")
                yield self._rf("Hyperreflexia (ankle jerk bilaterally)",                       "umn_hyperreflexia")
                yield self._rf("Positive Babinski reflex (upgoing plantars)",                  "umn_babinski")
                yield self._rf("Clonus (calf bilaterally)",                                    "umn_clonus")
                yield self._rf("Impaired balance on Romberg's test",                           "umn_romberg")
                yield self._rf("Impaired coordination (finger-nose, alternating, heel-shin)",  "umn_coordination")
                yield Label("Interpretation:")
                yield TextArea(id="umn_interpretation", language="plain")

                # ── Differential Screening ───────────────────────────────
                yield Label("— Differential Screening —", classes="subsection_header", id="med_differential")

                yield Label("Ankylosing Spondylitis:", classes="subgroup_header")
                yield YesNoField("Insidious onset",                          field_id="diff_as_insidious")
                yield YesNoField("Lumbar / SIJ progressing to other areas",  field_id="diff_as_lumbar_sij")
                yield YesNoField("Inflammatory symptom pattern",             field_id="diff_as_inflammatory")
                yield YesNoField("Breathing difficulties",                   field_id="diff_as_breathing")
                yield YesNoField("Fever / weight loss",                      field_id="diff_as_fever_weight_loss")
                yield LikelihoodField("Likelihood:", field_id="diff_as_likelihood")
                yield Label("Action:")
                yield TextArea(id="diff_as_action", language="plain")

                yield Label("Abdominal Aortic Aneurysm:", classes="subgroup_header")
                yield YesNoField("Pulsating lumbar / groin pain",               field_id="diff_aaa_pulsating")
                yield YesNoField("Age >50",                                     field_id="diff_aaa_age_50")
                yield YesNoField("Cardiovascular risk factors present",         field_id="diff_aaa_cvd_risk")
                yield YesNoField("Sudden onset with low BP / shock (ruptured)", field_id="diff_aaa_ruptured")
                yield LikelihoodField("Likelihood:", field_id="diff_aaa_likelihood")
                yield Label("Action:")
                yield TextArea(id="diff_aaa_action", language="plain")

                yield Label("Vascular Claudication:", classes="subgroup_header")
                yield YesNoField("Non-dermatomal leg symptoms",                               field_id="diff_vc_non_dermatomal")
                yield YesNoField("Age >50",                                                   field_id="diff_vc_age_50")
                yield YesNoField("Cardiovascular risk factors",                               field_id="diff_vc_cvd_risk")
                yield YesNoField("Pain / burning / fatigue with walking, relieved by rest",  field_id="diff_vc_walking_pain")
                yield YesNoField("Peripheral vascular signs (cold, blotchy, shiny, hairless skin)", field_id="diff_vc_pvd_signs")
                yield YesNoField("Impotence in men",                                         field_id="diff_vc_impotence")
                yield YesNoField("Leg pain at night",                                        field_id="diff_vc_night_pain")
                yield LikelihoodField("Likelihood:", field_id="diff_vc_likelihood")
                yield Label("Action:")
                yield TextArea(id="diff_vc_action", language="plain")

                # ── Medications ──────────────────────────────────────────
                yield Label("— Medications —", classes="subsection_header", id="med_medications")
                with Horizontal(classes="med_header_row"):
                    for lbl, css in zip(_MED_COL_LABELS, _MED_COL_CLASSES):
                        yield Label(lbl, classes=css)
                with Vertical(id="med_table"):
                    for i in range(4):
                        yield MedRow(i, classes="med_row")

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.query_one("#med_scroll", ScrollableContainer).scroll_to_widget(target, top=True)
        except Exception:
            pass

    def _update_rf_alert(self) -> None:
        try:
            alert = self.query_one("#med_rf_alert", Static)
            urgent_cauda = any(
                self.query_one(f"#{fid}", RedFlagField).get_value() is True
                for fid in self._RF_URGENT_CAUDA
            )
            urgent_cord = any(
                self.query_one(f"#{fid}", RedFlagField).get_value() is True
                for fid in self._RF_URGENT_CORD
            )
            general_rf = any(
                self.query_one(f"#{fid}", RedFlagField).get_value() is True
                for fid in self._RF_GENERAL
            )
            if urgent_cauda:
                alert.update("⚠ URGENT: Cauda equina symptoms — document action below")
                alert.remove_class("rf_warning")
                alert.add_class("rf_urgent")
                alert.display = True
            elif urgent_cord:
                alert.update("⚠ URGENT: Spinal cord compression signs — document action below")
                alert.remove_class("rf_warning")
                alert.add_class("rf_urgent")
                alert.display = True
            elif general_rf:
                alert.update("⚠ Red flag(s) positive — clinical judgement required")
                alert.remove_class("rf_urgent")
                alert.add_class("rf_warning")
                alert.display = True
            else:
                alert.display = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Dynamic medication rows
    # ------------------------------------------------------------------

    def _add_medication_row(self) -> None:
        i = self._med_row_count
        try:
            self.query_one("#med_table", Vertical).mount(MedRow(i, classes="med_row"))
            self._med_row_count += 1
        except Exception:
            pass

    def _focus_med_input(self, row: int) -> None:
        try:
            self.query_one(f"#med_{row}_{_MED_COLS[0]}", Input).focus()
        except Exception:
            pass

    def _load_extra_meds(self, meds: list, start: int) -> None:
        self._loading = True
        try:
            for i in range(start, min(len(meds), self._med_row_count)):
                med = meds[i]
                for col in _MED_COLS:
                    try:
                        self.query_one(f"#med_{i}_{col}", Input).value = med.get(col, "")
                    except Exception:
                        pass
        finally:
            self._loading = False

    def on_key(self, event) -> None:
        if event.key != "tab":
            return
        focused = self.app.focused
        if focused is None:
            return
        last = self._med_row_count - 1
        if focused.id == f"med_{last}_{_MED_COLS[-1]}":
            self._add_medication_row()
            new_row = self._med_row_count - 1
            self.set_timer(0.05, lambda: self._focus_med_input(new_row))

    # ------------------------------------------------------------------
    # Data — independent of UI structure
    # ------------------------------------------------------------------

    def _get_toggle_widget(self, fid: str):
        """Return the correct widget type for a toggle field ID."""
        if fid in self._RED_FLAG_TOGGLE_FIELDS:
            return self.query_one(f"#{fid}", RedFlagField)
        return self.query_one(f"#{fid}", YesNoField)

    def collect(self) -> dict:
        data = {}
        for fid in self._TOGGLE_FIELDS:
            try:
                data[fid] = self._get_toggle_widget(fid).get_value()
            except Exception:
                data[fid] = None
        for fid in self._LIKELIHOOD_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", LikelihoodField).get_value()
            except Exception:
                data[fid] = None
        for fid in self._TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        medications = []
        for i in range(self._med_row_count):
            row = {}
            for col in _MED_COLS:
                try:
                    row[col] = self.query_one(f"#med_{i}_{col}", Input).value
                except Exception:
                    row[col] = ""
            if any(row.values()):
                medications.append(row)
        data["medications"] = medications
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            medical = data if isinstance(data, dict) else {}
            for fid in self._TOGGLE_FIELDS:
                if fid in medical:
                    try:
                        self._get_toggle_widget(fid).set_value(medical[fid])
                    except Exception:
                        pass
            for fid in self._LIKELIHOOD_FIELDS:
                if fid in medical:
                    try:
                        self.query_one(f"#{fid}", LikelihoodField).set_value(medical[fid])
                    except Exception:
                        pass
            for fid in self._TEXT_FIELDS:
                if fid in medical:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = medical[fid]
                    except Exception:
                        pass
            meds = medical.get("medications", [])
            # Load the initial 4 rows directly
            for i, med in enumerate(meds[:4]):
                for col in _MED_COLS:
                    try:
                        self.query_one(f"#med_{i}_{col}", Input).value = med.get(col, "")
                    except Exception:
                        pass
            # Add + defer-load any extra rows
            extra = meds[4:]
            if extra:
                start = 4
                for _ in extra:
                    self._add_medication_row()
                self.set_timer(0.1, lambda s=start, m=meds: self._load_extra_meds(m, s))
        finally:
            self._loading = False
            self._update_rf_alert()

    def is_complete(self) -> bool:
        data = self.collect()
        urgent = self._RF_URGENT_CAUDA + self._RF_URGENT_CORD
        return all(data.get(fid) is not None for fid in urgent)

    def urgent_red_flag_status(self) -> str:
        """
        'pending'  — at least one urgent field unanswered
        'positive' — all answered, at least one True
        'clear'    — all answered, all False
        """
        urgent = self._RF_URGENT_CAUDA + self._RF_URGENT_CORD
        try:
            values = [self.query_one(f"#{fid}", RedFlagField).get_value() for fid in urgent]
        except Exception:
            return "pending"
        if any(v is None for v in values):
            return "pending"
        if any(v is True for v in values):
            return "positive"
        return "clear"

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(YesNoField.Changed)
    @on(LikelihoodField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._update_rf_alert()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
