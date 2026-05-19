"""Shared clinical toggle button widgets."""

from textual.app import ComposeResult, on
from textual.containers import Container
from textual.message import Message
from textual import events
from textual.widgets import Button, Input, Label, Static


# ---------------------------------------------------------------------------
# GridInput — Input that posts Navigate on boundaries for grid arrow-key nav
# ---------------------------------------------------------------------------

class GridInput(Input):
    """Input that posts Navigate messages at cursor boundaries instead of doing nothing."""

    class Navigate(Message):
        def __init__(self, direction: str) -> None:
            super().__init__()
            self.direction = direction

    def _on_key(self, event: events.Key) -> None:
        key = event.key
        if key in ("up", "down"):
            self.post_message(self.Navigate(key))
            event.stop()
            return
        if key == "left" and self.cursor_position == 0:
            self.post_message(self.Navigate("left"))
            event.stop()
            return
        if key == "right" and self.cursor_position >= len(self.value):
            self.post_message(self.Navigate("right"))
            event.stop()
            return
        super()._on_key(event)


# ---------------------------------------------------------------------------
# RadioGroup — exclusive single-select button gang
# ---------------------------------------------------------------------------

class _RadioButton(Button):
    """Non-focusable button inside RadioGroup. Click bubbles up; keyboard ignored."""

    can_focus = False


    class Clicked(Message):
        def __init__(self, button: "Button") -> None:
            super().__init__()
            self.button = button

    async def _on_click(self, event: events.Click) -> None:
        event.stop()
        self.post_message(self.Clicked(self))


class RadioGroup(Static):
    """Exclusive single-select button gang — one tab stop for the whole group.

    options: list of (label, variant) pairs. The outer Static carries the data
    key via id=. Each button is exactly 6 cells wide; the gang width is automatic.

    Left/Right   → select previous/next option.
    Enter/Space/Y → advance focus to next field (selection stays).
    Tab           → advance focus (Textual default, no override needed).
    Click/tap     → select that button, focus returns to the group.
    """

    can_focus = True

    class Changed(Message):
        pass

    DEFAULT_CSS = """
    RadioGroup             { height: 3; layout: horizontal; width: auto; }
    RadioGroup Button      { height: 3; width: 6; min-width: 6; max-width: 6; padding: 0; border: none; }
    RadioGroup.-rg-focused { border: tall $accent; }
    RadioGroup.-rg-focused Button { height: 1; min-height: 1; }
    """

    def __init__(self, options: list[tuple[str, str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._options = options
        self._selected: int | None = None

    @property
    def value(self) -> str | None:
        if self._selected is None:
            return None
        return self._options[self._selected][0]

    def compose(self) -> ComposeResult:
        for i, (label, _) in enumerate(self._options):
            yield _RadioButton(label, variant="default", id=f"{self.id}_r{i}")

    def _select(self, idx: int) -> None:
        self._selected = idx
        for i, (_, variant) in enumerate(self._options):
            try:
                btn = self.query_one(f"#{self.id}_r{i}", _RadioButton)
                if i == idx:
                    # "default" variant is visually identical to unselected;
                    # use "primary" so selection is always visible.
                    btn.variant = variant if variant != "default" else "primary"
                else:
                    btn.variant = "default"
            except Exception:
                pass
        self.post_message(self.Changed())

    @on(_RadioButton.Clicked)
    def _on_btn_clicked(self, event: _RadioButton.Clicked) -> None:
        for i in range(len(self._options)):
            if event.button.id == f"{self.id}_r{i}":
                if i == self._selected:
                    self._deselect()
                else:
                    self._select(i)
                self.focus()
                return

    def _deselect(self) -> None:
        self._selected = None
        for i in range(len(self._options)):
            try:
                self.query_one(f"#{self.id}_r{i}", _RadioButton).variant = "default"
            except Exception:
                pass
        self.post_message(self.Changed())

    def key_left(self) -> None:
        if self._selected is None:
            self._select(len(self._options) - 1)
        else:
            self._select(max(0, self._selected - 1))

    def key_right(self) -> None:
        if self._selected is None:
            self._select(0)
        else:
            self._select(min(len(self._options) - 1, self._selected + 1))

    def key_enter(self) -> None:
        self.screen.focus_next()

    def key_space(self) -> None:
        self.screen.focus_next()

    async def key_y(self) -> None:
        self.screen.focus_next()

    def on_focus(self) -> None:
        self.add_class("-rg-focused")

    def on_blur(self) -> None:
        self.remove_class("-rg-focused")

    def set_value(self, value: str | None) -> None:
        if value is None:
            self._selected = None
            for i in range(len(self._options)):
                try:
                    self.query_one(f"#{self.id}_r{i}", _RadioButton).variant = "default"
                except Exception:
                    pass
            return
        for i, (label, _) in enumerate(self._options):
            if label == value:
                self._select(i)
                return
        self._selected = None


# ---------------------------------------------------------------------------
# CycleButton — generalised cycling state widget
# ---------------------------------------------------------------------------

class CycleButton(Static):
    """Click cycles through (label, variant) state pairs.

    The outer Static carries the data key via its id=.  The inner Button gets
    id f"{self.id}_btn" when an id is provided — this lets grid-nav code track
    which Button belongs to which cell without a separate lookup table.

    Width must be set by caller; the shared convention is width: 25% (≤¼ rule).
    """

    class Changed(Message):
        pass

    DEFAULT_CSS = """
    CycleButton        { width: 25%; height: 3; }
    CycleButton Button { width: 100%; height: 3; min-width: 0; }
    """

    def __init__(self, states: list[tuple[str, str]], **kwargs) -> None:
        super().__init__(**kwargs)
        self._states: list[tuple[str | None, str]] = [(None, "default")] + list(states)
        self._idx = 0

    @property
    def value(self) -> str | None:
        return self._states[self._idx][0]

    def compose(self) -> ComposeResult:
        btn_id = f"{self.id}_btn" if self.id else None
        yield Button("·", variant="default", id=btn_id)

    def _apply(self) -> None:
        label, variant = self._states[self._idx]
        try:
            btn = self.query_one(Button)
            btn.label   = "·" if label is None else label
            btn.variant = variant
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._idx = (self._idx + 1) % len(self._states)
        self._apply()
        self.post_message(self.Changed())
        event.stop()

    def set_value(self, value: str | None) -> None:
        for i, (lbl, _) in enumerate(self._states):
            if lbl == value:
                self._idx = i
                self._apply()
                return
        self._idx = 0
        self._apply()


class CheckButton(Button):
    """
    3-state clinical toggle: blank/orange → Yes/green → No/red.

    Click or Enter/Space cycles state.
    Y key: set Yes + advance focus.
    N key: set No + advance focus.

    Use for positive-good questions (consent, framing checks).
    """

    STATES = [
        ("", "#FFBF00"),      # unanswered
        ("Yes", "green"),    # confirmed yes
        ("No", "red"),       # confirmed no
    ]

    class Changed(Message):
        """Posted when state changes."""
        def __init__(self, button: "CheckButton") -> None:
            super().__init__()
            self.button = button

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.base_name = name
        self.state = 0

    def on_mount(self) -> None:
        self._apply()

    def _apply(self) -> None:
        suffix, colour = self.STATES[self.state]
        self.label = f"{self.base_name} {suffix}".rstrip() if suffix else self.base_name
        self.styles.background = colour
        self.styles.color = "black"

    def _cycle(self) -> None:
        self.state = (self.state + 1) % 3
        self._apply()
        self.post_message(self.Changed(self))

    # Override both entry points so click AND keyboard both cycle
    async def _on_click(self, event) -> None:
        event.stop()
        if not self.has_class("-active"):
            self._start_active_affect()
            self._cycle()

    def action_press(self) -> None:
        if not self.has_class("-active"):
            self._start_active_affect()
            self._cycle()

    async def key_y(self) -> None:
        if self.state != 1:
            self.state = 1
            self._apply()
            self.post_message(self.Changed(self))
        self.screen.focus_next()

    async def key_n(self) -> None:
        if self.state != 2:
            self.state = 2
            self._apply()
            self.post_message(self.Changed(self))
        self.screen.focus_next()

    def set_value(self, value: bool | None) -> None:
        """Load a stored value without emitting Changed."""
        self.state = 1 if value is True else 2 if value is False else 0
        self._apply()

    @property
    def value(self) -> bool | None:
        return [None, True, False][self.state]


class FlagButton(CheckButton):
    """
    3-state flag button: blank/orange → Yes/red → No/green.

    Reversed colours: YES = flag/danger present, NO = safe/clear.
    Use for red-flag and screening questions.
    """

    STATES = [
        ("", "#FFBF00"),     # unanswered
        ("Yes", "red"),     # flag present — danger
        ("No", "green"),    # flag absent — safe
    ]


class YesNoField(Container):
    """Label + toggle button showing YES/NO/?.

    Kept for backward compatibility with sections that haven't migrated
    to CheckButton yet. New sections should use CheckButton directly.
    """

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

    class Changed(Message):
        pass

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
        return self._value

    def set_value(self, value: bool | None) -> None:
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
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_toggle":
            if self._value is True:
                self.set_value(False)
            elif self._value is False:
                self.set_value(None)
            else:
                self.set_value(True)
            self.post_message(YesNoField.Changed())
            event.stop()
