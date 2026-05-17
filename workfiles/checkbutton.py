from textual.widgets import Button


class CheckButton(Button):
    """
    Lightweight 3-state clinical toggle button for Textual.

    States:
        0 = blank/orange
        1 = yes/green
        2 = no/red

    Controls:
        Enter / Space  -> cycle states
        Y              -> set YES and move focus forward
        N              -> set NO and move focus forward

    Example:
        CheckButton("Consent")

    Resulting labels:
        "Consent"
        "Consent Yes"
        "Consent No"
    """

    # Ordered list of states:
    # (label_suffix, background_colour)
    STATES = [
        ("", "orange"),
        ("Yes", "green"),
        ("No", "red"),
    ]

    def __init__(self, name: str):
        """
        Args:
            name:
                Base field label shown on the button.
                Example: "Pain", "Weakness", "Numbness"
        """

        # Initial button label
        super().__init__(name)

        # Permanent base label text
        self.base_name = name

        # Current state index:
        # 0=blank, 1=yes, 2=no
        self.state = 0

        # Apply initial appearance
        self.update_button()

    def update_button(self):
        """
        Refresh visible label and colours
        based on current state.
        """

        text, colour = self.STATES[self.state]

        # Blank state shows only field name
        if text:
            self.label = f"{self.base_name} {text}"
        else:
            self.label = self.base_name

        # Background colour by state
        self.styles.background = colour

        # Keep text readable
        self.styles.color = "black"

    def cycle_state(self):
        """
        Advance through:
            blank -> yes -> no -> blank
        """

        self.state = (self.state + 1) % 3
        self.update_button()

    async def action_press(self):
        """
        Called automatically by:
            - Enter
            - Space
            - Mouse click
        """

        self.cycle_state()

    async def key_y(self):
        """
        Keyboard shortcut:
            Y -> YES + next field
        """

        self.state = 1
        self.update_button()
        self.screen.focus_next()

    async def key_n(self):
        """
        Keyboard shortcut:
            N -> NO + next field
        """

        self.state = 2
        self.update_button()
        self.screen.focus_next()

    @property
    def value(self):
        """
        Clean logical value for exporting.

        Returns:
            None   -> blank
            True   -> yes
            False  -> no
        """

        return [None, True, False][self.state]