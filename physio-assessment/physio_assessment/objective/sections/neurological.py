"""Neurological — 04 Objective Examination."""

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import CheckButton, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_REFLEX  = [("Norm", "success"), ("Redu",  "warning"), ("Absnt", "error"),
            ("Brisk","warning"), ("Hyper",  "error")]        # 5 × 6 = 30 cols

_PLANTAR = [("Flexr","success"), ("Extnr",  "error")]        # 2 × 6 = 12 cols

_MYOTOME = [("5/5", "success"), ("4/5",   "warning"), ("3/5", "error"),
            ("2/5", "error"),   ("0/5",   "error")]          # 5 × 6 = 30 cols

_DERM    = [("Norm", "success"), ("↓Hypo", "warning"), ("Absnt", "error"),
            ("↑Hypr","error")]                               # 4 × 6 = 24 cols

_ND_RESP = [("Neg",  "success"), ("Lumbar","warning"), ("Leg",   "error"),
            ("Cntrl","error"),   ("Sensd", "warning")]        # 5 × 6 = 30 cols


# ---------------------------------------------------------------------------
# Row definitions
# ---------------------------------------------------------------------------

_REFLEX_ROWS: list[tuple[str, str, list]] = [
    ("Knee jerk  L3/4", "nr_knee",    _REFLEX),
    ("Ankle jerk  S1",  "nr_ankle",   _REFLEX),
    ("Plantar",          "nr_plantar", _PLANTAR),
]
_MYOTOME_ROWS: list[tuple[str, str, list]] = [
    ("L2  Hip flex",   "nr_l2", _MYOTOME),
    ("L3  Knee ext",   "nr_l3", _MYOTOME),
    ("L4  Ankle DF",   "nr_l4", _MYOTOME),
    ("L5  GT ext/EHL", "nr_l5", _MYOTOME),
    ("S1  PF / evert", "nr_s1", _MYOTOME),
    ("S2  Ham / KF",   "nr_s2", _MYOTOME),
]
_DERM_ROWS: list[tuple[str, str]] = [
    ("L2  Ant thigh",  "sn_l2"),
    ("L3  Med knee",   "sn_l3"),
    ("L4  Med leg",    "sn_l4"),
    ("L5  Lat leg/GT", "sn_l5"),
    ("S1  Lat foot",   "sn_s1"),
    ("S2  Post thigh", "sn_s2"),
]
_ND_ROWS: list[tuple[str, str]] = [
    ("SLR",   "nr_slr"),
    ("Slump", "nr_slump"),
    ("PKF",   "nr_pkf"),
]
_UMN_ITEMS: list[tuple[str, str]] = [
    ("Hyperreflexia",  "nr_umn_hyper"),
    ("Babinski +",     "nr_umn_bab"),
    ("Clonus",         "nr_umn_clonus"),
    ("Romberg +",      "nr_umn_romberg"),
    ("Coord impaired", "nr_umn_coord"),
]

_GAP = 2   # char gap between adjacent gangs


# ---------------------------------------------------------------------------
# NeurologicalSection
# ---------------------------------------------------------------------------

class NeurologicalSection(BaseSection):
    """04 Neurological — reflexes, myotomes, dermatomes, neurodynamics, UMN signs."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    NeurologicalSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    NeurologicalSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* Reflex / myotome / dermatome L|R grid
       label=18  L-gang(auto)  gap=2  R-gang(auto)                          */
    NeurologicalSection .rm_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .rm_hdr_lbl { width: 18; }
    NeurologicalSection .rm_hdr_col { width: 1fr; text-align: center; }
    NeurologicalSection .rm_hdr_gap { width: 2; }
    NeurologicalSection .rm_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    NeurologicalSection .rm_lbl     { width: 18; height: 3; content-align: left middle; }
    NeurologicalSection .rm_gap     { width: 2;  height: 3; }

    /* Neurodynamics
       label=8  L-deg=6  gap=2  L-resp=30  gap=2  R-deg=6  gap=2  R-resp=30 */
    NeurologicalSection .nd_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .nd_hdr_lbl  { width: 8; }
    NeurologicalSection .nd_hdr_grp  { width: 38; text-align: center; text-style: bold; }
    NeurologicalSection .nd_hdr_gap  { width: 2; }
    NeurologicalSection .nd_sub      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    NeurologicalSection .nd_sub_lbl  { width: 8; }
    NeurologicalSection .nd_sub_deg  { width: 6;  text-align: center; }
    NeurologicalSection .nd_sub_gap  { width: 2; }
    NeurologicalSection .nd_sub_resp { width: 30; text-align: center; }
    NeurologicalSection .nd_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    NeurologicalSection .nd_lbl      { width: 8;  height: 3; content-align: left middle; }
    NeurologicalSection .nd_deg      { width: 6;  height: 3; padding: 0 1; }
    NeurologicalSection .nd_gap      { width: 2;  height: 3; }

    /* UMN — CheckButtons fill equally across the row */
    NeurologicalSection .umn_row { layout: horizontal; height: 3; width: 100%; }
    NeurologicalSection .umn_row CheckButton {
        width: 1fr; height: 3; min-width: 0; margin: 0 1 0 0;
    }
    NeurologicalSection .umn_row CheckButton:last-of-type { margin: 0; }

    NeurologicalSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    NeurologicalSection Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("04 Neurological", classes="section_title")

        # ── Reflexes ──────────────────────────────────────────────────────────
        yield Label("Reflexes", classes="subsection_header", id="nr_reflexes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _REFLEX_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r")

        # ── Myotomes ──────────────────────────────────────────────────────────
        yield Label("Myotomes", classes="subsection_header", id="nr_myotomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix, states in _MYOTOME_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(states, id=f"{prefix}_l")
                yield Static("",    classes="rm_gap")
                yield RadioGroup(states, id=f"{prefix}_r")

        # ── Dermatomes ────────────────────────────────────────────────────────
        yield Label("Dermatomes", classes="subsection_header", id="nr_dermatomes")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix in _DERM_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label, classes="rm_lbl")
                yield RadioGroup(_DERM, id=f"{prefix}_l")
                yield Static("",       classes="rm_gap")
                yield RadioGroup(_DERM, id=f"{prefix}_r")

        # ── Neurodynamics ─────────────────────────────────────────────────────
        yield Label("Neurodynamics", classes="subsection_header", id="nr_neurodynamics")
        with Horizontal(classes="nd_hdr"):
            yield Static("",      classes="nd_hdr_lbl")
            yield Static("Left",  classes="nd_hdr_grp")
            yield Static("",      classes="nd_hdr_gap")
            yield Static("Right", classes="nd_hdr_grp")
        with Horizontal(classes="nd_sub"):
            yield Static("",         classes="nd_sub_lbl")
            yield Static("Deg",      classes="nd_sub_deg")
            yield Static("",         classes="nd_sub_gap")
            yield Static("Response", classes="nd_sub_resp")
            yield Static("",         classes="nd_sub_gap")
            yield Static("Deg",      classes="nd_sub_deg")
            yield Static("",         classes="nd_sub_gap")
            yield Static("Response", classes="nd_sub_resp")
        for label, prefix in _ND_ROWS:
            with Horizontal(classes="nd_row"):
                yield Static(label,  classes="nd_lbl")
                yield Input(placeholder="°", id=f"{prefix}_l_deg", classes="nd_deg")
                yield Static("",             classes="nd_gap")
                yield RadioGroup(_ND_RESP,   id=f"{prefix}_l_resp")
                yield Static("",             classes="nd_gap")
                yield Input(placeholder="°", id=f"{prefix}_r_deg", classes="nd_deg")
                yield Static("",             classes="nd_gap")
                yield RadioGroup(_ND_RESP,   id=f"{prefix}_r_resp")

        # ── UMN Signs ─────────────────────────────────────────────────────────
        yield Label("UMN Signs", classes="subsection_header", id="nr_umn")
        with Horizontal(classes="umn_row"):
            for label, uid in _UMN_ITEMS:
                yield CheckButton(label, id=uid)

        # ── Notes ─────────────────────────────────────────────────────────────
        yield Label("Notes:")
        yield TextArea(id="nr_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation — up/down across reflex + myotome + dermatome rows
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # 3-tuple rows (reflex + myotome)
        for _, prefix, _ in _REFLEX_ROWS + _MYOTOME_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)
        # 2-tuple rows (dermatome)
        for _, prefix in _DERM_ROWS:
            row_idx = len(self._grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._grid_pos[fid]
        target_row = row - 1 if event.key == "up" else row + 1
        if 0 <= target_row < len(self._grid):
            try:
                self.query_one(f"#{self._grid[target_row][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(CheckButton.Changed)
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
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for _, uid in _UMN_ITEMS:
            try:
                data[uid] = self.query_one(f"#{uid}", CheckButton).value
            except Exception:
                data[uid] = None
        for _, prefix in _ND_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}_deg"
                try:
                    data[fid] = self.query_one(f"#{fid}", Input).value.strip()
                except Exception:
                    data[fid] = ""
        try:
            data["nr_notes"] = self.query_one("#nr_notes", TextArea).text
        except Exception:
            data["nr_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for _, uid in _UMN_ITEMS:
                try:
                    self.query_one(f"#{uid}", CheckButton).set_value(data.get(uid))
                except Exception:
                    pass
            for _, prefix in _ND_ROWS:
                for side in ("l", "r"):
                    fid = f"{prefix}_{side}_deg"
                    try:
                        self.query_one(f"#{fid}", Input).value = data.get(fid, "")
                    except Exception:
                        pass
            try:
                self.query_one("#nr_notes", TextArea).text = data.get("nr_notes", "")
            except Exception:
                pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#nr_knee_l", RadioGroup).value is not None
        except Exception:
            return False
