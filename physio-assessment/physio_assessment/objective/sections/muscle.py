"""Muscle Testing — 06 Objective Examination."""

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...nav import escape_to_neighbor
from ...sections.base import BaseSection
from ...widgets import CheckButton, GridInput, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_ML4 = [("Norm", "success"), ("↓Mild", "warning"), ("↓Mod", "error"), ("↓Mrkd", "error")]
# 4 × 6 = 24 cols

_MA4 = [("Norm", "success"), ("Fair", "warning"), ("Poor", "error"), ("Ovact", "error")]
# 4 × 6 = 24 cols


# ---------------------------------------------------------------------------
# Row definitions
# ---------------------------------------------------------------------------

# Muscle length: (label, prefix) — bilateral L/R RadioGroup
_ML_ROWS: list[tuple[str, str]] = [
    ("QL (side sit)",  "ml_ql"),
    ("Thomas test",    "ml_thomas"),
    ("Hamstrings SLR", "ml_ham"),
]

# Muscle activation: (label, id) — single RadioGroup per row
_MA_ROWS: list[tuple[str, str]] = [
    ("Tx erector spinae", "ma_tx_es"),
    ("Transversus abd",   "ma_tva"),
    ("Lumbar multifidus", "ma_lmf"),
]

# Hip strength rows — L/R kg via GridInput: (label, prefix)
_HIP_ROWS: list[tuple[str, str]] = [
    ("Hip flexion",      "sh_hip_flex"),
    ("Hip extension",    "sh_hip_ext"),
    ("Hip abduction",    "sh_hip_abd"),
    ("Hip adduction",    "sh_hip_add"),
    ("Hip int rotation", "sh_hip_ir"),
    ("Hip ext rotation", "sh_hip_er"),
]

# SIJ provocation: (label, id)
_SIJ_ITEMS: list[tuple[str, str]] = [
    ("Sacral thrust",      "sij_sacral"),
    ("Post thigh thrust",  "sij_ptt"),
    ("Distraction supine", "sij_dist"),
    ("Compression s/l",    "sij_comp"),
    ("Gaenslen",           "sij_gaenslen"),
    ("ASLR compression",   "sij_aslr"),
]

_GAP = 2   # char gap between adjacent gangs


# ---------------------------------------------------------------------------
# MuscleSection
# ---------------------------------------------------------------------------

class MuscleSection(BaseSection):
    """06 Muscle Testing — length, activation, strength (Wagner FPX), SIJ signs."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    MuscleSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    MuscleSection .section_title     { text-style: bold; margin-bottom: 0; }


    /* Muscle length / activation header + rows */
    MuscleSection .rm_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    MuscleSection .rm_hdr_lbl { width: 18; }
    MuscleSection .rm_hdr_col { width: 24; text-align: center; }
    MuscleSection .rm_hdr_gap { width: 2; }
    MuscleSection .rm_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    MuscleSection .rm_lbl     { width: 18; height: 3; content-align: left middle; }
    MuscleSection .rm_gap     { width: 2;  height: 3; }

    /* Trunk strength rows — label + single input */
    MuscleSection .trunk_row  { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    MuscleSection .trunk_lbl  { width: 18; height: 3; content-align: left middle; }
    MuscleSection .trunk_inp  { width: 1fr; height: 3; padding: 0 1; }

    /* Hip strength grid */
    MuscleSection .hip_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    MuscleSection .hip_hdr_lbl { width: 18; }
    MuscleSection .hip_hdr_col { width: 1fr; text-align: center; }
    MuscleSection .hip_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    MuscleSection .hip_lbl     { width: 18; height: 3; content-align: left middle; }
    MuscleSection .hip_inp     { width: 1fr; height: 3; padding: 0 1; }

    /* SIJ row */
    MuscleSection .sij_row { layout: horizontal; height: 3; width: 100%; }
    MuscleSection .sij_row CheckButton {
        width: 1fr; height: 3; min-width: 0; margin: 0 1 0 0;
    }
    MuscleSection .sij_row CheckButton:last-of-type { margin: 0; }

    MuscleSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    MuscleSection Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ml_grid:     list[list[str]] = []
        self._ml_grid_pos: dict[str, tuple[int, int]] = {}
        self._hip_grid:     list[list[str]] = []
        self._hip_grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("06 Muscle Testing", classes="section_title")

        # ── Muscle Length ─────────────────────────────────────────────────────
        yield Label("Muscle Length", classes="subsection_header", id="ml_length")
        with Horizontal(classes="rm_hdr"):
            yield Static("",      classes="rm_hdr_lbl")
            yield Static("Left",  classes="rm_hdr_col")
            yield Static("",      classes="rm_hdr_gap")
            yield Static("Right", classes="rm_hdr_col")
        for label, prefix in _ML_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label,             classes="rm_lbl")
                yield RadioGroup(_ML4, id=f"{prefix}_l")
                yield Static("",                classes="rm_gap")
                yield RadioGroup(_ML4, id=f"{prefix}_r")

        # ── Muscle Activation ─────────────────────────────────────────────────
        yield Label("Muscle Activation", classes="subsection_header", id="ml_activation")
        for label, mid in _MA_ROWS:
            with Horizontal(classes="rm_row"):
                yield Static(label,         classes="rm_lbl")
                yield RadioGroup(_MA4, id=mid)

        # ── Strength — Trunk ──────────────────────────────────────────────────
        yield Label("Strength — Trunk", classes="subsection_header", id="ml_strength_trunk")
        with Horizontal(classes="trunk_row"):
            yield Static("Flexion (crook)",   classes="trunk_lbl")
            yield GridInput(placeholder="reps / min",   id="st_flex", classes="trunk_inp")
        with Horizontal(classes="trunk_row"):
            yield Static("Extension (ball)",  classes="trunk_lbl")
            yield GridInput(placeholder="raises / min", id="st_ext",  classes="trunk_inp")

        # ── Strength — Hip (Wagner FPX kg) ────────────────────────────────────
        yield Label("Strength — Hip  (Wagner FPX kg)", classes="subsection_header", id="ml_strength_hip")
        with Horizontal(classes="hip_hdr"):
            yield Static("",      classes="hip_hdr_lbl")
            yield Static("Left",  classes="hip_hdr_col")
            yield Static("Right", classes="hip_hdr_col")
        for label, prefix in _HIP_ROWS:
            with Horizontal(classes="hip_row"):
                yield Static(label, classes="hip_lbl")
                yield GridInput(placeholder="kg", id=f"{prefix}_l", classes="hip_inp")
                yield GridInput(placeholder="kg", id=f"{prefix}_r", classes="hip_inp")

        # ── SIJ Provocation ───────────────────────────────────────────────────
        yield Label("SIJ Provocation Signs", classes="subsection_header", id="ml_sij")
        with Horizontal(classes="sij_row"):
            for label, sid in _SIJ_ITEMS:
                yield CheckButton(label, id=sid)

        # ── Notes ─────────────────────────────────────────────────────────────
        yield Label("Notes:")
        yield TextArea(id="mu_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # Muscle length grid — RadioGroup up/down nav
        for _, prefix in _ML_ROWS:
            row_idx = len(self._ml_grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._ml_grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._ml_grid_pos[rg_id] = (row_idx, col_idx)

        # Hip strength grid — GridInput.Navigate
        for _, prefix in _HIP_ROWS:
            row_idx = len(self._hip_grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._hip_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._hip_grid_pos[wid] = (row_idx, col_idx)

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._ml_grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._ml_grid_pos[fid]
        target_row = row - 1 if event.key == "up" else row + 1
        if 0 <= target_row < len(self._ml_grid):
            try:
                self.query_one(f"#{self._ml_grid[target_row][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._hip_grid_pos:
            return
        row, col = self._hip_grid_pos[focused.id]
        navigated = False
        if event.direction == "up":
            target_row = row - 1
            if 0 <= target_row < len(self._hip_grid):
                try:
                    self.query_one(f"#{self._hip_grid[target_row][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "down":
            target_row = row + 1
            if 0 <= target_row < len(self._hip_grid):
                try:
                    self.query_one(f"#{self._hip_grid[target_row][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "left" and col > 0:
            try:
                self.query_one(f"#{self._hip_grid[row][col - 1]}").focus()
                navigated = True
            except Exception:
                pass
        elif event.direction == "right" and col < len(self._hip_grid[row]) - 1:
            try:
                self.query_one(f"#{self._hip_grid[row][col + 1]}").focus()
                navigated = True
            except Exception:
                pass
        if not navigated:
            escape_to_neighbor(self, focused, event.direction)
        event.stop()

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(CheckButton.Changed)
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
        for _, sid in _SIJ_ITEMS:
            try:
                data[sid] = self.query_one(f"#{sid}", CheckButton).value
            except Exception:
                data[sid] = None
        for fid in ("st_flex", "st_ext"):
            try:
                data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
            except Exception:
                data[fid] = ""
        for _, prefix in _HIP_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        try:
            data["mu_notes"] = self.query_one("#mu_notes", TextArea).text
        except Exception:
            data["mu_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for _, sid in _SIJ_ITEMS:
                try:
                    self.query_one(f"#{sid}", CheckButton).set_value(data.get(sid))
                except Exception:
                    pass
            for fid in ("st_flex", "st_ext"):
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
            for _, prefix in _HIP_ROWS:
                for side in ("l", "r"):
                    fid = f"{prefix}_{side}"
                    try:
                        self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                    except Exception:
                        pass
            try:
                self.query_one("#mu_notes", TextArea).text = data.get("mu_notes", "")
            except Exception:
                pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#ml_ql_l", RadioGroup).value is not None
        except Exception:
            return False
