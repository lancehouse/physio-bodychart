"""Base class for all assessment sections."""

from textual import events
from textual.containers import Container, ScrollableContainer
from textual.css.query import NoMatches
from textual.widgets import Input, TextArea


class BaseSection(Container):

    DEFAULT_CSS = """
    BaseSection { padding-bottom: 2; }

    .subsection_header {
        text-style: bold;
        width: 100%;
        height: auto;
        margin-top: 1;
        margin-bottom: 0;
        background: $primary;
        color: $background;
        border: solid $primary;
        padding: 0 1;
    }

    /* Focus highlight — bright accent ring on every focusable widget type */
    BaseSection Input:focus      { border: tall $accent; }
    BaseSection Button:focus     { border: tall $accent; background: $accent 15%; }

    /* RadioGroup focus is handled inside RadioGroup itself via .-rg-focused class */
    """
    """Base class for assessment sections.

    Sections must implement load(), collect(), and is_complete() methods.
    """

    # Set True in objective sections so arrow-key navigation includes GridInput/Input
    # cells.  Assessment sections leave this False so up/down only moves between
    # button-type widgets (CheckButton, FlagButton, RadioGroup) and skips text fields.
    _nav_include_inputs: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_file = ""
        self._loading = False

    def on_key(self, event: events.Key) -> None:
        """Arrow-key navigation between focusable fields in this section.

        Delegates to nav.find_neighbor which uses section-relative coordinates:
        up/down selects the nearest widget above/below (not DOM order), so a
        3-column button row navigates correctly to the widget directly above.
        Left/right stays within the same horizontal row (strong y-penalty).

        Stops the event only when focus actually moves.  At a section boundary
        (no widget in that direction) the event is not stopped, so the
        ScrollableContainer scrolls instead.

        Sections that define their own on_key (objective grid sections) shadow
        this via Python MRO and take priority.
        """
        if event.key not in ("up", "down", "left", "right"):
            return

        focused = self.app.focused
        # Never navigate away from TextArea or Input — those widgets need their own
        # arrow keys for cursor movement within the field.
        if focused is None or isinstance(focused, (TextArea, Input)):
            return

        # RadioGroup handles left/right internally via key_left/key_right bindings
        try:
            from ..widgets import RadioGroup
            if isinstance(focused, RadioGroup) and event.key in ("left", "right"):
                return
        except Exception:
            pass

        from ..nav import find_neighbor

        # Navigation candidates: TextArea is always excluded (handles its own keys).
        # Input/GridInput are excluded unless _nav_include_inputs is True — objective
        # sections set this True so numeric grid cells are reachable; assessment
        # sections leave it False to avoid landing on mostly-empty text fields.
        candidates = [
            w for w in self.query("*")
            if w.can_focus
            and not isinstance(w, TextArea)
            and (self._nav_include_inputs or not isinstance(w, Input))
        ]
        target = find_neighbor(focused, candidates, event.key, section=self)

        if target is not None:
            target.focus()
            try:
                sc = self.app.query_one("#section_content", ScrollableContainer)
                sc.scroll_to_widget(target, animate=False)
            except Exception:
                pass
            event.stop()

    def on_mount(self) -> None:
        for inp in self.query(Input):
            inp.select_on_focus = False

    def on_show(self) -> None:
        for ta in self.query(TextArea):
            if ta.text and ta.cursor_location == (0, 0):
                lines = ta.text.split("\n")
                ta.cursor_location = (len(lines) - 1, len(lines[-1]))

    def focus_first_field(self) -> None:
        """Focus the first interactive widget in this section."""
        try:
            self.query("Input, TextArea, CheckButton, Button").first().focus()
        except NoMatches:
            pass

    def _focus_first_after(self, anchor_id: str) -> None:
        """Focus and scroll to the first can_focus widget after anchor_id in DOM order."""
        try:
            anchor = self.query_one(f"#{anchor_id}")
            nodes = list(self.query("*"))
            for widget in nodes[nodes.index(anchor) + 1:]:
                if widget.can_focus:
                    widget.focus()
                    try:
                        sc = self.app.query_one("#section_content", ScrollableContainer)
                        sc.scroll_to_widget(widget, animate=False)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    def load(self, data: dict) -> None:
        """Populate section fields from JSON data dict.

        Args:
            data: Dict containing section data (e.g., data["assessment"]["consent"])
        """
        raise NotImplementedError

    def collect(self) -> dict:
        """Collect current field values into a dict ready to save.

        Returns:
            Dict matching the section's data structure
        """
        raise NotImplementedError

    def is_complete(self) -> bool:
        """Check if section is complete according to its completion criteria.

        Returns:
            True if all required fields are filled
        """
        raise NotImplementedError
