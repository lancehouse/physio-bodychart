"""General Observation — 01 Objective Examination."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets — labels ≤ 6 chars (border: none gives full 6 chars)
# ---------------------------------------------------------------------------

_SEV4  = [("Norm",  "success"), ("Mild",   "warning"), ("Mod",    "error"),   ("Sev",   "error")]
_LORD3 = [("Norm",  "success"), ("↑Inc",   "warning"), ("↓Dec",   "warning")]
_KYPH3 = [("Norm",  "success"), ("↑Inc",   "warning"), ("↓Dec",   "warning")]
_LEAN4 = [("None",  "success"), ("Left",   "warning"), ("Right",  "warning"), ("Fwd",   "default")]
_BRTH4 = [("Norm",  "success"), ("Apical", "warning"), ("Abdo",   "warning"), ("Paradx","error")]
_SCAP5 = [("Norm",  "success"), ("Prot",   "warning"), ("Retr",   "warning"), ("Elev",  "warning"), ("Depr", "warning")]
_GAIT2 = [("Norm",  "success"), ("Antlg",  "warning")]
_SLS4  = [("<1s",   "error"),   ("<5s",    "warning"), ("<10s",   "warning"), ("Norm",  "success")]
_STS4  = [("Norm",  "success"), ("Hand",   "warning"), ("Reduc",  "warning"), ("Unabl", "error")]


# ---------------------------------------------------------------------------
# GeneralSection
# ---------------------------------------------------------------------------

class GeneralSection(BaseSection):
    """01 General Observation — physical stats, posture, functional movement."""

    _nav_include_inputs = True  # include Input (stats) in arrow-key nav candidates

    class FieldChanged(Message):
        pass

    # (row label, data-key, gang options)
    _POSTURE_ROWS: list[tuple[str, str, list]] = [
        ("Lumbar lordosis",   "go_lx_lord", _LORD3),
        ("Thoracic kyphosis", "go_tx_kyph", _KYPH3),
        ("Antalgic lean",     "go_lean",    _LEAN4),
        ("Sway posture",      "go_sway",    _SEV4),
        ("Breathing",         "go_breath",  _BRTH4),
        ("Scapular L",        "go_scap_l",  _SCAP5),
        ("Scapular R",        "go_scap_r",  _SCAP5),
        ("Muscle wasting",    "go_wasting", _SEV4),
    ]
    _FUNCTIONAL_ROWS: list[tuple[str, str, list]] = [
        ("Gait",         "go_gait",  _GAIT2),
        ("SLS Left",     "go_sls_l", _SLS4),
        ("SLS Right",    "go_sls_r", _SLS4),
        ("Sit-to-stand", "go_sts",   _STS4),
    ]

    _INPUT_IDS = ("go_height", "go_weight", "go_bmi", "go_nrs", "go_sit_tol")
    _TA_IDS    = ("go_posture_notes", "go_functional_notes")

    DEFAULT_CSS = """
    GeneralSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    GeneralSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* Physical stats row */
    GeneralSection .stats_row   { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    GeneralSection .stats_lbl   { height: 3; content-align: right middle; padding: 0 1; }
    GeneralSection .stats_input { width: 10; height: 3; padding: 0 1; }
    GeneralSection .stats_unit  { width: 6;  height: 3; content-align: left middle; color: $text-muted; }

    /* Observation rows — label + gang + comment input */
    GeneralSection .obs_row   { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    GeneralSection .obs_label { width: 20; height: 3; content-align: left middle; }
    GeneralSection .obs_cmt   { height: 3; width: 1fr; }

    GeneralSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    GeneralSection Label    { height: auto; margin-top: 0; }
    """

    def compose(self) -> ComposeResult:
        yield Label("01 General Observation", classes="section_title")

        # ── Physical ──────────────────────────────────────────────────────────
        yield Label("Physical", classes="subsection_header", id="go_physical")
        with Horizontal(classes="stats_row"):
            yield Static("Height",           classes="stats_lbl")
            yield Input(placeholder="cm",    id="go_height",  classes="stats_input")
            yield Static("cm",               classes="stats_unit")
            yield Static("Weight",           classes="stats_lbl")
            yield Input(placeholder="kg",    id="go_weight",  classes="stats_input")
            yield Static("kg",               classes="stats_unit")
            yield Static("BMI",              classes="stats_lbl")
            yield Input(placeholder="kg/m²", id="go_bmi",     classes="stats_input")
        with Horizontal(classes="stats_row"):
            yield Static("NRS rest",         classes="stats_lbl")
            yield Input(placeholder="/10",   id="go_nrs",     classes="stats_input")
            yield Static("/10",              classes="stats_unit")
            yield Static("Sitting tol",      classes="stats_lbl")
            yield Input(placeholder="min",   id="go_sit_tol", classes="stats_input")
            yield Static("min",              classes="stats_unit")
        with Horizontal(classes="obs_row"):
            yield Static("General mobility", classes="obs_label")
            yield RadioGroup(_SEV4, id="go_transfer")
            yield Input(id="go_transfer_cmt", classes="obs_cmt")

        # ── Posture ───────────────────────────────────────────────────────────
        yield Label("Posture", classes="subsection_header", id="go_posture")
        for label, key, opts in self._POSTURE_ROWS:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_label")
                yield RadioGroup(opts, id=key)
                yield Input(id=f"{key}_cmt", classes="obs_cmt")
        yield Label("Posture notes:")
        yield TextArea(id="go_posture_notes", language="plain")

        # ── Functional Movement ───────────────────────────────────────────────
        yield Label("Functional Movement", classes="subsection_header", id="go_functional_movement")
        for label, key, opts in self._FUNCTIONAL_ROWS:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_label")
                yield RadioGroup(opts, id=key)
                yield Input(id=f"{key}_cmt", classes="obs_cmt")
        yield Label("Functional notes:")
        yield TextArea(id="go_functional_notes", language="plain")

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
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
        for iid in self._INPUT_IDS:
            try:
                data[iid] = self.query_one(f"#{iid}", Input).value.strip()
            except Exception:
                data[iid] = ""
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for inp in self.query("Input.obs_cmt"):
            data[inp.id] = inp.value
        for tid in self._TA_IDS:
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for iid in self._INPUT_IDS:
                try:
                    self.query_one(f"#{iid}", Input).value = data.get(iid, "")
                except Exception:
                    pass
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for inp in self.query("Input.obs_cmt"):
                inp.value = data.get(inp.id, "")
            for tid in self._TA_IDS:
                try:
                    self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return bool(self.query_one("#go_height", Input).value.strip())
        except Exception:
            return False
