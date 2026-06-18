# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# Spec is executed from the project root (via --distpath etc.)
project_root = Path(os.getcwd())

datas = []
# Collect all .tcss files under src/zfs_tui/tcss
tcss_root = project_root / "src" / "zfs_tui" / "tcss"
if tcss_root.exists():
    for f in sorted(tcss_root.rglob("*.tcss")):
        dest = str(f.relative_to(tcss_root.parent))
        datas.append((str(f), str(Path(dest).parent)))

a = Analysis(
    ['src/zfs_tui/__main__.py'],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'zfs_tui.controllers',
        'zfs_tui.models',
        'zfs_tui.screens',
        'zfs_tui.utils',
        'zfs_tui.tcss',
        'textual._xterm_parser',
        'textual.widgets._data_table',
        'textual.widgets._tree',
        'textual.widgets._toggle_button',
        'textual.widgets._select',
        'textual.widgets._header',
        'textual.widgets._footer',
        'asyncssh',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'PIL',
        'pandas',
        'scipy',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='zfs-tui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
