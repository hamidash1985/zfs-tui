<div align="center">
  <h1>zfs-tui</h1>
  <p><strong>Terminal UI for ZFS Pool & Dataset Management</strong></p>
  <p>
    <img src="https://img.shields.io/badge/python-≥3.12-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-GPLv3-green" alt="License">
    <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Platform">
  </p>
</div>

zfs-tui is a terminal user interface for managing OpenZFS pools and datasets. It wraps every `zpool` and `zfs` subcommand in a keyboard-driven TUI built with [Textual](https://textual.textualize.io/), providing real-time status, properties inspection, and destructive-action confirmation.

## Features

- **Pool management**: create, destroy, export, import, add/remove/replace vdevs, attach/detach, split, online/offline, scrub, trim, initialize, clear, reguid, checkpoint, wait, iostat
- **Dataset management**: create, destroy, snapshot, rollback, clone, promote, rename, mount/unmount, send/receive, hold/release, bookmark, diff, inherit, allow/unallow, userspace/groupspace, upgrade, property get/set
- **Dashboard**: split-panel view with pool health table (color-coded) and hierarchical dataset tree
- **Pool detail**: 4-tab drilldown — VDEV tree with status, properties editor (key=value), I/O statistics, datasets list
- **Dataset detail**: information/properties panel, snapshot management, clone and bookmark listing
- **SSH remote hosts**: connection manager for managing remote ZFS servers over SSH
- **Sudo integration**: automatic credential caching with status indicator, falls back gracefully when sudo is unavailable
- **Confirmation dialogs**: all destructive operations require explicit confirmation
- **Standalone executable**: build a single-file binary with PyInstaller — no Python runtime required on the target machine

## Requirements

- **OS**: Linux with OpenZFS (`zpool` and `zfs` commands)
- **Python**: ≥ 3.12 (if running from source)
- **Sudo**: recommended for pool-level operations

## Installation

### From source (with uv)

```bash
git clone <repo-url> && cd zfs-tui
uv sync
uv run zfs-tui
```

### From source (with pip)

```bash
pip install .
zfs-tui
```

## Building standalone executables

All build methods produce a single-file, self-contained binary with no Python or dependency requirements on the target machine.

### Prerequisites

```bash
uv sync --dev          # install dev dependencies including pyinstaller
```

### Native build (current platform)

Builds for whatever OS you are running on:

```bash
# Option A — project script (recommended)
uv run build-exe

# Option B — direct PyInstaller invocation
uv run pyinstaller zfs-tui.spec --noconfirm
```

| Platform | Output |
|----------|--------|
| Linux    | `dist/zfs-tui` |
| Windows  | `dist/zfs-tui.exe` |

The native build takes ~30–60 seconds and bundles Python + all dependencies into a ~20 MB executable.

### Cross-compile for Linux (via Docker)

Use this on **any OS** (Windows, macOS, Linux) to produce a Linux binary. Requires [Docker](https://docs.docker.com/get-docker/).

```bash
# Option A — project script with --linux flag (recommended)
uv run build-exe --linux

# Option B — convenience shell scripts
./build-linux.sh          # Bash (Linux / macOS / WSL)
.\build-linux.ps1         # PowerShell (Windows)

# Option C — manual Docker steps
docker build -t zfs-tui-builder -f Dockerfile.build .
docker run --rm `
    -v "$(pwd):/project" `
    -v "$(pwd)/dist:/output" `
    zfs-tui-builder
```

The output is a statically-linked Linux ELF binary at `dist/zfs-tui`. It is compiled inside a `python:3.14-slim-bookworm` container, so it is compatible with any Linux distribution running kernel 3.2+ (i.e. any modern Linux).

### Verify the build

```bash
./dist/zfs-tui --help
# If the binary runs, it will attempt to connect to ZFS.
# On a non-ZFS system it will show a warning — that's expected.
```

### Deployment

```bash
# Copy to any Linux server with OpenZFS
scp dist/zfs-tui user@nas-server:~
ssh user@nas-server
./zfs-tui
```

## Usage

### Key bindings

| Key | Action |
|-----|--------|
| `F1` | Help (key reference) |
| `F2` | Create new pool |
| `F3` | Import pools |
| `F4` | Create new dataset |
| `F5` | Refresh all data |
| `F6` | SSH connection manager |
| `F10` / `Ctrl+C` | Quit |
| `Enter` | Open detail view for selected item |
| `R` | Refresh (on dashboard) |
| `D` | Destroy selected pool (with confirmation) |
| `E` | Export selected pool |
| `/` | Cycle focus through pool rows |
| `Tab` / `Shift+Tab` | Cycle focus between panels |

### Dashboard

The main screen shows two panels:

- **Left — Pools table**: lists all pools with name, size, allocated, free, capacity %, health status (color-coded), and host. Use `D` to destroy, `E` to export, `Enter` to drill into pool details.
- **Right — Datasets tree**: hierarchical view of all filesystems and volumes. `Enter` opens dataset details.

### Pool detail (Enter on a pool)

Four tabs:

1. **Status** — VDEV tree with health, read/write/cksum errors, and scan progress
2. **Properties** — key=value property editor (type to set, `Enter` to apply)
3. **I/O Stats** — bandwidth and operation rates per VDEV
4. **Datasets** — datasets within this pool (opens dataset detail on selection)

### Dataset detail (Enter on a dataset in the tree)

Three tabs:

1. **Info** — dataset type, used/available/ referenced space, compression, dedup, mountpoint, encryption, atime, recordsize
2. **Snapshots** — create/rollback/destroy snapshots
3. **Clones & Bookmarks** — list clones and bookmarks

### SSH connections

Press `F6` to open the connection manager. Add remote hosts with hostname, port, username, and optional identity file path. Select a host to connect — the dashboard switches to show that host's pools and datasets. All subsequent operations run over SSH.

## Project structure

```
src/zfs_tui/
├── app.py                    # ZfsTuiApp — main Textual App, sudo init, screen routing
├── __main__.py               # python -m entry point
├── build.py                  # PyInstaller build script
│
├── models/                   # Data models (dataclasses + enums)
│   ├── pool.py               # Pool, Vdev, PoolHealth
│   ├── dataset.py            # Dataset, DatasetType, DatasetProperties
│   └── snapshot.py           # Snapshot, Bookmark
│
├── controllers/              # Backend logic (shell out to zpool/zfs)
│   ├── zpool_ctl.py          # All 24 zpool subcommands
│   ├── zfs_ctl.py            # All 20 zfs subcommands
│   ├── ssh_ctl.py            # SSH remote connections
│   └── parser.py             # JSON + tabular output parsing
│
├── utils/
│   ├── sudo.py               # SudoContext — authentication, caching, execution
│   └── config.py             # ConfigManager — persistent settings (~/.config/zfs-tui/config.json)
│
├── screens/                  # Textual Screen widgets
│   ├── dashboard.py          # Main dashboard (pool table + dataset tree)
│   ├── pool_detail.py        # Pool drill-down (4 tabs)
│   ├── dataset_detail.py     # Dataset drill-down (3 tabs)
│   ├── create_pool.py        # Pool creation form
│   ├── create_dataset.py     # Dataset creation form
│   ├── confirm_dialog.py     # Confirmation dialog for destructive ops
│   └── connection_manager.py # SSH host management
│
└── tcss/                     # Textual CSS theme files
    ├── app.tcss              # Global styles
    ├── dashboard.tcss
    ├── pool_detail.tcss
    ├── dataset_detail.tcss
    ├── create_pool.tcss
    ├── create_dataset.tcss
    ├── confirm_dialog.tcss
    └── connection_manager.tcss
```

## Configuration

zfs-tui stores configuration at `~/.config/zfs-tui/config.json`:

```json
{
  "sudo_keep_timeout": 900,
  "ssh_hosts": [
    {
      "hostname": "nas.example.com",
      "port": 22,
      "username": "root",
      "identity_file": "/home/user/.ssh/id_ed25519"
    }
  ]
}
```

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).

## Contributing

Bug reports, feature requests, and pull requests are welcome. Please open an issue on the repository first to discuss significant changes.
