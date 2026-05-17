from textual.widgets import Button


class FlagButton(Button):
    """
    Clinical FLAG button.

    States:
        0 = blank/orange
        1 = yes/red
        2 = no/green

    Intended meaning:
        YES = danger/problem/flag present
        NO  = clear/safe/flag absent

    This intentionally reverses normal YES/NO colours.
    """

    STATES = [
        ("", "orange"),
        ("Yes", "red"),
        ("No", "green"),
    ]

    def __init__(self, name: str):

        super().__init__(name)

        self.base_name = name
        self.state = 0

        self.update_button()

    def update_button(self):

        text, colour = self.STATES[self.state]

        self.label = (
            self.base_name
            if not text
            else f"{self.base_name} {text}"
        )

        self.styles.background = colour
        self.styles.color = "black"

    def cycle_state(self):

        self.state = (self.state + 1) % 3
        self.update_button()

    async def action_press(self):

        self.cycle_state()

    async def key_y(self):

        self.state = 1
        self.update_button()
        self.screen.focus_next()

    async def key_n(self):

        self.state = 2
        self.update_button()
        self.screen.focus_next()

    @property
    def value(self):

        return [None, True, False][self.state]