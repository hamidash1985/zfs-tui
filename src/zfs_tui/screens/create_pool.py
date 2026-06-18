import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Input, Button, Select, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding


RAID_LEVELS = [
    ("Striped (RAID0)", "striped"),
    ("Mirror (RAID1)", "mirror"),
    ("RAIDZ1 (single parity)", "raidz1"),
    ("RAIDZ2 (double parity)", "raidz2"),
    ("RAIDZ3 (triple parity)", "raidz3"),
    ("dRAID1", "draid1"),
    ("dRAID2", "draid2"),
    ("dRAID3", "draid3"),
]


class CreatePoolScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("f10", "submit", "Create", key_display="F10"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="create-pool-layout"):
            yield Label("[bold]Create New Pool[/]", id="create-pool-title")
            yield Label("Pool Name")
            yield Input(placeholder="e.g., tank, storage, data", id="pool-name-input")

            yield Label("RAID Level")
            yield Select(RAID_LEVELS, id="raid-select")

            yield Label("Devices (space-separated paths)")
            yield Input(
                placeholder="e.g., /dev/sdb /dev/sdc /dev/sdd",
                id="devices-input",
            )

            yield Label("Mountpoint (optional)")
            yield Input(placeholder="e.g., /mnt/storage", id="mountpoint-input")

            yield Label("Properties (optional, one per line: key=value)")
            yield Input(
                placeholder="e.g., ashift=12, compression=lz4",
                id="properties-input",
            )

            yield Label("Force creation (use if devices appear in use)")
            yield Select([
                ("No", "no"),
                ("Yes", "yes"),
            ], id="force-select")

            with Horizontal(id="create-pool-buttons"):
                yield Button("Create Pool", variant="primary", id="create-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "create-btn":
            await self._create_pool()
        elif event.button.id == "cancel-btn":
            self.dismiss()

    async def _create_pool(self):
        name = self.query_one("#pool-name-input", Input).value.strip()
        raid = self.query_one("#raid-select", Select).value
        devices = self.query_one("#devices-input", Input).value.strip()
        mountpoint = self.query_one("#mountpoint-input", Input).value.strip()
        props_str = self.query_one("#properties-input", Input).value.strip()
        force = self.query_one("#force-select", Select).value == "yes"

        if not name:
            self.app.notify("Pool name is required", severity="error")
            return
        if not devices:
            self.app.notify("At least one device is required", severity="error")
            return

        dev_list = devices.split()
        properties = {}
        if props_str:
            for pair in props_str.split(","):
                pair = pair.strip()
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    properties[k.strip()] = v.strip()

        vdev_spec: list[str] = []
        if raid == "striped":
            vdev_spec = dev_list
        elif raid == "mirror":
            vdev_spec = ["mirror"] + dev_list
        elif raid.startswith("raidz"):
            vdev_spec = [raid] + dev_list
        elif raid.startswith("draid"):
            vdev_spec = [raid] + dev_list

        ctl = self.app.get_zpool_ctl()
        ok, msg = await ctl.create_pool(
            name, vdev_spec,
            properties=properties if properties else None,
            mountpoint=mountpoint if mountpoint else None,
            force=force,
        )
        self.app.notify(msg, severity="information" if ok else "error")
        if ok:
            self.dismiss()

    def action_cancel(self):
        self.dismiss()

    def action_submit(self):
        asyncio.create_task(self._create_pool())
