# VPACK Desktop Packaging

Hướng dẫn đóng gói VPACK thành ứng dụng desktop (.exe cho Windows, .dmg cho macOS).

## Kiến trúc

```
VPACK Desktop/
├── VPACK.exe                    # Main launcher (double-click vào đây)
├── backend/
│   └── vpack-backend.exe        # Flask backend (PyInstaller bundle)
├── frontend/
│   ├── node.exe                 # Node.js runtime
│   └── standalone/              # Next.js standalone build
│       └── server.js
├── resources/
│   └── icon.ico
└── data/                        # User data (auto-created)
    ├── database/
    ├── logs/
    └── output/
```

## Flow hoạt động

1. User double-click `VPACK.exe`
2. Launcher khởi động backend (`localhost:8080`)
3. Launcher khởi động frontend (`localhost:3000`)
4. Chờ health check OK
5. Tự động mở browser mặc định → `http://localhost:3000`
6. Hiện tray icon (optional)

## Build trên Windows

### Yêu cầu

- Python 3.10+
- Node.js 18+
- Inno Setup 6+ (cho installer)

### Các bước

```bash
# 1. Cài đặt dependencies
cd desktop
pip install -r requirements-desktop.txt

# 2. Build
python build_windows.py

# 3. Output
# - dist/VPACK/           → Portable version
# - dist/installer/       → Setup.exe installer
```

## Build trên macOS

### Yêu cầu

- Python 3.10+
- Node.js 18+
- create-dmg (`brew install create-dmg`)
- Xcode Command Line Tools

### Các bước

```bash
# 1. Cài đặt dependencies
cd desktop
pip install -r requirements-desktop.txt

# 2. Build
python build_macos.py

# 3. Output
# - dist/VPACK.app        → macOS app bundle
# - dist/VPACK-*.dmg      → DMG installer
```

## Cấu trúc files

| File | Mục đích |
|------|----------|
| `config.py` | Cấu hình desktop (ports, paths, etc.) |
| `launcher.py` | Main launcher script |
| `vpack-backend.spec` | PyInstaller config cho backend |
| `vpack-launcher.spec` | PyInstaller config cho launcher |
| `build_windows.py` | Build script Windows |
| `build_macos.py` | Build script macOS |
| `inno_setup.iss` | Inno Setup installer script |
| `requirements-desktop.txt` | Desktop-specific dependencies |

## Cấu hình

### Thay đổi ports

Sửa trong `config.py`:

```python
BACKEND_PORT = 8080
FRONTEND_PORT = 3000
```

### Thay đổi app info

Sửa trong `config.py`:

```python
APP_NAME = "VPACK"
APP_VERSION = "1.0.0"
```

### Thêm icon

1. Đặt `icon.ico` vào `desktop/resources/` (Windows)
2. Đặt `icon.icns` vào `desktop/resources/` (macOS)

## Troubleshooting

### PyInstaller báo lỗi hidden imports

Thêm vào `vpack-backend.spec`:

```python
hidden_imports = [
    ...
    'your_missing_module',
]
```

### MediaPipe không load được models

Đảm bảo collect_data_files:

```python
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('mediapipe')
```

### OpenCV DLL errors (Windows)

Thêm vào PATH hoặc copy DLLs vào output directory.

### macOS Gatekeeper block

```bash
# Xcode signing
codesign --force --deep --sign - dist/VPACK.app

# hoặc ad-hoc
xattr -cr dist/VPACK.app
```

## So sánh với các app tương tự

| App | Backend | Frontend | Launcher | Size |
|-----|---------|----------|----------|------|
| Ollama | Go binary | - | Tray app | ~150MB |
| LM Studio | C++/Python | Embedded | Electron | ~200MB |
| GPT4All | C++ | Qt | Native | ~100MB |
| **VPACK** | Python/Flask | Next.js | PyInstaller | ~200MB |

## License

MIT License
