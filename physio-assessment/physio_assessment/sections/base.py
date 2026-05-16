"""Base class for all assessment sections."""

from textual.containers import ScrollableContainer
from textual.css.query import NoMatches


class BaseSection(ScrollableContainer):

    DEFAULT_CSS = """
    BaseSection { padding-bottom: 2; }
    """
    """Base class for assessment sections.

    Sections must implement load(), collect(), and is_complete() methods.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session_file = ""
        self._loading = False

    def focus_first_field(self) -> None:
        """Focus the first interactive widget in this section."""
        try:
            self.query("Input, TextArea, CheckButton, Button").first().focus()
        except NoMatches:
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
