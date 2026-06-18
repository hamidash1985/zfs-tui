from typing import Optional, Callable
from zfs_tui.utils.sudo import SudoContext
from zfs_tui.controllers.parser import ZfsParser
from zfs_tui.models.pool import Pool, PoolHealth


class ZpoolCtl:
    def __init__(self, sudo: SudoContext, ssh_host: Optional[str] = None):
        self.sudo = sudo
        self.ssh_host = ssh_host

    def _cmd(self, *args: str) -> list[str]:
        cmd = ["zpool"]
        cmd.extend(args)
        return cmd

    async def list_pools(self) -> list[Pool]:
        ret, stdout, stderr = await self.sudo.run(self._cmd("list", "-H"))
        if ret != 0:
            return []
        return ZfsParser.parse_pool_list_stdout(stdout)

    async def get_pool_status(self, pool_name: str) -> Optional[Pool]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("status", "-j", pool_name)
        )
        if ret != 0:
            return None
        pools = ZfsParser.parse_pool_status_json(stdout)
        pool = pools.get(pool_name)
        if pool:
            pool.host = self.ssh_host or "localhost"
        return pool

    async def get_all_pools_status(self) -> dict[str, Pool]:
        ret, stdout, stderr = await self.sudo.run(self._cmd("status", "-j"))
        if ret != 0:
            return {}
        pools = ZfsParser.parse_pool_status_json(stdout)
        for p in pools.values():
            p.host = self.ssh_host or "localhost"
        return pools

    async def create_pool(
        self, name: str, vdev_spec: list[str],
        properties: Optional[dict[str, str]] = None,
        mountpoint: Optional[str] = None,
        force: bool = False,
    ) -> tuple[bool, str]:
        cmd = ["create"]
        if force:
            cmd.append("-f")
        if mountpoint:
            cmd.extend(["-m", mountpoint])
        if properties:
            for k, v in properties.items():
                cmd.extend(["-o", f"{k}={v}"])
        cmd.append(name)
        cmd.extend(vdev_spec)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Pool '{name}' created successfully"
        return False, stderr.strip()

    async def destroy_pool(self, name: str, force: bool = False) -> tuple[bool, str]:
        cmd = ["destroy"]
        if force:
            cmd.append("-f")
        cmd.append(name)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Pool '{name}' destroyed"
        return False, stderr.strip()

    async def add_vdev(self, pool: str, vdev_spec: list[str],
                       force: bool = False) -> tuple[bool, str]:
        cmd = ["add"]
        if force:
            cmd.append("-f")
        cmd.append(pool)
        cmd.extend(vdev_spec)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, "VDEV added successfully"
        return False, stderr.strip()

    async def remove_vdev(self, pool: str, device: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("remove", pool, device)
        )
        if ret == 0:
            return True, "VDEV removed"
        return False, stderr.strip()

    async def attach_device(self, pool: str, device: str,
                            new_device: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("attach", pool, device, new_device)
        )
        if ret == 0:
            return True, "Device attached"
        return False, stderr.strip()

    async def detach_device(self, pool: str, device: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("detach", pool, device)
        )
        if ret == 0:
            return True, "Device detached"
        return False, stderr.strip()

    async def replace_device(self, pool: str, old_device: str,
                             new_device: Optional[str] = None,
                             force: bool = False) -> tuple[bool, str]:
        cmd = ["replace"]
        if force:
            cmd.append("-f")
        cmd.append(pool)
        cmd.append(old_device)
        if new_device:
            cmd.append(new_device)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, "Device replaced"
        return False, stderr.strip()

    async def set_property(self, pool: str, prop: str,
                           value: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("set", f"{prop}={value}", pool)
        )
        if ret == 0:
            return True, f"Set {prop}={value}"
        return False, stderr.strip()

    async def get_properties(self, pool: str) -> dict[str, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("get", "-H", "all", pool)
        )
        if ret != 0:
            return {}
        props: dict[str, str] = {}
        for line in stdout.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                props[parts[1]] = parts[2]
        return props

    async def export_pool(self, pool: str, force: bool = False) -> tuple[bool, str]:
        cmd = ["export"]
        if force:
            cmd.append("-f")
        cmd.append(pool)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Pool '{pool}' exported"
        return False, stderr.strip()

    async def import_pool(self, pool: Optional[str] = None,
                          new_name: Optional[str] = None,
                          dir: Optional[str] = None,
                          force: bool = False) -> tuple[bool, str]:
        cmd = ["import"]
        if force:
            cmd.append("-f")
        if dir:
            cmd.extend(["-d", dir])
        if pool:
            cmd.append(pool)
            if new_name:
                cmd.append(new_name)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            name = new_name or pool or "(all)"
            return True, f"Pool '{name}' imported"
        return False, stderr.strip()

    async def list_importable(self) -> list[dict[str, str]]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("import", "-H")
        )
        if ret != 0:
            return []
        pools: list[dict[str, str]] = []
        for line in stdout.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 1:
                pools.append({"name": parts[0], "info": line.strip()})
        return pools

    async def scrub_pool(self, pool: str,
                         pause: bool = False) -> tuple[bool, str]:
        cmd = ["scrub"]
        if pause:
            cmd.append("-s")
        cmd.append(pool)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            action = "Paused" if pause else "Started"
            return True, f"{action} scrub on '{pool}'"
        return False, stderr.strip()

    async def trim_pool(self, pool: str, release: bool = False,
                        secure: bool = False) -> tuple[bool, str]:
        cmd = ["trim"]
        if release:
            cmd.append("-r")
        if secure:
            cmd.append("-s")
        cmd.append(pool)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Trim started on '{pool}'"
        return False, stderr.strip()

    async def online_device(self, pool: str,
                            device: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("online", pool, device)
        )
        if ret == 0:
            return True, f"Device '{device}' online"
        return False, stderr.strip()

    async def offline_device(self, pool: str, device: str,
                             temporary: bool = False) -> tuple[bool, str]:
        cmd = ["offline"]
        if temporary:
            cmd.append("-t")
        cmd.extend([pool, device])
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Device '{device}' offlined"
        return False, stderr.strip()

    async def clear_errors(self, pool: str,
                           device: Optional[str] = None) -> tuple[bool, str]:
        cmd = ["clear", pool]
        if device:
            cmd.append(device)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Errors cleared on '{pool}'"
        return False, stderr.strip()

    async def get_iostat(self, pool: Optional[str] = None,
                         interval: int = 2, count: int = 1
                         ) -> list[dict[str, str]]:
        cmd = ["iostat", "-Hp"]
        if pool:
            cmd.append(pool)
        cmd.append(str(interval))
        cmd.append(str(count))
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret != 0:
            return []
        return ZfsParser.parse_zpool_iostat(stdout)

    async def upgrade_pool(self, pool: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("upgrade", pool)
        )
        if ret == 0:
            return True, f"Pool '{pool}' upgraded"
        return False, stderr.strip()

    async def split_pool(self, pool: str, new_pool: str,
                         vdev_spec: Optional[list[str]] = None
                         ) -> tuple[bool, str]:
        cmd = ["split", pool, new_pool]
        if vdev_spec:
            cmd.extend(vdev_spec)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Pool '{pool}' split into '{new_pool}'"
        return False, stderr.strip()

    async def initialize_pool(self, pool: str,
                              device: Optional[str] = None,
                              cancel: bool = False,
                              suspend: bool = False) -> tuple[bool, str]:
        cmd = ["initialize"]
        if cancel:
            cmd.append("-c")
        elif suspend:
            cmd.append("-s")
        cmd.append(pool)
        if device:
            cmd.append(device)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Initialize {'cancelled' if cancel else 'started'} on '{pool}'"
        return False, stderr.strip()

    async def reguid_pool(self, pool: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("reguid", pool)
        )
        if ret == 0:
            return True, f"Pool '{pool}' reguided"
        return False, stderr.strip()

    async def reopen_pool(self, pool: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("reopen", pool)
        )
        if ret == 0:
            return True, f"Pool '{pool}' reopened"
        return False, stderr.strip()

    async def checkpoint_pool(self, pool: str,
                              discard: bool = False) -> tuple[bool, str]:
        cmd = ["checkpoint"]
        if discard:
            cmd.append("-d")
        cmd.append(pool)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            action = "discarded" if discard else "created"
            return True, f"Checkpoint {action} on '{pool}'"
        return False, stderr.strip()

    async def wait_pool(self, pool: str,
                        activity: str = "scrub") -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("wait", "-t", activity, pool), timeout=300
        )
        if ret == 0:
            return True, f"Activity '{activity}' completed on '{pool}'"
        return False, stderr.strip()
