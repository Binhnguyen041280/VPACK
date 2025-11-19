# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for VPACK Launcher
Tạo file launcher.exe/.app chính
"""

import sys
from pathlib import Path

DESKTOP_DIR = Path('.').resolve()

block_cipher = None

hidden_imports = [
    'pystray',
    'pystray._win32' if sys.platform == 'win32' else 'pystray._darwin' if sys.platform == 'darwin' else 'pystray._xorg',
    'PIL',
    'PIL.Image',
    'PIL._tkinter_finder',
    'requests',
]

datas = [
    ('config.py', '.'),
]

# Add icon if exists
if (DESKTOP_DIR / 'resources' / 'icon.ico').exists():
    datas.append((str(DESKTOP_DIR / 'resources' / 'icon.ico'), 'resources'))

a = Analysis(
    ['launcher.py'],
    pathex=[str(DESKTOP_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='VPACK',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window - tray app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(DESKTOP_DIR / 'resources' / 'icon.ico') if (DESKTOP_DIR / 'resources' / 'icon.ico').exists() else None,
)

# macOS app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='VPACK.app',
        icon=str(DESKTOP_DIR / 'resources' / 'icon.icns') if (DESKTOP_DIR / 'resources' / 'icon.icns').exists() else None,
        bundle_identifier='com.vpack.desktop',
        info_plist={
            'CFBundleName': 'VPACK',
            'CFBundleDisplayName': 'VPACK',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSUIElement': True,  # Hide from dock (tray app)
        },
    )
