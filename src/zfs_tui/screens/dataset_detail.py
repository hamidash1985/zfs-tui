import asyncio
import time
from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, DataTable, Input, Button, Static
from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane
from textual.binding import Binding

from zfs_tui.models.dataset import Dataset, DatasetType
from zfs_tui.models.snapshot import Snapshot


class DatasetDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("f5", "refresh_data", "Refresh"),
        Binding("s", "snapshot", "Snapshot", key_display="S"),
        Binding("r", "rollback", "Rollback", key_display="R"),
        Binding("c", "clone", "Clone", key_display="C"),
        Binding("d", "destroy", "Destroy", key_display="D"),
        Binding("m", "mount", "Mount/Unmount", key_display="M"),
        Binding("e", "edit_properties", "Properties", key_display="E"),
        Binding("b", "bookmark", "Bookmark", key_display="B"),
    ]

    dataset_name: str = ""
    dataset: Optional[Dataset] = None

    def __init__(self, dataset_name: str = ""):
        super().__init__()
        self.dataset_name = dataset_name

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="dataset-detail-layout"):
            yield Label(id="dataset-detail-title")
            with TabbedContent(id="dataset-detail-tabs"):
                with TabPane("Info", id="info-tab"):
                    yield Static(id="dataset-info")
                    yield Label("Properties", id="props-title")
                    yield DataTable(id="dataset-properties-table", cursor_type="row")
                with TabPane("Snapshots", id="snapshots-tab"):
                    yield DataTable(id="snapshots-table", cursor_type="row")
                    with Horizontal(id="snapshot-actions"):
                        yield Button("Snapshot", variant="primary", id="snap-btn")
                        yield Button("Rollback", variant="warning", id="rollback-btn")
                        yield Button("Clone", variant="default", id="clone-btn")
                        yield Button("Delete Snap", variant="error", id="delete-snap-btn")
                with TabPane("Clones & Bookmarks", id="clones-tab"):
                    yield DataTable(id="clones-table", cursor_type="row")
                    yield Label("Bookmarks", id="bookmarks-title")
                    yield DataTable(id="bookmarks-table", cursor_type="row")
        yield Footer()

    async def on_mount(self):
        self._setup_tables()
        await self.refresh_data()

    def _setup_tables(self):
        props_table = self.query_one("#dataset-properties-table", DataTable)
        props_table.clear(columns=True)
        props_table.add_columns("Property", "Value", "Source")

        snaps_table = self.query_one("#snapshots-table", DataTable)
        snaps_table.clear(columns=True)
        snaps_table.add_columns("Name", "Created", "Used", "Referenced")

        clones_table = self.query_one("#clones-table", DataTable)
        clones_table.clear(columns=True)
        clones_table.add_columns("Name", "Origin")

        bm_table = self.query_one("#bookmarks-table", DataTable)
        bm_table.clear(columns=True)
        bm_table.add_columns("Name", "Created")

    async def refresh_data(self):
        zfs_ctl = self.app.get_zfs_ctl()
        datasets = await zfs_ctl.list_datasets(recursive=True)
        for ds in datasets:
            if ds.name == self.dataset_name:
                self.dataset = ds
                break
        if self.dataset:
            self._update_display()

    def _update_display(self):
        if not self.dataset:
            return

        ds = self.dataset
        title = self.query_one("#dataset-detail-title", Label)
        host = self.app.current_host or "localhost"
        title.update(f"[bold]{ds.name}[/] @ {host}")

        info = self.query_one("#dataset-info", Static)
        p = ds.properties
        info_str = (
            f"[bold]Type:[/] {ds.type.value}  "
            f"[bold]Used:[/] {p.used}  "
            f"[bold]Available:[/] {p.available}  "
            f"[bold]Referenced:[/] {p.referenced}  "
            f"[bold]Mountpoint:[/] {p.mountpoint}  "
            f"[bold]Compression:[/] {p.compression}  "
            f"[bold]Compressratio:[/] {p.compressratio}"
        )
        if ds.origin:
            info_str += f"  [bold]Origin:[/] {ds.origin}"
        info.update(info_str)

        self._update_properties()
        asyncio.create_task(self._update_snapshots())

    def _update_properties(self):
        table = self.query_one("#dataset-properties-table", DataTable)
        table.clear()
        if not self.dataset:
            return
        p = self.dataset.properties
        props = {
            "name": self.dataset.name,
            "type": self.dataset.type.value,
            "used": p.used,
            "available": p.available,
            "referenced": p.referenced,
            "compressratio": p.compressratio,
            "compression": p.compression,
            "mountpoint": p.mountpoint,
            "quota": p.quota,
            "reservation": p.reservation,
            "recordsize": p.recordsize,
            "atime": p.atime,
            "relatime": p.relatime,
            "encryption": p.encryption,
            "checksum": p.checksum,
            "dedup": p.dedup,
            "copies": p.copies,
            "refquota": p.refquota,
            "refreservation": p.refreservation,
        }
        if self.dataset.origin:
            props["origin"] = self.dataset.origin
        for k, v in props.items():
            table.add_row(k, str(v), "local")

    async def _update_snapshots(self):
        if not self.dataset:
            return
        zfs_ctl = self.app.get_zfs_ctl()
        snapshots = await zfs_ctl.list_snapshots(
            self.dataset.name, recursive=True
        )
        table = self.query_one("#snapshots-table", DataTable)
        table.clear()
        for snap in snapshots:
            table.add_row(
                snap.short_name, snap.creation,
                snap.used, snap.referenced,
            )

    async def action_snapshot(self):
        if not self.dataset:
            return
        zfs_ctl = self.app.get_zfs_ctl()
        snap_name = f"{self.dataset.name}@{time.strftime('%Y%m%d-%H%M%S')}"
        ok, msg = await zfs_ctl.create_snapshot(snap_name)
        self.app.notify(msg, severity="information" if ok else "error")
        await self._update_snapshots()

    async def action_rollback(self):
        if not self.dataset:
            return
        table = self.query_one("#snapshots-table", DataTable)
        if table.cursor_row is not None:
            snaps_table = self.query_one("#snapshots-table", DataTable)
            if snaps_table.rows:
                row_keys = list(snaps_table.rows.keys())
                if snaps_table.cursor_row < len(row_keys):
                    row_key = row_keys[snaps_table.cursor_row]
                    row = snaps_table.rows[row_key]
                    snap_name = f"{self.dataset.name}@{row.label}"
                    confirmed = await self.app.confirm_dialog(
                        f"Rollback to '{snap_name}'?",
                        "This will discard all changes since the snapshot.",
                    )
                    if confirmed:
                        zfs_ctl = self.app.get_zfs_ctl()
                        ok, msg = await zfs_ctl.rollback_snapshot(
                            snap_name, destroy_older=True
                        )
                        self.app.notify(
                            msg, severity="information" if ok else "error"
                        )
                        await self.refresh_data()

    async def action_clone(self):
        if not self.dataset:
            return
        table = self.query_one("#snapshots-table", DataTable)
        if table.cursor_row is not None:
            row_keys = list(table.rows.keys())
            if table.cursor_row < len(row_keys):
                snap_name = f"{self.dataset.name}@{row_keys[table.cursor_row]}"
                clone_name = f"{self.dataset.name}/clone_{row_keys[table.cursor_row]}"
                zfs_ctl = self.app.get_zfs_ctl()
                ok, msg = await zfs_ctl.clone_snapshot(snap_name, clone_name)
                self.app.notify(
                    msg, severity="information" if ok else "error"
                )
                await self.refresh_data()

    async def action_destroy(self):
        if not self.dataset:
            return
        confirmed = await self.app.confirm_dialog(
            f"Destroy dataset '{self.dataset.name}'?",
            f"This will destroy '{self.dataset.name}' and may cause data loss.",
        )
        if confirmed:
            zfs_ctl = self.app.get_zfs_ctl()
            ok, msg = await zfs_ctl.destroy_dataset(
                self.dataset.name, recursive=True
            )
            self.app.notify(msg, severity="information" if ok else "error")
            self.dismiss()

    async def action_mount(self):
        if not self.dataset:
            return
        zfs_ctl = self.app.get_zfs_ctl()
        p = self.dataset.properties
        if p.mountpoint == "/" or p.mountpoint.startswith("/"):
            ok, msg = await zfs_ctl.mount_dataset(self.dataset.name)
        else:
            ok, msg = await zfs_ctl.unmount_dataset(self.dataset.name)
        self.app.notify(msg, severity="information" if ok else "error")

    async def action_bookmark(self):
        if not self.dataset:
            return
        table = self.query_one("#snapshots-table", DataTable)
        if table.cursor_row is not None:
            row_keys = list(table.rows.keys())
            if table.cursor_row < len(row_keys):
                snap_name = f"{self.dataset.name}@{row_keys[table.cursor_row]}"
                bm_name = f"{self.dataset.name}#{row_keys[table.cursor_row]}"
                zfs_ctl = self.app.get_zfs_ctl()
                ok, msg = await zfs_ctl.bookmark_snapshot(snap_name, bm_name)
                self.app.notify(
                    msg, severity="information" if ok else "error"
                )

    async def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "snap-btn":
            await self.action_snapshot()
        elif btn_id == "rollback-btn":
            await self.action_rollback()
        elif btn_id == "clone-btn":
            await self.action_clone()
        elif btn_id == "delete-snap-btn":
            table = self.query_one("#snapshots-table", DataTable)
            if table.cursor_row is not None and self.dataset:
                row_keys = list(table.rows.keys())
                if table.cursor_row < len(row_keys):
                    snap_name = f"{self.dataset.name}@{row_keys[table.cursor_row]}"
                    confirmed = await self.app.confirm_dialog(
                        f"Delete snapshot '{snap_name}'?",
                        "This cannot be undone.",
                    )
                    if confirmed:
                        zfs_ctl = self.app.get_zfs_ctl()
                        ok, msg = await zfs_ctl.destroy_dataset(snap_name)
                        self.app.notify(
                            msg, severity="information" if ok else "error"
                        )
                        await self._update_snapshots()

    def action_back(self):
        self.dismiss()

    def action_edit_properties(self):
        self.app.notify("Edit properties: use 'zfs set' from the command line", timeout=5)
