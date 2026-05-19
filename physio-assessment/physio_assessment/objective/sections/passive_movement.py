"""Passive Movement & Overpressure — 03 Objective Examination."""

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_END_FEEL = [
    ("Norm",  "success"),
    ("Hard",  "default"),
    ("Sprng", "warning"),
    ("Spasm", "error"),
]                                           # 4 × 6 = 24 cols

_OP_RESP = [
    ("NoChg", "success"),
    ("Repro", "warning"),
    ("Incrs", "error"),
    ("Decrs", "default"),
]                                           # 4 × 6 = 24 cols

_PAIVM = [
    ("Norm",  "success"),
    ("↑R",    "warning"),
    ("↑R+P",  "error"),
    ("Pain",  "error"),
    ("↓R",    "default"),
]                                           # 5 × 6 = 30 cols


# ---------------------------------------------------------------------------
# Row definitions  — Tx (superior) first, Lx (inferior) last
# ---------------------------------------------------------------------------

_OP_ROWS: list[tuple[str, str]] = [
    ("Tx Flexion",   "op_tx_flex"),
    ("Tx Extension", "op_tx_ext"),
    ("Tx Rot L",     "op_tx_rot_l"),
    ("Tx Rot R",     "op_tx_rot_r"),
    ("Lx Flexion",   "op_lx_flex"),
    ("Lx Extension", "op_lx_ext"),
    ("Lx Lat Fl L",  "op_lx_lf_l"),
    ("Lx Lat Fl R",  "op_lx_lf_r"),
]

# T superior → L inferior; grid rows run top-to-bottom
_PAIVM_LEVELS: list[str] = [
    "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3",  "L4",  "L5",
]

# Column order: Left | Central | Right
_PAIVM_DIRS = ("ul_l", "c", "ul_r")

_COL_GAP = 2   # spacer columns between gang widgets


def _paivm_id(level: str, direction: str) -> str:
    return f"pm_{level}_{direction}"


# ---------------------------------------------------------------------------
# PassiveMovementSection
# ---------------------------------------------------------------------------

class PassiveMovementSection(BaseSection):
    """03 Passive Movement & Overpressure — OP end-feel/response + PAIVM grid."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    PassiveMovementSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    PassiveMovementSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* OP table
       label=16  ef-gang=24  gap=2  resp-gang=24  */
    PassiveMovementSection .op_hdr         { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    PassiveMovementSection .op_hdr_lbl     { width: 16; }
    PassiveMovementSection .op_hdr_ef      { width: 24; text-align: center; }
    PassiveMovementSection .op_hdr_gap     { width: 2; }
    PassiveMovementSection .op_hdr_resp    { width: 24; text-align: center; }

    PassiveMovementSection .op_row         { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    PassiveMovementSection .op_row_lbl     { width: 16; height: 3; content-align: left middle; }
    PassiveMovementSection .op_gap         { width: 2;  height: 3; }

    /* PAIVM table
       level=6  left-gang=30  gap=2  central-gang=30  gap=2  right-gang=30  */
    PassiveMovementSection .paivm_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    PassiveMovementSection .paivm_hdr_lbl  { width: 6; }
    PassiveMovementSection .paivm_hdr_col  { width: 30; text-align: center; }
    PassiveMovementSection .paivm_hdr_gap  { width: 2; }

    PassiveMovementSection .paivm_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    PassiveMovementSection .paivm_row_lbl  { width: 6; height: 3; content-align: left middle; }
    PassiveMovementSection .paivm_gap      { width: 2; height: 3; }

    PassiveMovementSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    PassiveMovementSection Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []   # [row][col] → RadioGroup id
        self._grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("03 Passive Movement & Overpressure", classes="section_title")

        # ── Overpressure ──────────────────────────────────────────────────────
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",          classes="op_hdr_lbl")
            yield Static("End-feel",  classes="op_hdr_ef")
            yield Static("",          classes="op_hdr_gap")
            yield Static("Response",  classes="op_hdr_resp")
        for label, prefix in _OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label,  classes="op_row_lbl")
                yield RadioGroup(_END_FEEL, id=f"{prefix}_ef")
                yield Static("",     classes="op_gap")
                yield RadioGroup(_OP_RESP,  id=f"{prefix}_resp")
        yield Label("OP notes:")
        yield TextArea(id="pm_op_notes", language="plain")

        # ── PAIVMs ────────────────────────────────────────────────────────────
        yield Label("PAIVMs", classes="subsection_header")
        with Horizontal(classes="paivm_hdr"):
            yield Static("",        classes="paivm_hdr_lbl")
            yield Static("Left",    classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Central", classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Right",   classes="paivm_hdr_col")
        for level in _PAIVM_LEVELS:
            with Horizontal(classes="paivm_row"):
                yield Static(level, classes="paivm_row_lbl")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "ul_l"))
                yield Static("",    classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "c"))
                yield Static("",    classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "ul_r"))
        yield Label("PAIVM notes:")
        yield TextArea(id="pm_paivm_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation — up/down between PAIVM rows; L/R handled by RadioGroup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        for row_idx, level in enumerate(_PAIVM_LEVELS):
            row = [_paivm_id(level, d) for d in _PAIVM_DIRS]
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
        for tid in ("pm_op_notes", "pm_paivm_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for tid in ("pm_op_notes", "pm_paivm_notes"):
                try:
                    self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#op_tx_flex_ef", RadioGroup).value is not None
        except Exception:
            return False
