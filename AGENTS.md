# AGENTS.md — zfs-tui

## Project overview

Terminal UI for OpenZFS management. Shells out to `zpool`/`zfs` commands on a Linux host, parses JSON/tabular output. Built with [Textual](https://textual.textualize.io/) 8.x.

## Entry points

- **App**: `src/zfs_tui/app.py` — `ZfsTuiApp` class, `run()` function
- **CLI entry**: `zfs-tui` script → `zfs_tui.app:run` (pyproject.toml `[project.scripts]`)
- **`python -m`**: `src/zfs_tui/__main__.py` → imports and calls `run()`
- **Package import path**: `from zfs_tui.<module> import ...` — `src/` is the package root (setuptools `[tool.setuptools.packages.find] where = ["src"]`)

## Essential commands

```bash
uv sync --dev          # install runtime + dev deps (pyinstaller)
uv run zfs-tui         # run the TUI
uv run build-exe       # build native standalone executable (via PyInstaller)
uv run build-exe --linux  # cross-compile Linux binary via Docker
uv run pyinstaller zfs-tui.spec --noconfirm  # direct build
```

## Architecture

```
src/zfs_tui/
├── app.py              # ZfsTuiApp — screen routing, sudo init, host switching
├── models/             # Pure dataclasses + enums (no logic)
│   ├── pool.py         # Pool, Vdev, PoolHealth, PoolStatus
│   ├── dataset.py      # Dataset, DatasetType, DatasetProperties
│   └── snapshot.py     # Snapshot, Bookmark
├── controllers/        # Shell-out logic (zpool/zfs commands via SudoContext)
│   ├── zpool_ctl.py    # All zpool subcommands (24 methods)
│   ├── zfs_ctl.py      # All zfs subcommands (20 methods)
│   ├── ssh_ctl.py      # SSH command runner (subprocess ssh binary)
│   └── parser.py       # JSON + tabular output → model objects
├── screens/            # Textual Screen widgets
│   ├── dashboard.py    # Split panel: pool DataTable + dataset Tree
│   ├── pool_detail.py  # 4-tab drilldown
│   ├── create_pool.py  # Form-based pool creation
│   ├── confirm_dialog.py  # Blocking confirmation (spin-loop, not modal)
│   └── ...             # Other screens
├── utils/
│   ├── sudo.py         # SudoContext — sudo check/auth/cache/run
│   └── config.py       # ~/.config/zfs-tui/config.json read/write
└── tcss/               # Textual CSS stylesheets (not all loaded — see quirk)
```

## Key design decisions & quirks

### Controllers shell out, no bindings
`ZpoolCtl` and `ZfsCtl` run `zpool`/`zfs` via `SudoContext.run()` — they parse stdout, they do NOT use any Python ZFS library or C bindings. `ssh_ctl.py` shells to the `ssh` binary (not `asyncssh`), even though `asyncssh` is in dependencies.

### SudoContext controls privileged access
`SudoContext` wraps every command with `sudo` prefix (or `doas`). It caches auth status with a configurable timeout. `check()` tests with `sudo -n true`. `authenticate()` runs `sudo -v`. `is_elevated` property checks both auth state and timeout. On SSH hosts, a fresh `SudoContext()` is created (no local auth needed).

### Screen navigation: push instances, not names
Detail screens (`PoolDetailScreen`, `DatasetDetailScreen`) take constructor args and are pushed as instances:
```python
await self.app.push_screen(PoolDetailScreen(pool_name=pool.name))
```
Only `dashboard`, `create_pool`, `create_dataset`, `connection_manager` are registered in `ZfsTuiApp.SCREENS` dict.

### Confirm dialog uses a blocking spin-loop
`ZfsTuiApp.confirm_dialog()` pushes a `ConfirmScreen` (with a `callback`) and then `while result is None: await asyncio.sleep(0.05)`. This is NOT Textual's built-in modal pattern.

### Host switching replaces controller instances
`switch_host()` on the App replaces `self.zpool_ctl` and `self.zfs_ctl` with new instances pointing to the remote host. All screens retrieve the current ctl via `self.app.get_zpool_ctl()` / `self.app.get_zfs_ctl()`.

### TCSS loading quirk
Only `tcss/app.tcss` is loaded (via `CSS_PATH = "tcss/app.tcss"` on `ZfsTuiApp`). The other `tcss/*.tcss` files exist but are NOT loaded by any screen — they are dead code. If adding screen-specific styles, either `@import` them from `app.tcss` or set `CSS_PATH` on the screen class.

### Config
`~/.config/zfs-tui/config.json` is auto-created on first run. SSH hosts are stored inline in the same file.

## PyInstaller build specifics

- Spec: `zfs-tui.spec` (at project root)
- Entry script: `src/zfs_tui/__main__.py`
- TCSS files are collected as data via `os.walk` in the spec
- Hidden imports declared in spec: `textual._xterm_parser`, all `textual.widgets._*` modules, `asyncssh`
- Docker cross-build: `Dockerfile.build` uses `python:3.14-slim-bookworm`, installs uv, runs PyInstaller inside

## Style conventions

- No comments in code (project convention)
- Async methods for all ZFS operations (`async def`)
- `tuple[bool, str]` return type for mutation methods (success + message)
- Textual 8.x imports: `TabbedContent`, `TabPane` from `textual.widgets` (NOT `textual.containers`)
