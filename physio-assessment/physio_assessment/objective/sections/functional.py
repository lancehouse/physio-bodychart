"""Functional Assessment — 07 Objective Examination."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...sections.base import BaseSection
from ...widgets import GridInput, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_GAIT3 = [("Norm", "success"), ("Antlgc", "warning"), ("Anlgsc", "default")]
# 3 × 6 = 18 cols

_FUNC3 = [("Norm", "success"), ("Reduc", "warning"), ("Unabl", "error")]
# 3 × 6 = 18 cols

_BIN2  = [("Norm", "success"), ("Abnml", "error")]
# 2 × 6 = 12 cols


# ---------------------------------------------------------------------------
# Row definitions
# ---------------------------------------------------------------------------

# Single-gang functional movement obs: (label, id, gang options)
_FM_SINGLE: list[tuple[str, str, list]] = [
    ("Gait",          "ft_gait",  _GAIT3),
    ("Prone hip rot", "ft_phr",   _BIN2),
    ("Sit-to-stand",  "ft_sts_q", _FUNC3),
]

# Balance rows: (label, [input ids])
_BAL_ROWS: list[tuple[str, list]] = [
    ("Both legs",       ["ft_bal_both"]),
    ("Feet together",   ["ft_bal_feet"]),
    ("Tandem",          ["ft_bal_tandem"]),
    ("SLS eyes open",   ["ft_sls_eo_l",   "ft_sls_eo_r"]),
    ("SLS eyes closed", ["ft_sls_ec_l",   "ft_sls_ec_r"]),
    ("SLS foam 10cm",   ["ft_sls_foam_l", "ft_sls_foam_r"]),
]

# Timed capability measures: (label, id, unit)
_CAP_ROWS: list[tuple[str, str, str]] = [
    ("TUG  (3m chair→chair)", "ft_tug",   "s"),
    ("5× Sit-to-Stand",       "ft_sts5",  "s"),
    ("10m walk comfortable",  "ft_10m_e", "m/s"),
    ("10m walk fast",         "ft_10m_f", "m/s"),
    ("2 min walk",            "ft_2mw",   "m"),
]


# ---------------------------------------------------------------------------
# FunctionalSection
# ---------------------------------------------------------------------------

class FunctionalSection(BaseSection):
    """07 Functional — movement obs, balance (Steffen 2002), timed capability measures."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    FunctionalSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    FunctionalSection .section_title     { text-style: bold; margin-bottom: 0; }
    FunctionalSection .subsection_header { text-style: bold; color: $primary; margin-top: 1; margin-bottom: 0; }

    /* Single-gang obs rows — label + gang */
    FunctionalSection .obs_row { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    FunctionalSection .obs_lbl { width: 18; height: 3; content-align: left middle; }

    /* Bilateral SLS row — label + L-gang + gap + R-gang */
    FunctionalSection .sls_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    FunctionalSection .sls_hdr_lbl { width: 18; }
    FunctionalSection .sls_hdr_col { width: 18; text-align: center; }
    FunctionalSection .sls_hdr_gap { width: 2; }
    FunctionalSection .sls_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    FunctionalSection .sls_lbl     { width: 18; height: 3; content-align: left middle; }
    FunctionalSection .sls_gap     { width: 2;  height: 3; }

    /* Balance / capability table */
    FunctionalSection .tbl_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    FunctionalSection .tbl_hdr_lbl { width: 22; }
    FunctionalSection .tbl_hdr_col { width: 1fr; text-align: center; }
    FunctionalSection .tbl_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    FunctionalSection .tbl_lbl     { width: 22; height: 3; content-align: left middle; }
    FunctionalSection .tbl_inp     { width: 1fr; height: 3; padding: 0 1; }
    FunctionalSection .tbl_empty   { width: 1fr; height: 3; }

    FunctionalSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    FunctionalSection Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("07 Functional", classes="section_title")

        # ── Functional Movement Observation ───────────────────────────────────
        yield Label("Functional Movement", classes="subsection_header")
        for label, fid, opts in _FM_SINGLE:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_lbl")
                yield RadioGroup(opts, id=fid)

        # SLS — bilateral L/R
        with Horizontal(classes="sls_hdr"):
            yield Static("",      classes="sls_hdr_lbl")
            yield Static("Left",  classes="sls_hdr_col")
            yield Static("",      classes="sls_hdr_gap")
            yield Static("Right", classes="sls_hdr_col")
        with Horizontal(classes="sls_row"):
            yield Static("SLS",                  classes="sls_lbl")
            yield RadioGroup(_FUNC3, id="ft_sls_l")
            yield Static("",                     classes="sls_gap")
            yield RadioGroup(_FUNC3, id="ft_sls_r")

        # ── Balance (Steffen 2002) ────────────────────────────────────────────
        yield Label("Balance  (Steffen 2002)", classes="subsection_header")
        with Horizontal(classes="tbl_hdr"):
            yield Static("",         classes="tbl_hdr_lbl")
            yield Static("Left  s",  classes="tbl_hdr_col")
            yield Static("Right  s", classes="tbl_hdr_col")
        for label, ids in _BAL_ROWS:
            with Horizontal(classes="tbl_row"):
                yield Static(label, classes="tbl_lbl")
                yield GridInput(placeholder="s", id=ids[0], classes="tbl_inp")
                if len(ids) == 2:
                    yield GridInput(placeholder="s", id=ids[1], classes="tbl_inp")
                else:
                    yield Static("", classes="tbl_empty")

        # ── Timed Capability Measures ─────────────────────────────────────────
        yield Label("Timed Capability Measures", classes="subsection_header")
        for label, fid, unit in _CAP_ROWS:
            with Horizontal(classes="tbl_row"):
                yield Static(label, classes="tbl_lbl")
                yield GridInput(placeholder=unit, id=fid, classes="tbl_inp")
                yield Static("", classes="tbl_empty")

        # ── Notes / Special Tests ─────────────────────────────────────────────
        yield Label("Special tests / notes:")
        yield TextArea(id="ft_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation — balance + capability rows
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        for _, ids in _BAL_ROWS:
            row_idx = len(self._grid)
            self._grid.append(ids[:])
            for col_idx, wid in enumerate(ids):
                self._grid_pos[wid] = (row_idx, col_idx)
        for _, fid, _ in _CAP_ROWS:
            row_idx = len(self._grid)
            self._grid.append([fid])
            self._grid_pos[fid] = (row_idx, 0)

    def _focus_nearest(self, row: int, col: int) -> None:
        if row < 0 or row >= len(self._grid):
            return
        grid_row = self._grid[row]
        col = max(0, min(col, len(grid_row) - 1))
        try:
            self.query_one(f"#{grid_row[col]}").focus()
        except Exception:
            pass

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._grid_pos:
            return
        row, col = self._grid_pos[focused.id]
        if event.direction == "up":
            self._focus_nearest(row - 1, col)
        elif event.direction == "down":
            self._focus_nearest(row + 1, col)
        elif event.direction == "left" and col > 0:
            self._focus_nearest(row, col - 1)
        elif event.direction == "right" and col < len(self._grid[row]) - 1:
            self._focus_nearest(row, col + 1)
        event.stop()

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(GridInput.Changed)
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
        for _, ids in _BAL_ROWS:
            for fid in ids:
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        for _, fid, _ in _CAP_ROWS:
            try:
                data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
            except Exception:
                data[fid] = ""
        try:
            data["ft_notes"] = self.query_one("#ft_notes", TextArea).text
        except Exception:
            data["ft_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for _, ids in _BAL_ROWS:
                for fid in ids:
                    try:
                        self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                    except Exception:
                        pass
            for _, fid, _ in _CAP_ROWS:
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
            try:
                self.query_one("#ft_notes", TextArea).text = data.get("ft_notes", "")
            except Exception:
                pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#ft_tug", GridInput).value.strip() != ""
        except Exception:
            return False
