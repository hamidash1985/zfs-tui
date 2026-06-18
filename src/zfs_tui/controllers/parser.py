import json
import re
from typing import Optional
from zfs_tui.models.pool import Pool, Vdev, PoolHealth, PoolStatus
from zfs_tui.models.dataset import Dataset, DatasetType, DatasetProperties
from zfs_tui.models.snapshot import Snapshot, Bookmark


class ZfsParser:
    @staticmethod
    def parse_pool_list_stdout(output: str) -> list[Pool]:
        pools: list[Pool] = []
        lines = output.strip().split("\n")
        if not lines or lines[0].startswith("NAME"):
            lines = lines[1:]
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            pool = Pool(name=parts[0])
            if len(parts) > 1:
                pool.size = parts[1]
            if len(parts) > 2:
                pool.allocated = parts[2]
            if len(parts) > 3:
                pool.free = parts[3]
            if len(parts) > 6:
                pool.capacity = parts[6]
            if len(parts) > 7:
                try:
                    pool.health = PoolHealth(parts[7].upper())
                except ValueError:
                    pass
            pools.append(pool)
        return pools

    @staticmethod
    def parse_pool_status_json(output: str) -> dict[str, Pool]:
        result: dict[str, Pool] = {}
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return result

        pools_data = data.get("pools", [])
        if isinstance(pools_data, dict):
            pools_data = [{"name": k, **v} for k, v in pools_data.items()]

        for pool_data in pools_data:
            pname = pool_data.get("name", "unknown")
            pdata = pool_data.get("pool_info", pool_data)
            pool = Pool(name=pname, host=pool_data.get("host", "localhost"))
            pool.size = ZfsParser._fmt_bytes(
                pdata.get("size", pdata.get("alloc", {}).get("size", 0))
            )
            scan = pdata.get("scan", {})
            if scan:
                pool.scan = (
                    f"{scan.get('function', '')} "
                    f"{scan.get('state', '')} "
                    f"{scan.get('percentage', '')}%"
                ).strip()
            pool.errors = pdata.get("errors", {}).get("count", "")
            try:
                pool.health = PoolHealth(
                    pdata.get("health", pdata.get("state", "ONLINE")).upper()
                )
            except ValueError:
                pass
            vdevs_data = pdata.get("vdev_tree", {})
            if vdevs_data:
                pool.vdevs = ZfsParser._parse_vdevs(vdevs_data)
            if "listsnapshots" in pdata.get("properties", {}):
                pool.properties = ZfsParser._extract_properties(
                    pdata.get("properties", {})
                )
            result[pname] = pool
        return result

    @staticmethod
    def _parse_vdevs(vdev_data: dict) -> list[Vdev]:
        vdevs: list[Vdev] = []
        children = vdev_data.get("children", [])
        if children:
            for child in children:
                vdevs.append(ZfsParser._parse_vdev(child))
        else:
            vdevs.append(ZfsParser._parse_vdev(vdev_data))
        return vdevs

    @staticmethod
    def _parse_vdev(data: dict) -> Vdev:
        vdev = Vdev(
            name=data.get("name", data.get("path", "unknown")),
            type=data.get("type", "disk"),
            state=data.get("state", "UNKNOWN"),
            read_errors=data.get("read_errors", 0),
            write_errors=data.get("write_errors", 0),
            checksum_errors=data.get("checksum_errors", 0),
            guid=data.get("guid"),
            path=data.get("path"),
            ashift=data.get("ashift"),
        )
        if "size" in data:
            vdev.size = ZfsParser._fmt_bytes(data["size"])
        if "alloc" in data:
            vdev.allocated = ZfsParser._fmt_bytes(data["alloc"])
        if "free" in data:
            vdev.free = ZfsParser._fmt_bytes(data["free"])
        children = data.get("children", [])
        vdev.children = [ZfsParser._parse_vdev(c) for c in children]
        return vdev

    @staticmethod
    def _fmt_bytes(val) -> str:
        if isinstance(val, str):
            return val
        if val is None:
            return "-"
        val = int(val)
        for unit in ("", "K", "M", "G", "T", "P"):
            if abs(val) < 1024.0:
                return f"{val:.1f}{unit}" if val else "0"
            val /= 1024.0
        return f"{val:.1f}E"

    @staticmethod
    def _extract_properties(props: dict) -> dict[str, str]:
        return {
            k: v.get("value", str(v)) if isinstance(v, dict) else str(v)
            for k, v in props.items()
        }

    @staticmethod
    def parse_dataset_list_json(output: str) -> list[Dataset]:
        datasets: list[Dataset] = []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return datasets

        raw = data.get("datasets", data)
        if isinstance(raw, dict):
            raw = list(raw.values())

        for entry in raw:
            if isinstance(entry, str):
                continue
            name = entry.get("name", "")
            dtype_str = entry.get("type", "filesystem")
            try:
                dtype = DatasetType(dtype_str.lower())
            except ValueError:
                dtype = DatasetType.FILESYSTEM
            if dtype in (DatasetType.SNAPSHOT, DatasetType.BOOKMARK):
                continue
            props = entry.get("properties", {})
            dp = DatasetProperties()
            for key, val in props.items():
                value = val.get("value", "") if isinstance(val, dict) else str(val)
                if hasattr(dp, key):
                    setattr(dp, key, value)
            ds = Dataset(
                name=name,
                pool=name.split("/")[0],
                type=dtype,
                properties=dp,
                origin=props.get("origin", {}).get("value") if isinstance(
                    props.get("origin"), dict
                ) else None,
                creation=props.get("creation", {}).get("value") if isinstance(
                    props.get("creation"), dict
                ) else None,
            )
            datasets.append(ds)
        return datasets

    @staticmethod
    def parse_snapshot_list_json(output: str) -> list[Snapshot]:
        snapshots: list[Snapshot] = []
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            return snapshots
        raw = data.get("datasets", data)
        if isinstance(raw, dict):
            raw = list(raw.values())
        for entry in raw:
            if isinstance(entry, str):
                continue
            name = entry.get("name", "")
            if "@" not in name:
                continue
            props = entry.get("properties", {})
            snap = Snapshot(
                name=name,
                dataset=name.split("@")[0],
                creation=props.get("creation", {}).get("value", ""),
                used=props.get("used", {}).get("value", "0"),
                referenced=props.get("referenced", {}).get("value", "0"),
            )
            snapshots.append(snap)
        return snapshots

    @staticmethod
    def parse_zpool_iostat(output: str) -> list[dict[str, str]]:
        stats: list[dict[str, str]] = []
        lines = output.strip().split("\n")
        header = None
        for line in lines:
            if not line.strip():
                continue
            if line.startswith("---"):
                continue
            if "alloc" in line.lower() and "free" in line.lower():
                header = line.strip().split()
                continue
            if header and not line.startswith("---"):
                parts = line.strip().split()
                if parts and len(parts) >= len(header):
                    row = dict(zip(header, parts))
                    stats.append(row)
        return stats
