from typing import Optional
from zfs_tui.utils.sudo import SudoContext
from zfs_tui.controllers.parser import ZfsParser
from zfs_tui.models.dataset import Dataset, DatasetProperties
from zfs_tui.models.snapshot import Snapshot, Bookmark


class ZfsCtl:
    def __init__(self, sudo: SudoContext, ssh_host: Optional[str] = None):
        self.sudo = sudo
        self.ssh_host = ssh_host

    def _cmd(self, *args: str) -> list[str]:
        cmd = ["zfs"]
        cmd.extend(args)
        return cmd

    async def list_datasets(
        self, recursive: bool = False,
        types: str = "filesystem,volume",
    ) -> list[Dataset]:
        cmd = ["list", "-Hjp"]
        if types:
            cmd.extend(["-t", types])
        if recursive:
            cmd.append("-r")
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret != 0:
            return []
        datasets = ZfsParser.parse_dataset_list_json(stdout)
        for ds in datasets:
            ds.host = self.ssh_host or "localhost"
        return datasets

    async def create_dataset(
        self, name: str,
        properties: Optional[dict[str, str]] = None,
        mountpoint: Optional[str] = None,
        recursive: bool = False,
        volume_size: Optional[str] = None,
    ) -> tuple[bool, str]:
        cmd = ["create"]
        if recursive:
            cmd.append("-p")
        if properties:
            for k, v in properties.items():
                cmd.extend(["-o", f"{k}={v}"])
        if volume_size:
            cmd.extend(["-V", volume_size])
        cmd.append(name)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Dataset '{name}' created"
        return False, stderr.strip()

    async def destroy_dataset(
        self, name: str, recursive: bool = False,
        force: bool = False, defer: bool = False,
    ) -> tuple[bool, str]:
        cmd = ["destroy"]
        if recursive:
            cmd.append("-r")
        if force:
            cmd.append("-f")
        if defer:
            cmd.append("-d")
        cmd.append(name)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Dataset '{name}' destroyed"
        return False, stderr.strip()

    async def set_property(self, dataset: str, prop: str,
                           value: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("set", f"{prop}={value}", dataset)
        )
        if ret == 0:
            return True, f"Set {prop}={value} on '{dataset}'"
        return False, stderr.strip()

    async def get_properties(self, dataset: str) -> dict[str, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("get", "-Hp", "all", dataset)
        )
        if ret != 0:
            return {}
        props: dict[str, str] = {}
        for line in stdout.strip().split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 3:
                props[parts[1]] = parts[2]
        return props

    async def inherit_property(self, dataset: str,
                               prop: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("inherit", prop, dataset)
        )
        if ret == 0:
            return True, f"'{prop}' inherited on '{dataset}'"
        return False, stderr.strip()

    async def create_snapshot(
        self, name: str, recursive: bool = False,
        properties: Optional[dict[str, str]] = None,
    ) -> tuple[bool, str]:
        cmd = ["snapshot"]
        if recursive:
            cmd.append("-r")
        if properties:
            for k, v in properties.items():
                cmd.extend(["-o", f"{k}={v}"])
        cmd.append(name)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Snapshot '{name}' created"
        return False, stderr.strip()

    async def list_snapshots(
        self, dataset: Optional[str] = None,
        recursive: bool = False,
    ) -> list[Snapshot]:
        cmd = ["list", "-Hjp", "-t", "snapshot"]
        if recursive:
            cmd.append("-r")
        if dataset:
            cmd.append(dataset)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret != 0:
            return []
        snapshots = ZfsParser.parse_snapshot_list_json(stdout)
        for s in snapshots:
            s.host = self.ssh_host or "localhost"
        return snapshots

    async def rollback_snapshot(
        self, snapshot: str, recursive: bool = False,
        destroy_older: bool = False,
    ) -> tuple[bool, str]:
        cmd = ["rollback"]
        if recursive:
            cmd.append("-r")
        if destroy_older:
            cmd.append("-R")
        cmd.append(snapshot)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Rolled back to '{snapshot}'"
        return False, stderr.strip()

    async def clone_snapshot(self, snapshot: str,
                             destination: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("clone", snapshot, destination)
        )
        if ret == 0:
            return True, f"Cloned '{snapshot}' -> '{destination}'"
        return False, stderr.strip()

    async def promote_dataset(self, dataset: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("promote", dataset)
        )
        if ret == 0:
            return True, f"'{dataset}' promoted"
        return False, stderr.strip()

    async def rename_dataset(self, old_name: str,
                             new_name: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("rename", old_name, new_name)
        )
        if ret == 0:
            return True, f"Renamed '{old_name}' -> '{new_name}'"
        return False, stderr.strip()

    async def mount_dataset(self, dataset: str,
                            mountpoint: Optional[str] = None,
                            all_: bool = False) -> tuple[bool, str]:
        if all_:
            ret, stdout, stderr = await self.sudo.run(
                self._cmd("mount", "-a")
            )
        elif mountpoint:
            ret, stdout, stderr = await self.sudo.run(
                self._cmd("mount", "-O", dataset, mountpoint)
            )
        else:
            ret, stdout, stderr = await self.sudo.run(
                self._cmd("mount", dataset)
            )
        if ret == 0:
            return True, f"Mounted '{dataset}'"
        return False, stderr.strip()

    async def unmount_dataset(self, dataset: str,
                               force: bool = False,
                               all_: bool = False) -> tuple[bool, str]:
        cmd = ["unmount"]
        if force:
            cmd.append("-f")
        if all_:
            cmd.append("-a")
        else:
            cmd.append(dataset)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, f"Unmounted '{dataset}'"
        return False, stderr.strip()

    async def hold_snapshot(self, tag: str,
                            snapshot: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("hold", tag, snapshot)
        )
        if ret == 0:
            return True, f"Hold '{tag}' on '{snapshot}'"
        return False, stderr.strip()

    async def release_snapshot(self, tag: str,
                               snapshot: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("release", tag, snapshot)
        )
        if ret == 0:
            return True, f"Released '{tag}' from '{snapshot}'"
        return False, stderr.strip()

    async def diff_snapshot(self, snapshot: str,
                            second: Optional[str] = None
                            ) -> tuple[bool, str]:
        cmd = ["diff"]
        cmd.append(snapshot)
        if second:
            cmd.append(second)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            return True, stdout
        return False, stderr.strip()

    async def bookmark_snapshot(self, snapshot: str,
                                bookmark: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("bookmark", snapshot, bookmark)
        )
        if ret == 0:
            return True, f"Bookmarked '{snapshot}' as '{bookmark}'"
        return False, stderr.strip()

    async def send_snapshot(
        self, snapshot: str,
        incremental_from: Optional[str] = None,
        properties: bool = False,
        replicates: bool = False,
        large_block: bool = False,
        compressed: bool = False,
        saved: bool = False,
        verbose: bool = False,
    ) -> tuple[int, bytes, str]:
        cmd = ["send"]
        if properties:
            cmd.append("-p")
        if replicates:
            cmd.append("-R")
        if large_block:
            cmd.append("-L")
        if compressed:
            cmd.append("-c")
        if saved:
            cmd.append("-w")
        if verbose:
            cmd.append("-v")
        if incremental_from:
            cmd.extend(["-i", incremental_from])
        cmd.append(snapshot)
        return await self.sudo.run(self._cmd(*cmd), timeout=3600)

    async def receive_snapshot(
        self, dataset: str,
        input_data: bytes,
        force: bool = False,
        verbose: bool = False,
    ) -> tuple[bool, str]:
        cmd = ["receive"]
        if force:
            cmd.append("-F")
        if verbose:
            cmd.append("-v")
        cmd.append(dataset)
        ret, stdout, stderr = await self.sudo.run(
            self._cmd(*cmd), input_data=input_data, timeout=3600
        )
        if ret == 0:
            return True, f"Received into '{dataset}'"
        return False, stderr.strip()

    async def list_bookmarks(
        self, dataset: Optional[str] = None,
    ) -> list[Bookmark]:
        cmd = ["list", "-Hjp", "-t", "bookmark"]
        if dataset:
            cmd.append(dataset)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret != 0:
            return []
        bookmarks: list[Bookmark] = []
        try:
            import json
            data = json.loads(stdout)
            raw = data.get("datasets", data)
            if isinstance(raw, dict):
                raw = list(raw.values())
            for entry in raw:
                name = entry.get("name", "")
                if "#" not in name:
                    continue
                bm = Bookmark(
                    name=name,
                    dataset=name.split("#")[0],
                    creation=entry.get("properties", {}).get("creation", {}).get("value", ""),
                    host=self.ssh_host or "localhost",
                )
                bookmarks.append(bm)
        except json.JSONDecodeError:
            pass
        return bookmarks

    async def allow_unallow(self, dataset: str,
                             permissions: list[str],
                             user: Optional[str] = None,
                             group: Optional[str] = None,
                             unallow: bool = False,
                             recursive: bool = False) -> tuple[bool, str]:
        cmd = ["unallow" if unallow else "allow"]
        if recursive:
            cmd.append("-r")
        if user:
            cmd.extend(["-u", user])
        if group:
            cmd.extend(["-g", group])
        cmd.extend(permissions)
        cmd.append(dataset)
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret == 0:
            action = "removed" if unallow else "set"
            return True, f"Permissions {action} on '{dataset}'"
        return False, stderr.strip()

    async def get_usage(self, dataset: str, usage_type: str = "user"
                        ) -> list[dict[str, str]]:
        cmd = ["userspace" if usage_type == "user" else "groupspace",
               "-Hp", dataset]
        ret, stdout, stderr = await self.sudo.run(self._cmd(*cmd))
        if ret != 0:
            return []
        result: list[dict[str, str]] = []
        for line in stdout.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 4:
                result.append({
                    "type": parts[0],
                    "name": parts[1],
                    "used": parts[2],
                    "quota": parts[3],
                })
        return result

    async def upgrade_dataset(self, dataset: str) -> tuple[bool, str]:
        ret, stdout, stderr = await self.sudo.run(
            self._cmd("upgrade", dataset)
        )
        if ret == 0:
            return True, f"Dataset '{dataset}' upgraded"
        return False, stderr.strip()
