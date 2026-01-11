# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ESO Build Optimizer Companion App
Builds cross-platform executables for Windows, macOS, and Linux
"""

import sys
from pathlib import Path

block_cipher = None

# Get the companion directory
companion_dir = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(companion_dir)],
    binaries=[],
    datas=[
        ('config.example.json', '.'),
    ],
    hiddenimports=[
        'watchdog.observers',
        'watchdog.events',
        'httpx',
        'httpx._transports',
        'httpx._transports.default',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'sqlite3',
        'json',
        'logging',
        'pathlib',
        'queue',
        'threading',
        'hashlib',
        'base64',
        'time',
        'datetime',
        'dataclasses',
        'typing',
        'asyncio',
        'ssl',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        # Note: PIL is required for tray icons, do not exclude
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ESOBuildOptimizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (tray app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if sys.platform == 'win32' else 'icon.icns' if sys.platform == 'darwin' else None,
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='ESOBuildOptimizer.app',
        icon='icon.icns',
        bundle_identifier='com.esobuildoptimizer.companion',
        info_plist={
            'LSUIElement': True,  # Hide from dock (tray app)
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
        },
    )
