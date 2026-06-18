import asyncio
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable, Tree, Label, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from zfs_tui.models.pool import Pool, PoolHealth
from zfs_tui.models.dataset import Dataset, DatasetType
from zfs_tui.screens.pool_detail import PoolDetailScreen
from zfs_tui.screens.dataset_detail import DatasetDetailScreen


class DashboardScreen(Screen):
    BINDINGS = [
        Binding("tab", "focus_next", "Next", show=False),
        Binding("shift+tab", "focus_previous", "Prev", show=False),
        Binding("enter", "select_item", "Select"),
        Binding("r", "refresh_data", "Refresh", key_display="R"),
        Binding("d", "destroy_pool", "Destroy", key_display="D"),
        Binding("e", "export_pool", "Export", key_display="E"),
        Binding("/", "search", "Search", key_display="/"),
    ]

    pools: list[Pool] = []
    datasets: list[Dataset] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label(id="host-indicator")
        with Horizontal(id="main-layout"):
            with Vertical(id="pool-panel"):
                yield Label("Pools", id="pool-panel-title")
                yield DataTable(id="pool-table", cursor_type="row")
                yield Static(id="pool-actions",
                             markup="[bold]Actions:[/] [yellow]D[/]estroy  "
                                    "[yellow]E[/]xport  [yellow]Enter[/] detail")
            with Vertical(id="dataset-panel"):
                yield Label("Datasets", id="dataset-panel-title")
                yield Tree("Datasets", id="dataset-tree")
                yield Static(id="dataset-actions",
                             markup="[bold]Actions:[/] [yellow]Enter[/] detail")
        yield Footer()

    async def on_mount(self):
        self._setup_pool_table()
        await self.refresh_data()

    def _setup_pool_table(self):
        table = self.query_one("#pool-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Name", "Size", "Alloc", "Free", "Cap", "Health", "Host")

    async def refresh_data(self):
        ctl = self.app.get_zpool_ctl()
        zfs_ctl = self.app.get_zfs_ctl()

        self.pools = await ctl.list_pools()
        detailed = await ctl.get_all_pools_status()
        for pool in self.pools:
            if pool.name in detailed:
                d = detailed[pool.name]
                pool.vdevs = d.vdevs
                pool.scan = d.scan
                pool.errors = d.errors
                pool.health = d.health

        self.datasets = await zfs_ctl.list_datasets(recursive=True)

        self._update_pool_table()
        self._update_dataset_tree()

        host = self.app.current_host
        indicator = self.query_one("#host-indicator", Label)
        indicator.update(f"Connected: [bold green]{host}[/]")
        indicator.styles.background = "green" if host == "localhost" else "blue"

    def _update_pool_table(self):
        table = self.query_one("#pool-table", DataTable)
        table.clear()
        health_icons = {
            PoolHealth.ONLINE: "●",
            PoolHealth.DEGRADED: "◐",
            PoolHealth.FAULTED: "○",
            PoolHealth.OFFLINE: "○",
            PoolHealth.UNAVAIL: "✕",
            PoolHealth.REMOVED: "○",
            PoolHealth.SUSPENDED: "◌",
        }
        for pool in self.pools:
            icon = health_icons.get(pool.health, "?")
            health_str = f"[{pool.health_color}]{icon} {pool.health.value}[/]"
            table.add_row(
                pool.name,
                pool.size,
                pool.allocated,
                pool.free,
                pool.capacity,
                health_str,
                pool.host,
            )

    def _update_dataset_tree(self):
        tree = self.query_one("#dataset-tree", Tree)
        tree.clear()
        root = tree.root

        pool_map: dict[str, list[Dataset]] = {}
        for ds in self.datasets:
            pool_map.setdefault(ds.pool, []).append(ds)

        for pool_name in sorted(pool_map.keys()):
            pool_ds = pool_map[pool_name]
            pool_node = root.add(
                f"[bold]{pool_name}[/]", expand=True,
            )
            top_level = [d for d in pool_ds if d.depth == 1]
            for ds in sorted(top_level, key=lambda d: d.name):
                self._add_ds_to_tree(pool_node, ds, pool_ds)

    def _add_ds_to_tree(self, parent_node, ds: Dataset,
                        all_ds: list[Dataset]):
        icon = "📁" if ds.type == DatasetType.FILESYSTEM else "💿"
        label = f"{icon} {ds.short_name}  [{ds.properties.used}]"
        node = parent_node.add(label, data=ds.name)
        children = [d for d in all_ds
                    if d.name.startswith(ds.name + "/")
                    and d.depth == ds.depth + 1]
        for child in sorted(children, key=lambda d: d.name):
            self._add_ds_to_tree(node, child, all_ds)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        table = self.query_one("#pool-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.pools):
            pool = self.pools[table.cursor_row]
            self.app.push_screen(
                PoolDetailScreen(pool_name=pool.name)
            )

    def on_tree_node_selected(self, event: Tree.NodeSelected):
        node = event.node
        if node.data and isinstance(node.data, str):
            self.app.push_screen(
                DatasetDetailScreen(dataset_name=node.data)
            )

    async def action_select_item(self):
        focused = self.focused
        if focused and focused.id == "pool-table":
            table = self.query_one("#pool-table", DataTable)
            if table.cursor_row is not None and table.cursor_row < len(self.pools):
                pool = self.pools[table.cursor_row]
                await self.app.push_screen(
                    PoolDetailScreen(pool_name=pool.name)
                )
        elif focused and focused.id == "dataset-tree":
            tree = self.query_one("#dataset-tree", Tree)
            node = tree.cursor_node
            if node and node != tree.root and node.data:
                await self.app.push_screen(
                    DatasetDetailScreen(dataset_name=node.data)
                )

    async def action_destroy_pool(self):
        table = self.query_one("#pool-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.pools):
            pool = self.pools[table.cursor_row]
            confirmed = await self.app.confirm_dialog(
                f"Destroy pool '{pool.name}'?",
                f"This will destroy pool '{pool.name}' and all its data.\n"
                "This action cannot be undone!",
            )
            if confirmed:
                ctl = self.app.get_zpool_ctl()
                ok, msg = await ctl.destroy_pool(pool.name, force=True)
                self.app.notify(msg, severity="information" if ok else "error")
                await self.refresh_data()

    async def action_export_pool(self):
        table = self.query_one("#pool-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.pools):
            pool = self.pools[table.cursor_row]
            ctl = self.app.get_zpool_ctl()
            ok, msg = await ctl.export_pool(pool.name)
            self.app.notify(msg, severity="information" if ok else "error")
            await self.refresh_data()

    async def action_search(self):
        table = self.query_one("#pool-table", DataTable)
        pool_count = len(self.pools)
        if pool_count > 0:
            current = table.cursor_row or 0
            next_row = (current + 1) % pool_count
            table.move_cursor(row=next_row)
