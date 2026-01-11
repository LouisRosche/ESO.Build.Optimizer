# PyInstaller Cross-Platform Packaging Guide

> **Last Updated**: January 2026
> **PyInstaller Version**: 6.17.0
> **Source**: [PyInstaller Docs](https://pyinstaller.org/), [Real Python Guide](https://realpython.com/pyinstaller-python/)

---

## Critical Constraint

**PyInstaller cannot cross-compile.**

- To build Windows `.exe`: Run PyInstaller on Windows
- To build macOS `.app`: Run PyInstaller on macOS
- To build Linux binary: Run PyInstaller on Linux

Use CI/CD (GitHub Actions) to build for all platforms automatically.

---

## Python Version Compatibility

| Python Version | Support Status |
|----------------|----------------|
| 3.8 - 3.14 | Supported |
| 3.10.0 | NOT supported (bug) |
| 3.15 beta | NOT supported |

---

## Virtual Environment Setup

```bash
# Always use venv for clean dependency detection
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install app dependencies
pip install -r requirements.txt

# Install PyInstaller in same venv
pip install pyinstaller

# Now PyInstaller sees all dependencies
pyinstaller your_app.py
```

---

## Spec File Configuration

```python
# build.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include data files: (source, dest_folder)
        ('config.example.json', '.'),
        ('assets/*', 'assets'),
    ],
    hiddenimports=[
        # Explicitly list imports PyInstaller misses
        'watchdog.observers',
        'httpx._transports.default',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # Exclude unused heavy packages
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
    ],
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
    name='MyApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression
    console=False,  # False = no console window (GUI app)
    icon='icon.ico',  # Windows icon
)

# macOS app bundle (only on macOS)
import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='MyApp.app',
        icon='icon.icns',
        bundle_identifier='com.example.myapp',
        info_plist={
            'LSUIElement': True,  # Hide from dock (tray app)
        },
    )
```

---

## Build Commands

```bash
# Basic build (creates dist/ and build/ folders)
pyinstaller main.py

# One-file executable
pyinstaller --onefile main.py

# No console window (GUI apps)
pyinstaller --windowed main.py

# With spec file
pyinstaller build.spec

# Clean build
pyinstaller --clean --noconfirm build.spec
```

---

## File Size Optimization

### UPX Compression

```bash
# Install UPX
# Windows: choco install upx
# macOS: brew install upx
# Linux: apt install upx

# PyInstaller uses UPX automatically if found
# Or specify path:
pyinstaller --upx-dir=/path/to/upx main.py
```

**Results**: 460 MB → 130 MB (typical reduction)

### Exclude Unused Modules

```python
excludes=[
    'tkinter',      # GUI toolkit (if not using)
    'matplotlib',   # Plotting
    'numpy',        # Numerical (if not using)
    'pandas',       # Data frames
    'scipy',        # Scientific
    'PIL',          # Image processing
    'cv2',          # OpenCV
    'unittest',     # Testing
    'test',         # Test modules
]
```

---

## Hidden Imports

PyInstaller may miss dynamically imported modules. Common ones:

```python
hiddenimports=[
    # Async libraries
    'anyio._backends._asyncio',
    'asyncio',

    # HTTP clients
    'httpx._transports',
    'httpx._transports.default',

    # File watching
    'watchdog.observers',
    'watchdog.events',

    # Database
    'sqlite3',
    'sqlalchemy.dialects.postgresql',

    # Encoding
    'encodings.idna',
    'encodings.utf_8',
]
```

---

## Linux GLIBC Compatibility

**Problem**: Linux binaries built on newer distros may not run on older ones due to GLIBC version requirements.

**Solution**: Build on the oldest target distro.

```bash
# Check GLIBC version
ldd --version

# Build in Docker with older base
FROM python:3.11-slim-buster  # Older = more compatible
```

---

## Windows Considerations

### Antivirus False Positives

PyInstaller executables often trigger antivirus warnings because:
- They extract and execute code at runtime
- The bootloader is flagged by heuristics

**Mitigations**:
1. Sign your executable with a code signing certificate
2. Submit to Microsoft for analysis
3. Exclude from Windows Defender during development

### First-Run Slowness

Windows Defender scans large `.exe` files on first run. Can take 10-30 seconds.

---

## macOS Considerations

### Code Signing

```bash
# Sign the app bundle
codesign --force --deep --sign "Developer ID Application: Your Name" dist/MyApp.app

# Notarize for distribution
xcrun notarytool submit dist/MyApp.zip --apple-id your@email.com --team-id XXXXXXXXXX
```

### App Bundle Structure

```
MyApp.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── MyApp          # Executable
│   └── Resources/
│       └── icon.icns
```

---

## GitHub Actions CI/CD

```yaml
# .github/workflows/build.yml
name: Build Executables

on:
  release:
    types: [created]

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --clean --noconfirm build.spec
      - uses: actions/upload-artifact@v4
        with:
          name: windows-exe
          path: dist/*.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --clean --noconfirm build.spec
      - uses: actions/upload-artifact@v4
        with:
          name: macos-app
          path: dist/*.app

  build-linux:
    runs-on: ubuntu-20.04  # Older for GLIBC compat
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pyinstaller
      - run: pyinstaller --clean --noconfirm build.spec
      - uses: actions/upload-artifact@v4
        with:
          name: linux-binary
          path: dist/MyApp
```

---

## Debugging Build Issues

```bash
# Verbose output
pyinstaller --log-level DEBUG main.py

# Check what's being included
pyi-archive_viewer dist/main.exe

# Test imports manually
python -c "import your_module"
```

---

## Common Pitfalls

1. **Missing data files**: Use `--add-data` or `datas=[]` in spec
2. **Dynamic imports not detected**: Add to `hiddenimports`
3. **Relative paths break**: Use `sys._MEIPASS` for bundled resources
4. **Large file size**: Exclude unused packages, enable UPX
5. **GLIBC errors on Linux**: Build on older distro

---

*This document should be refreshed when PyInstaller releases major updates.*
