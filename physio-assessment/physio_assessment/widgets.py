"""Shared clinical toggle button widgets."""

from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import Button, Label


class CheckButton(Button):
    """
    3-state clinical toggle: blank/orange → Yes/green → No/red.

    Click or Enter/Space cycles state.
    Y key: set Yes + advance focus.
    N key: set No + advance focus.

    Use for positive-good questions (consent, framing checks).
    """

    STATES = [
        ("", "orange"),      # unanswered
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
        ("", "orange"),     # unanswered
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
