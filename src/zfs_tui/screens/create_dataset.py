from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Input, Button, Select
from textual.containers import Horizontal, Vertical
from textual.binding import Binding


class CreateDatasetScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f10", "submit", "Create", key_display="F10"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="create-dataset-layout"):
            yield Label("[bold]Create New Dataset[/]", id="create-dataset-title")
            yield Label("Dataset Name (pool/dataset)")
            yield Input(
                placeholder="e.g., tank/data, pool/home/user",
                id="ds-name-input",
            )

            yield Label("Type")
            yield Select([
                ("Filesystem", "filesystem"),
                ("Volume (zvol)", "volume"),
            ], id="ds-type-select")

            yield Label("Volume Size (only for volumes)")
            yield Input(placeholder="e.g., 10G, 500M", id="volume-size-input")

            yield Label("Mountpoint (optional)")
            yield Input(placeholder="e.g., /mnt/data", id="ds-mountpoint-input")

            yield Label("Properties (optional, key=value pairs)")
            yield Input(
                placeholder="e.g., compression=lz4, quota=100G, atime=off",
                id="ds-properties-input",
            )

            yield Label("Create parent datasets automatically")
            yield Select([
                ("Yes", "yes"),
                ("No", "no"),
            ], id="recursive-select")

            with Horizontal(id="create-dataset-buttons"):
                yield Button("Create Dataset", variant="primary", id="create-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-btn":
            await self._create_dataset()
        elif event.button.id == "cancel-btn":
            self.dismiss()

    async def _create_dataset(self):
        name = self.query_one("#ds-name-input", Input).value.strip()
        ds_type = self.query_one("#ds-type-select", Select).value
        vol_size = self.query_one("#volume-size-input", Input).value.strip()
        mountpoint = self.query_one("#ds-mountpoint-input", Input).value.strip()
        props_str = self.query_one("#ds-properties-input", Input).value.strip()
        recursive = self.query_one("#recursive-select", Select).value == "yes"

        if not name:
            self.app.notify("Dataset name is required", severity="error")
            return

        properties = {}
        if props_str:
            for pair in props_str.split(","):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    properties[k.strip()] = v.strip()

        if mountpoint:
            properties["mountpoint"] = mountpoint

        ctl = self.app.get_zfs_ctl()
        if ds_type == "volume":
            ok, msg = await ctl.create_dataset(
                name,
                properties=properties if properties else None,
                recursive=recursive,
                volume_size=vol_size if vol_size else None,
            )
        else:
            ok, msg = await ctl.create_dataset(
                name,
                properties=properties if properties else None,
                recursive=recursive,
            )
        self.app.notify(msg, severity="information" if ok else "error")
        if ok:
            self.dismiss()

    def action_cancel(self):
        self.dismiss()
