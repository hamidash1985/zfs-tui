import asyncio
from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Static, DataTable, Tree, Input, Button
from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane
from textual.binding import Binding

from zfs_tui.models.pool import Pool, PoolHealth, Vdev
from zfs_tui.models.dataset import Dataset


class PoolDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("f5", "refresh_data", "Refresh"),
        Binding("s", "scrub", "Scrub"),
        Binding("t", "trim", "Trim"),
        Binding("c", "clear_errors", "Clear Errors"),
        Binding("o", "export", "Export"),
        Binding("d", "destroy", "Destroy"),
        Binding("e", "edit_properties", "Properties"),
    ]

    pool_name: str = ""
    pool: Optional[Pool] = None

    def __init__(self, pool_name: str = ""):
        super().__init__()
        self.pool_name = pool_name

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="pool-detail-layout"):
            yield Label(id="pool-detail-title")
            with TabbedContent(id="pool-detail-tabs"):
                with TabPane("Status", id="status-tab"):
                    yield Label(id="pool-health-display")
                    yield Static(id="pool-scan-status")
                    yield Static(id="pool-errors")
                    yield Label("VDEV Layout", id="vdev-title")
                    yield Tree("VDEVs", id="vdev-tree")
                with TabPane("Properties", id="properties-tab"):
                    yield DataTable(id="pool-properties-table", cursor_type="row")
                    with Horizontal(id="prop-edit-row"):
                        yield Input(placeholder="Property", id="prop-name-input")
                        yield Input(placeholder="Value", id="prop-value-input")
                        yield Button("Set", variant="primary", id="set-prop-btn")
                with TabPane("I/O Stats", id="iostat-tab"):
                    yield DataTable(id="iostat-table")
                    yield Label("Press F5 to refresh", id="iostat-hint")
                with TabPane("Datasets", id="datasets-tab"):
                    yield DataTable(id="pool-datasets-table", cursor_type="row")
        yield Footer()

    async def on_mount(self):
        self._setup_properties_table()
        self._setup_iostat_table()
        await self.refresh_data()

    def _setup_properties_table(self):
        table = self.query_one("#pool-properties-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Property", "Value", "Source")

    def _setup_iostat_table(self):
        table = self.query_one("#iostat-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Device", "r/s", "w/s", "rKB/s", "wKB/s")

    async def refresh_data(self):
        ctl = self.app.get_zpool_ctl()
        pool = await ctl.get_pool_status(self.pool_name)
        if pool:
            self.pool = pool
            self._update_display()

    def _update_display(self):
        if not self.pool:
            return

        title = self.query_one("#pool-detail-title", Label)
        name = self.pool.name
        host = self.app.current_host or "localhost"
        title.update(f"[bold]{name}[/] @ {host}")

        health_label = self.query_one("#pool-health-display", Label)
        icon = {
            PoolHealth.ONLINE: "●", PoolHealth.DEGRADED: "◐",
            PoolHealth.FAULTED: "○", PoolHealth.OFFLINE: "○",
        }.get(self.pool.health, "?")
        health_label.update(
            f"Health: [{self.pool.health_color}]{icon} {self.pool.health.value}[/]  "
            f"Size: {self.pool.size}  "
            f"Alloc: {self.pool.allocated}  "
            f"Free: {self.pool.free}  "
            f"Cap: {self.pool.capacity}"
        )

        scan_label = self.query_one("#pool-scan-status", Static)
        scan_label.update(
            f"[bold]Scan:[/] {self.pool.scan or 'No recent scan'}"
        )

        errors_label = self.query_one("#pool-errors", Static)
        errors_label.update(
            f"[bold]Errors:[/] {self.pool.errors or 'No errors'}"
        )

        self._update_vdev_tree()
        self._update_properties_table()
        asyncio.create_task(self._update_iostat())
        asyncio.create_task(self._update_datasets_table())

    def _update_vdev_tree(self):
        tree = self.query_one("#vdev-tree", Tree)
        tree.clear()
        if not self.pool:
            return
        root = tree.root
        for vdev in self.pool.vdevs:
            self._add_vdev_node(root, vdev)

    def _add_vdev_node(self, parent, vdev: Vdev):
        state_color = {
            "ONLINE": "green", "DEGRADED": "yellow",
            "FAULTED": "red", "OFFLINE": "gray",
        }.get(vdev.state.upper(), "white")
        label = (
            f"[{state_color}]{vdev.name}[/]  "
            f"[dim]{vdev.type}[/]  "
            f"[{state_color}]{vdev.state}[/]"
        )
        if vdev.read_errors or vdev.write_errors or vdev.checksum_errors:
            label += (
                f"  [red]R:{vdev.read_errors} W:{vdev.write_errors} "
                f"C:{vdev.checksum_errors}[/]"
            )
        node = parent.add(label)
        for child in vdev.children:
            self._add_vdev_node(node, child)

    def _update_properties_table(self):
        table = self.query_one("#pool-properties-table", DataTable)
        table.clear()
        if not self.pool:
            return
        props = {
            "name": self.pool.name,
            "size": self.pool.size,
            "allocated": self.pool.allocated,
            "free": self.pool.free,
            "fragmentation": self.pool.fragmentation,
            "capacity": self.pool.capacity,
            "dedupratio": self.pool.dedup_ratio,
            "health": self.pool.health.value,
        }
        props.update(self.pool.properties)
        for k, v in props.items():
            table.add_row(k, str(v), "local")

    async def _update_iostat(self):
        ctl = self.app.get_zpool_ctl()
        stats = await ctl.get_iostat(self.pool_name)
        table = self.query_one("#iostat-table", DataTable)
        table.clear()
        for stat in stats:
            table.add_row(
                stat.get("name", stat.get("device", "-")),
                stat.get("r/s", "-"), stat.get("w/s", "-"),
                stat.get("rKB/s", "-"), stat.get("wKB/s", "-"),
            )

    async def _update_datasets_table(self):
        zfs_ctl = self.app.get_zfs_ctl()
        datasets = await zfs_ctl.list_datasets(recursive=True)
        pool_ds = [d for d in datasets if d.pool == self.pool_name]
        table = self.query_one("#pool-datasets-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Used", "Available", "Mountpoint", "Compression")
        for ds in pool_ds:
            table.add_row(
                ds.name,
                ds.properties.used,
                ds.properties.available,
                ds.properties.mountpoint,
                ds.properties.compression,
            )

    async def action_scrub(self):
        if self.pool:
            ctl = self.app.get_zpool_ctl()
            ok, msg = await ctl.scrub_pool(self.pool.name)
            self.app.notify(msg, severity="information" if ok else "error")
            await self.refresh_data()

    async def action_trim(self):
        if self.pool:
            ctl = self.app.get_zpool_ctl()
            ok, msg = await ctl.trim_pool(self.pool.name)
            self.app.notify(msg, severity="information" if ok else "error")

    async def action_clear_errors(self):
        if self.pool:
            ctl = self.app.get_zpool_ctl()
            ok, msg = await ctl.clear_errors(self.pool.name)
            self.app.notify(msg, severity="information" if ok else "error")
            await self.refresh_data()

    async def action_export(self):
        if self.pool:
            ctl = self.app.get_zpool_ctl()
            ok, msg = await ctl.export_pool(self.pool.name)
            self.app.notify(msg, severity="information" if ok else "error")
            self.dismiss()

    async def action_destroy(self):
        if self.pool:
            confirmed = await self.app.confirm_dialog(
                f"Destroy pool '{self.pool.name}'?",
                f"This will permanently destroy pool '{self.pool.name}' "
                f"and all data on it.\nThis cannot be undone!",
            )
            if confirmed:
                ctl = self.app.get_zpool_ctl()
                ok, msg = await ctl.destroy_pool(self.pool.name, force=True)
                self.app.notify(msg, severity="information" if ok else "error")
                self.dismiss()

    async def action_edit_properties(self):
        tab = self.query_one("#properties-tab")
        inputs = self.query(".prop-edit-input")
        for inp in inputs:
            inp.focus()

    async def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "set-prop-btn":
            prop_input = self.query_one("#prop-name-input", Input)
            val_input = self.query_one("#prop-value-input", Input)
            if prop_input.value and val_input.value and self.pool:
                ctl = self.app.get_zpool_ctl()
                ok, msg = await ctl.set_property(
                    self.pool.name, prop_input.value, val_input.value
                )
                self.app.notify(msg, severity="information" if ok else "error")
                prop_input.value = ""
                val_input.value = ""
                await self.refresh_data()

    def action_back(self):
        self.dismiss()
