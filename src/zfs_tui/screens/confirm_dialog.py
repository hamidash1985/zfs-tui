from typing import Callable, Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button
from textual.containers import Horizontal, Vertical
from textual.binding import Binding


class ConfirmScreen(Screen):
    BINDINGS = [
        Binding("escape", "no", "Cancel"),
        Binding("enter", "yes", "Confirm"),
        Binding("y", "yes", "Yes"),
        Binding("n", "no", "No"),
    ]

    def __init__(self, title: str, message: str,
                 callback: Callable[[bool], None]):
        super().__init__()
        self._confirm_title = title
        self._confirm_message = message
        self._callback = callback

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Label(self._confirm_title, id="confirm-title")
            yield Label(self._confirm_message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Yes", variant="primary", id="yes-button")
                yield Button("No", variant="default", id="no-button")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "yes-button":
            self.action_yes()
        else:
            self.action_no()

    def action_yes(self):
        self._callback(True)
        self.dismiss()

    def action_no(self):
        self._callback(False)
        self.dismiss()
