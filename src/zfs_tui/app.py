import asyncio
from typing import Optional
from textual.app import App
from textual.binding import Binding

from zfs_tui.utils.sudo import SudoContext
from zfs_tui.utils.config import ConfigManager
from zfs_tui.controllers.zpool_ctl import ZpoolCtl
from zfs_tui.controllers.zfs_ctl import ZfsCtl
from zfs_tui.controllers.ssh_ctl import SshConnection
from zfs_tui.screens.dashboard import DashboardScreen
from zfs_tui.screens.pool_detail import PoolDetailScreen
from zfs_tui.screens.dataset_detail import DatasetDetailScreen
from zfs_tui.screens.create_pool import CreatePoolScreen
from zfs_tui.screens.create_dataset import CreateDatasetScreen
from zfs_tui.screens.connection_manager import ConnectionManagerScreen
from zfs_tui.screens.confirm_dialog import ConfirmScreen


CSS_PATH = "tcss/app.tcss"


class ZfsTuiApp(App):
    SCREENS = {
        "dashboard": DashboardScreen,
        "create_pool": CreatePoolScreen,
        "create_dataset": CreateDatasetScreen,
        "connection_manager": ConnectionManagerScreen,
    }

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("f1", "show_help", "Help", key_display="F1"),
        Binding("f2", "create_pool", "New Pool", key_display="F2"),
        Binding("f3", "import_pool", "Import", key_display="F3"),
        Binding("f4", "create_dataset", "New Dataset", key_display="F4"),
        Binding("f5", "refresh", "Refresh", key_display="F5"),
        Binding("f6", "connection_manager", "SSH", key_display="F6"),
        Binding("f10", "quit", "Quit", key_display="F10"),
    ]

    TITLE = "ZFS TUI"

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.sudo = SudoContext(timeout=self.config_manager.config.sudo_keep_timeout)
        self.current_host: str = "localhost"
        self.ssh_connection: Optional[SshConnection] = None
        self.zpool_ctl = ZpoolCtl(self.sudo)
        self.zfs_ctl = ZfsCtl(self.sudo)

    def get_zpool_ctl(self) -> ZpoolCtl:
        return self.zpool_ctl

    def get_zfs_ctl(self) -> ZfsCtl:
        return self.zfs_ctl

    async def on_mount(self):
        asyncio.create_task(self._check_sudo())

    async def _check_sudo(self):
        has_sudo = await self.sudo.check()
        self.notify(
            "Sudo access granted" if has_sudo else "Running without sudo - some operations may fail",
            severity="information" if has_sudo else "warning",
            timeout=5,
        )
        await self.push_screen("dashboard")

    def switch_host(self, hostname: str):
        self.current_host = hostname
        if hostname == "localhost":
            self.ssh_connection = None
            self.zpool_ctl = ZpoolCtl(self.sudo, ssh_host=None)
            self.zfs_ctl = ZfsCtl(self.sudo, ssh_host=None)
        else:
            for h in self.config_manager.config.ssh_hosts:
                if h.hostname == hostname:
                    self.ssh_connection = SshConnection(
                        hostname=h.hostname,
                        port=h.port,
                        username=h.username,
                        identity_file=h.identity_file,
                    )
                    remote_sudo = SudoContext()
                    self.zpool_ctl = ZpoolCtl(remote_sudo, ssh_host=hostname)
                    self.zfs_ctl = ZfsCtl(remote_sudo, ssh_host=hostname)
                    break
        self.notify(f"Switched to {hostname}")

        self.pop_screen()
        self.push_screen("dashboard")

    def action_show_help(self):
        self.notify(
            "F1: Help | F2: New Pool | F3: Import | "
            "F4: New Dataset | F5: Refresh | F6: SSH | F10: Quit",
            timeout=8,
        )

    def action_create_pool(self):
        self.push_screen("create_pool")

    async def action_import_pool(self):
        ctl = self.get_zpool_ctl()
        ok, msg = await ctl.import_pool()
        if ok:
            self.notify(msg, timeout=5)
            self._refresh_current()
        else:
            self.notify(msg, severity="error", timeout=5)

    def action_create_dataset(self):
        self.push_screen("create_dataset")

    def action_refresh(self):
        self._refresh_current()

    def _refresh_current(self):
        screen = self.screen
        if hasattr(screen, "refresh_data"):
            asyncio.create_task(screen.refresh_data())

    def action_connection_manager(self):
        self.push_screen("connection_manager")

    async def confirm_dialog(self, title: str, message: str) -> Optional[bool]:
        result: Optional[bool] = None

        def callback(value: bool):
            nonlocal result
            result = value

        await self.push_screen(ConfirmScreen(title=title, message=message,
                                              callback=callback))
        while result is None:
            await asyncio.sleep(0.05)
        return result

    async def _run_sudo_auth(self):
        if not self.sudo.is_elevated:
            ok = await self.sudo.authenticate()
            if ok:
                self.notify("Sudo authenticated")
            else:
                self.notify("Sudo authentication failed", severity="error")
            return ok
        return True


def run():
    app = ZfsTuiApp()
    app.run()


if __name__ == "__main__":
    run()
