"""Medical Screening section (core/03)."""

from textual.app import ComposeResult, on
from textual.containers import Vertical, ScrollableContainer, Horizontal
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton, FlagButton


# ---------------------------------------------------------------------------
# Medication table column definitions
# ---------------------------------------------------------------------------

_MED_COLS        = ["name",         "dose",  "timing",       "comments"]
_MED_COL_LABELS  = ["Name / brand", "Dose",  "Frequency",    "Comments"]
_MED_COL_CLASSES = ["med_col_name", "med_col_dose", "med_col_timing", "med_col_comments"]


class MedRow(Horizontal):
    """One row in the medications table."""

    def __init__(self, row_idx: int, **kwargs):
        super().__init__(**kwargs)
        self._row_idx = row_idx

    def compose(self) -> ComposeResult:
        for col, css_class in zip(_MED_COLS, _MED_COL_CLASSES):
            yield Input(id=f"med_{self._row_idx}_{col}", classes=css_class, placeholder="")


# ---------------------------------------------------------------------------
# LikelihoodField — kept here; imported by pain_classification.py
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

    _CYCLE    = [None, "Low", "Moderate", "High"]
    _VARIANTS = {None: "primary", "Low": "success", "Moderate": "warning", "High": "error"}

    def __init__(self, label: str, field_id: str, **kwargs):
        super().__init__(**kwargs)
        self.id       = field_id
        self._label   = label
        self._field_id = field_id
        self._value   = None

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Button("?", id=f"{self._field_id}_btn", variant="primary")

    def get_value(self) -> str | None:
        return self._value

    def set_value(self, value: str | None) -> None:
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_btn", Button)
            btn.label   = value if value else "?"
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
        height: auto;
        padding: 0 1;
    }

    .section_title    { text-style: bold; color: $text; margin-bottom: 0; }

    .subgroup_header  { color: $text-muted; margin-top: 1; margin-bottom: 0; text-style: italic; }

    .btn_row  { height: auto; width: 100%; margin-bottom: 1; }
    .solo_btn { margin-bottom: 0; }
    .field_row { height: auto; width: 100%; margin: 0; padding: 0; }
    .field_row Label   { width: 28; height: auto; padding: 0 1 0 0; }
    .field_row Input   { width: 1fr; height: auto; padding: 0 1; }
    .field_row TextArea { width: 1fr; height: auto; min-height: 2; padding: 0 1; }

    CheckButton { width: auto; height: 3; min-width: 16; margin: 0 1 0 0; }

    #med_rf_alert {
        width: 100%;
        padding: 0 1;
        text-style: bold;
        margin-bottom: 0;
        display: none;
    }
    #med_rf_alert.rf_warning { color: $warning; background: $warning 20%; }
    #med_rf_alert.rf_urgent  { color: $error;   background: $error 20%; }

    .med_header_row { height: auto; padding-top: 1; margin-bottom: 0; }
    .med_header_row Label { text-style: bold; color: $text-muted; margin-bottom: 0; padding: 0 1; }
    #med_table { height: auto; width: 100%; }
    .med_row { height: 3; width: 100%; margin-bottom: 0; }
    .med_row Input { height: 1fr; margin-bottom: 0; }
    .med_col_name     { width: 3fr; }
    .med_col_dose     { width: 2fr; }
    .med_col_timing   { width: 2fr; }
    .med_col_comments { width: 5fr; }
    """

    # Red flag field groups (all use FlagButton)
    _RF_GENERAL = [
        "rf_weight_loss", "rf_cancer_history", "rf_age_50_spinal", "rf_failed_conservative",
        "rf_trauma", "rf_corticosteroids_fracture", "rf_osteoporosis_fracture",
        "rf_fever", "rf_immunosuppressed", "rf_spinal_procedure",
        "umn_hyperreflexia", "umn_babinski", "umn_clonus", "umn_romberg", "umn_coordination",
    ]
    _RF_URGENT_CAUDA = ["rf_saddle_anaesthesia", "rf_bladder_disturbance", "rf_bowel_disturbance"]
    _RF_URGENT_CORD  = ["rf_bilateral_paraesthesia", "rf_gait_disturbance"]

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
        "rf_malignancy_comment", "rf_fracture_comment", "rf_infection_comment",
        "cauda_equina_action", "spinal_cord_action", "umn_interpretation",
        "diff_as_action", "diff_aaa_action", "diff_vc_action",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._med_row_count = 4

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("Medical Screening", classes="section_title")

        # ── Comorbidities / PMH ──────────────────────────────────────────
        yield Label("— Comorbidities / PMH —", classes="subsection_header", id="med_comorbidities")
        yield CheckButton("No previous injuries or general health issues: Confirmed",
                          id="no_previous_injuries", classes="solo_btn")
        with Horizontal(classes="field_row"):
            yield Label("Previous injuries:")
            yield TextArea(id="previous_injuries", language="plain")
        yield Label("Comorbidities:")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Cancer (hx or current)",    id="comorbid_cancer")
            yield FlagButton("Mental health",             id="comorbid_mental_health")
            yield FlagButton("Osteoporosis",              id="comorbid_osteoporosis")
            yield FlagButton("Inflammatory condition",    id="comorbid_inflammatory")
            yield FlagButton("Fibromyalgia",              id="comorbid_fibromyalgia")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Chronic fatigue (CFS)",    id="comorbid_cfs")
            yield FlagButton("Irritable bowel (IBS)",    id="comorbid_ibs")
            yield FlagButton("Chronic whiplash",         id="comorbid_whiplash")
            yield FlagButton("Painful skin rash",        id="comorbid_skin_rash")
            yield FlagButton("Drug / alcohol issues",    id="comorbid_drug_alcohol")
        yield FlagButton("Fatigue / memory / cognition issues",
                         id="comorbid_fatigue_memory", classes="solo_btn")
        with Horizontal(classes="field_row"):
            yield Label("Other comorbidities:")
            yield TextArea(id="comorbid_other", language="plain")

        # ── Cardiovascular Risk Factors ──────────────────────────────────
        yield Label("— Cardiovascular Risk Factors —", classes="subsection_header", id="med_cardiovascular")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Hypercholesterolaemia",     id="cvd_hypercholesterolaemia")
            yield FlagButton("Cardiac disease",           id="cvd_cardiac")
            yield FlagButton("Vascular disease",          id="cvd_vascular")
            yield FlagButton("Stroke / TIA",              id="cvd_stroke_tia")
            yield FlagButton("Diabetes",                  id="cvd_diabetes")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Prolonged corticosteroids", id="cvd_corticosteroids")
            yield FlagButton("Clotting disorder",         id="cvd_clotting")
            yield FlagButton("Oral contraceptive",        id="cvd_ocp")
            yield FlagButton("Smoker",                    id="cvd_smoker")
            yield FlagButton("Post-partum",               id="cvd_postpartum")
        yield FlagButton("Familial history of presenting condition",
                         id="cvd_familial_history", classes="solo_btn")

        # ── Red Flags ────────────────────────────────────────────────────
        yield Label("— Red Flags —", classes="subsection_header", id="med_red_flags")
        yield Static("", id="med_rf_alert")

        yield Label("Malignancy:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Unexplained weight loss",   id="rf_weight_loss")
            yield FlagButton("Cancer history",            id="rf_cancer_history")
            yield FlagButton("Age >50 + new spinal pain", id="rf_age_50_spinal")
            yield FlagButton("Failed conservative Rx",    id="rf_failed_conservative")
        with Horizontal(classes="field_row"):
            yield Label("Comment:")
            yield TextArea(id="rf_malignancy_comment", language="plain")

        yield Label("Fracture:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Significant trauma",          id="rf_trauma")
            yield FlagButton("Prolonged corticosteroids",   id="rf_corticosteroids_fracture")
            yield FlagButton("Confirmed osteoporosis",      id="rf_osteoporosis_fracture")
        with Horizontal(classes="field_row"):
            yield Label("Comment:")
            yield TextArea(id="rf_fracture_comment", language="plain")

        yield Label("Infection:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Fever",                      id="rf_fever")
            yield FlagButton("Immunosuppressed",           id="rf_immunosuppressed")
            yield FlagButton("Recent spinal procedure",    id="rf_spinal_procedure")
        with Horizontal(classes="field_row"):
            yield Label("Comment:")
            yield TextArea(id="rf_infection_comment", language="plain")

        yield Label("Cauda Equina Compression (URGENT):", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Saddle / perineal anaesthesia", id="rf_saddle_anaesthesia")
            yield FlagButton("Bladder disturbance",           id="rf_bladder_disturbance")
            yield FlagButton("Bowel disturbance",             id="rf_bowel_disturbance")
        with Horizontal(classes="field_row"):
            yield Label("Action taken:")
            yield TextArea(id="cauda_equina_action", language="plain")

        yield Label("Spinal Cord Compression (URGENT):", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Bilateral paraesthesia / weakness", id="rf_bilateral_paraesthesia")
            yield FlagButton("Gait / balance disturbance",        id="rf_gait_disturbance")
        with Horizontal(classes="field_row"):
            yield Label("Action taken:")
            yield TextArea(id="spinal_cord_action", language="plain")

        yield Label("Upper Motor Neurone Signs:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Hyperreflexia",          id="umn_hyperreflexia")
            yield FlagButton("Babinski +ve",           id="umn_babinski")
            yield FlagButton("Clonus",                 id="umn_clonus")
            yield FlagButton("Romberg impaired",       id="umn_romberg")
            yield FlagButton("Coordination impaired",  id="umn_coordination")
        with Horizontal(classes="field_row"):
            yield Label("Interpretation:")
            yield TextArea(id="umn_interpretation", language="plain")

        # ── Differential Screening ───────────────────────────────────────
        yield Label("— Differential Screening —", classes="subsection_header", id="med_differential")

        yield Label("Ankylosing Spondylitis:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Insidious onset",           id="diff_as_insidious")
            yield FlagButton("Lumbar / SIJ spreading",    id="diff_as_lumbar_sij")
            yield FlagButton("Inflammatory pattern",      id="diff_as_inflammatory")
            yield FlagButton("Breathing difficulties",    id="diff_as_breathing")
            yield FlagButton("Fever / weight loss",       id="diff_as_fever_weight_loss")
        yield LikelihoodField("Likelihood:", field_id="diff_as_likelihood")
        with Horizontal(classes="field_row"):
            yield Label("Action:")
            yield TextArea(id="diff_as_action", language="plain")

        yield Label("Abdominal Aortic Aneurysm:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Pulsating lumbar / groin pain",    id="diff_aaa_pulsating")
            yield FlagButton("Age >50",                          id="diff_aaa_age_50")
            yield FlagButton("CVD risk factors present",         id="diff_aaa_cvd_risk")
            yield FlagButton("Sudden onset + low BP (ruptured)", id="diff_aaa_ruptured")
        yield LikelihoodField("Likelihood:", field_id="diff_aaa_likelihood")
        with Horizontal(classes="field_row"):
            yield Label("Action:")
            yield TextArea(id="diff_aaa_action", language="plain")

        yield Label("Vascular Claudication:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Non-dermatomal leg symptoms",          id="diff_vc_non_dermatomal")
            yield FlagButton("Age >50",                              id="diff_vc_age_50")
            yield FlagButton("CVD risk factors",                     id="diff_vc_cvd_risk")
            yield FlagButton("Pain / fatigue with walking",          id="diff_vc_walking_pain")
            yield FlagButton("PVD signs (cold / blotchy / hairless)",id="diff_vc_pvd_signs")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Impotence (men)",                      id="diff_vc_impotence")
            yield FlagButton("Leg pain at night",                    id="diff_vc_night_pain")
        yield LikelihoodField("Likelihood:", field_id="diff_vc_likelihood")
        with Horizontal(classes="field_row"):
            yield Label("Action:")
            yield TextArea(id="diff_vc_action", language="plain")

        # ── Medications ──────────────────────────────────────────────────
        yield Label("— Medications —", classes="subsection_header", id="med_medications")
        with Horizontal(classes="med_header_row"):
            for lbl, css in zip(_MED_COL_LABELS, _MED_COL_CLASSES):
                yield Label(lbl, classes=css)
        with Vertical(id="med_table"):
            for i in range(4):
                yield MedRow(i, classes="med_row")

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
    # Red flag alert banner
    # ------------------------------------------------------------------

    def _update_rf_alert(self) -> None:
        try:
            alert = self.query_one("#med_rf_alert", Static)
            urgent_cauda = any(
                self.query_one(f"#{fid}", CheckButton).value is True
                for fid in self._RF_URGENT_CAUDA
            )
            urgent_cord = any(
                self.query_one(f"#{fid}", CheckButton).value is True
                for fid in self._RF_URGENT_CORD
            )
            general_rf = any(
                self.query_one(f"#{fid}", CheckButton).value is True
                for fid in self._RF_GENERAL
            )
            if urgent_cauda:
                alert.update("⚠ URGENT: Cauda equina symptoms — document action below")
                alert.set_class(True, "rf_urgent")
                alert.set_class(False, "rf_warning")
                alert.display = True
            elif urgent_cord:
                alert.update("⚠ URGENT: Spinal cord compression signs — document action below")
                alert.set_class(True, "rf_urgent")
                alert.set_class(False, "rf_warning")
                alert.display = True
            elif general_rf:
                alert.update("⚠ Red flag(s) positive — clinical judgement required")
                alert.set_class(True, "rf_warning")
                alert.set_class(False, "rf_urgent")
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

    def collect(self) -> dict:
        data = {}
        for fid in self._TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
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
                        self.query_one(f"#{fid}", CheckButton).set_value(medical[fid])
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
            for i, med in enumerate(meds[:4]):
                for col in _MED_COLS:
                    try:
                        self.query_one(f"#med_{i}_{col}", Input).value = med.get(col, "")
                    except Exception:
                        pass
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
        urgent = self._RF_URGENT_CAUDA + self._RF_URGENT_CORD
        try:
            values = [self.query_one(f"#{fid}", CheckButton).value for fid in urgent]
            return all(v is not None for v in values)
        except Exception:
            return False

    def urgent_red_flag_status(self) -> str:
        """'pending' / 'positive' / 'clear' — drives the Medical nav tab colour."""
        urgent = self._RF_URGENT_CAUDA + self._RF_URGENT_CORD
        try:
            values = [self.query_one(f"#{fid}", CheckButton).value for fid in urgent]
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

    @on(CheckButton.Changed)
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
