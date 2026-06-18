from typing import Optional
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Input, Button, DataTable, Static
from textual.containers import Horizontal, Vertical
from textual.binding import Binding

from zfs_tui.utils.config import SshHostConfig
from zfs_tui.controllers.ssh_ctl import SshConnection


class ConnectionManagerScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("f5", "refresh_data", "Refresh"),
        Binding("c", "connect", "Connect", key_display="C"),
        Binding("d", "delete_host", "Delete", key_display="D"),
        Binding("t", "test", "Test", key_display="T"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="connection-manager-layout"):
            yield Label("[bold]Connection Manager[/]", id="cm-title")

            yield Label("Saved SSH Hosts", id="cm-hosts-title")
            yield DataTable(id="hosts-table", cursor_type="row")

            yield Label("Add New Host", id="cm-add-title")
            yield Input(placeholder="Hostname or IP", id="hostname-input")
            yield Input(placeholder="Port (default: 22)", id="port-input")
            yield Input(placeholder="Username", id="username-input")
            yield Input(placeholder="Identity file path (optional)", id="identity-input")

            with Horizontal(id="cm-buttons"):
                yield Button("Add Host", variant="primary", id="add-btn")
                yield Button("Connect", variant="primary", id="connect-btn")
                yield Button("Test", variant="default", id="test-btn")
                yield Button("Back", variant="default", id="back-btn")

            yield Static(id="cm-status")
        yield Footer()

    async def on_mount(self):
        self._setup_table()
        self._load_hosts()

    def _setup_table(self):
        table = self.query_one("#hosts-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Hostname", "Port", "Username", "Identity File", "Status")

    def _load_hosts(self):
        table = self.query_one("#hosts-table", DataTable)
        table.clear()
        config = self.app.config_manager.config
        for host in config.ssh_hosts:
            table.add_row(
                host.hostname,
                str(host.port),
                host.username,
                host.identity_file or "-",
                "saved",
            )
        if config.ssh_hosts:
            table.add_row(
                "[bold]localhost[/]", "-", "-", "-", "[green]● active[/]"
            )

    async def on_button_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if btn_id == "add-btn":
            self._add_host()
        elif btn_id == "connect-btn":
            await self._connect()
        elif btn_id == "test-btn":
            await self._test_connection()
        elif btn_id == "back-btn":
            self.dismiss()

    def _add_host(self):
        hostname = self.query_one("#hostname-input", Input).value.strip()
        port_str = self.query_one("#port-input", Input).value.strip()
        username = self.query_one("#username-input", Input).value.strip()
        identity = self.query_one("#identity-input", Input).value.strip()

        if not hostname:
            self.app.notify("Hostname is required", severity="error")
            return

        port = int(port_str) if port_str else 22
        host_config = SshHostConfig(
            hostname=hostname,
            port=port,
            username=username,
            identity_file=identity if identity else None,
            display_name=hostname,
        )
        self.app.config_manager.add_ssh_host(host_config)
        self.query_one("#hostname-input", Input).value = ""
        self.query_one("#port-input", Input).value = ""
        self.query_one("#username-input", Input).value = ""
        self.query_one("#identity-input", Input).value = ""
        self.app.notify(f"Host '{hostname}' added")
        self._load_hosts()

    async def _connect(self):
        table = self.query_one("#hosts-table", DataTable)
        if table.cursor_row is not None:
            config = self.app.config_manager.config
            hosts = config.ssh_hosts
            if table.cursor_row < len(hosts):
                host = hosts[table.cursor_row]
                conn = SshConnection(
                    hostname=host.hostname,
                    port=host.port,
                    username=host.username,
                    identity_file=host.identity_file,
                )
                ok, msg = await conn.test_connection()
                if ok:
                    self.app.switch_host(host.hostname)
                    self.app.notify(f"Connected to {host.hostname}")
                else:
                    self.app.notify(
                        f"Connection failed: {msg}", severity="error"
                    )
            elif table.cursor_row == len(hosts):
                self.app.switch_host("localhost")

    async def _test_connection(self):
        table = self.query_one("#hosts-table", DataTable)
        if table.cursor_row is not None:
            config = self.app.config_manager.config
            hosts = config.ssh_hosts
            if table.cursor_row < len(hosts):
                host = hosts[table.cursor_row]
                conn = SshConnection(
                    hostname=host.hostname,
                    port=host.port,
                    username=host.username,
                    identity_file=host.identity_file,
                )
                status_label = self.query_one("#cm-status", Static)
                status_label.update(f"Testing connection to {host.hostname}...")
                ok, msg = await conn.test_connection()
                if ok:
                    status_label.update(
                        f"[green]● Connection to {host.hostname} successful[/]"
                    )
                else:
                    status_label.update(
                        f"[red]● Connection failed: {msg}[/]"
                    )

    async def action_delete_host(self):
        table = self.query_one("#hosts-table", DataTable)
        if table.cursor_row is not None:
            config = self.app.config_manager.config
            hosts = config.ssh_hosts
            if table.cursor_row < len(hosts):
                host = hosts[table.cursor_row]
                self.app.config_manager.remove_ssh_host(host.hostname)
                self.app.notify(f"Host '{host.hostname}' removed")
                self._load_hosts()

    async def action_refresh_data(self):
        self._load_hosts()

    def action_back(self):
        self.dismiss()
