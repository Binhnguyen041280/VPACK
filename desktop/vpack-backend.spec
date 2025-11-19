# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for VPACK Backend
Bundle Flask + MediaPipe + OpenCV thành single executable
"""

import sys
from pathlib import Path

# Paths
BACKEND_DIR = Path('../backend').resolve()
DESKTOP_DIR = Path('.').resolve()

block_cipher = None

# Hidden imports for Flask, MediaPipe, OpenCV
hidden_imports = [
    # Flask
    'flask',
    'flask_cors',
    'flask_socketio',
    'flask_session',
    'engineio.async_drivers.gevent',
    'gevent',
    'gevent.ssl',
    'gevent.socket',
    'gevent._ssl3',

    # Database
    'sqlite3',

    # MediaPipe & CV
    'mediapipe',
    'mediapipe.python',
    'mediapipe.python.solutions',
    'cv2',
    'numpy',

    # QR Detection
    'pyzbar',
    'pyzbar.pyzbar',

    # Google APIs
    'googleapiclient',
    'googleapiclient.discovery',
    'google.auth',
    'google.auth.transport.requests',
    'google.oauth2.credentials',
    'pydrive2',

    # Cryptography
    'cryptography',
    'cryptography.fernet',
    'jwt',

    # Scheduling
    'apscheduler',
    'apscheduler.schedulers.background',
    'apscheduler.triggers.cron',

    # Other
    'PIL',
    'PIL.Image',
    'requests',
    'werkzeug',
    'jinja2',
    'markupsafe',
    'dotenv',
    'email_validator',
]

# Data files to include
datas = [
    # Templates
    (str(BACKEND_DIR / 'templates'), 'templates'),

    # Static files
    (str(BACKEND_DIR / 'static'), 'static'),

    # Models (AI models)
    (str(BACKEND_DIR / 'models'), 'models'),

    # Config
    (str(BACKEND_DIR / 'config.json'), '.'),

    # MediaPipe models (critical!)
    # PyInstaller doesn't always find these
]

# Binary files
binaries = []

# Collect MediaPipe data
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
datas += collect_data_files('mediapipe')
hidden_imports += collect_submodules('mediapipe')

# Collect OpenCV data
try:
    import cv2
    cv2_path = Path(cv2.__file__).parent
    if (cv2_path / 'data').exists():
        datas.append((str(cv2_path / 'data'), 'cv2/data'))
except:
    pass

a = Analysis(
    [str(BACKEND_DIR / 'app.py')],
    pathex=[str(BACKEND_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
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
    [],
    exclude_binaries=True,
    name='vpack-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(DESKTOP_DIR / 'resources' / 'icon.ico') if (DESKTOP_DIR / 'resources' / 'icon.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='vpack-backend',
)
