#!/usr/bin/env python3
"""
VPACK macOS Build Script
Build .dmg installer cho macOS

Yêu cầu:
- Python 3.10+
- Node.js 18+
- create-dmg (brew install create-dmg)
- Xcode Command Line Tools

Chạy từ thư mục desktop/:
    python build_macos.py
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
import urllib.request
import tarfile

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
BUILD_DIR = SCRIPT_DIR / "build"
DIST_DIR = SCRIPT_DIR / "dist"
OUTPUT_DIR = DIST_DIR / "VPACK.app"
CONTENTS_DIR = OUTPUT_DIR / "Contents"
MACOS_DIR = CONTENTS_DIR / "MacOS"
RESOURCES_DIR = CONTENTS_DIR / "Resources"

# Node.js version
NODE_VERSION = "18.19.0"
# Detect architecture
ARCH = "arm64" if platform.machine() == "arm64" else "x64"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-darwin-{ARCH}.tar.gz"

def log(msg):
    print(f"[BUILD] {msg}")

def run_command(cmd, cwd=None, check=True):
    """Run shell command"""
    log(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        shell=isinstance(cmd, str),
        check=check,
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result

def clean():
    """Clean previous builds"""
    log("Cleaning previous builds...")
    for dir_path in [BUILD_DIR, DIST_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)

    # Create directory structure for .app bundle
    BUILD_DIR.mkdir(parents=True)
    DIST_DIR.mkdir(parents=True)
    MACOS_DIR.mkdir(parents=True)
    RESOURCES_DIR.mkdir(parents=True)

def create_info_plist():
    """Create Info.plist for macOS app bundle"""
    log("Creating Info.plist...")

    info_plist = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>VPACK</string>
    <key>CFBundleDisplayName</key>
    <string>VPACK</string>
    <key>CFBundleIdentifier</key>
    <string>com.vpack.desktop</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>VPACK</string>
    <key>CFBundleIconFile</key>
    <string>icon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <true/>
    <key>NSAppleEventsUsageDescription</key>
    <string>VPACK needs to open your default browser.</string>
</dict>
</plist>"""

    (CONTENTS_DIR / "Info.plist").write_text(info_plist)
    log("Info.plist created")

def build_frontend():
    """Build Next.js frontend in standalone mode"""
    log("Building frontend...")

    # Install dependencies
    run_command(["npm", "ci", "--legacy-peer-deps"], cwd=FRONTEND_DIR)

    # Build
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)

    # Copy standalone output
    standalone_src = FRONTEND_DIR / ".next" / "standalone"
    standalone_dst = RESOURCES_DIR / "frontend" / "standalone"

    log(f"Copying standalone build to {standalone_dst}")
    shutil.copytree(standalone_src, standalone_dst)

    # Copy static files
    static_src = FRONTEND_DIR / ".next" / "static"
    static_dst = standalone_dst / ".next" / "static"
    static_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(static_src, static_dst)

    # Copy public folder
    public_src = FRONTEND_DIR / "public"
    public_dst = standalone_dst / "public"
    if public_src.exists():
        shutil.copytree(public_src, public_dst)

    log("Frontend build complete")

def download_node():
    """Download Node.js for macOS"""
    log(f"Downloading Node.js v{NODE_VERSION} for {ARCH}...")

    node_tar = BUILD_DIR / "node.tar.gz"
    node_extract = BUILD_DIR / "node"

    # Download
    urllib.request.urlretrieve(NODE_URL, node_tar)

    # Extract
    with tarfile.open(node_tar, 'r:gz') as tar:
        tar.extractall(node_extract)

    # Find node binary
    node_dir = list(node_extract.glob("node-*"))[0]
    node_bin_src = node_dir / "bin" / "node"
    node_bin_dst = RESOURCES_DIR / "frontend" / "node"

    log(f"Copying node to {node_bin_dst}")
    shutil.copy2(node_bin_src, node_bin_dst)

    # Make executable
    os.chmod(node_bin_dst, 0o755)

    log("Node.js download complete")

def build_backend():
    """Build backend with PyInstaller"""
    log("Building backend with PyInstaller...")

    # Install PyInstaller
    run_command([sys.executable, "-m", "pip", "install", "pyinstaller>=6.3.0"])

    # Run PyInstaller
    spec_file = SCRIPT_DIR / "vpack-backend.spec"
    run_command([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--distpath", str(BUILD_DIR / "backend_dist"),
        "--workpath", str(BUILD_DIR / "backend_build"),
        str(spec_file)
    ], cwd=SCRIPT_DIR)

    # Copy to Resources
    backend_src = BUILD_DIR / "backend_dist" / "vpack-backend"
    backend_dst = RESOURCES_DIR / "backend"
    log(f"Copying backend to {backend_dst}")
    shutil.copytree(backend_src, backend_dst)

    log("Backend build complete")

def build_launcher():
    """Build launcher with PyInstaller"""
    log("Building launcher with PyInstaller...")

    # Install desktop dependencies
    requirements = SCRIPT_DIR / "requirements-desktop.txt"
    run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements)])

    # Run PyInstaller
    spec_file = SCRIPT_DIR / "vpack-launcher.spec"
    run_command([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--distpath", str(BUILD_DIR / "launcher_dist"),
        "--workpath", str(BUILD_DIR / "launcher_build"),
        str(spec_file)
    ], cwd=SCRIPT_DIR)

    # Copy executable to MacOS directory
    launcher_exe = BUILD_DIR / "launcher_dist" / "VPACK"
    if launcher_exe.exists():
        shutil.copy2(launcher_exe, MACOS_DIR / "VPACK")
        os.chmod(MACOS_DIR / "VPACK", 0o755)
    else:
        # Fallback: copy from .app bundle if PyInstaller created one
        launcher_app = BUILD_DIR / "launcher_dist" / "VPACK.app"
        if launcher_app.exists():
            src_macos = launcher_app / "Contents" / "MacOS" / "VPACK"
            shutil.copy2(src_macos, MACOS_DIR / "VPACK")
            os.chmod(MACOS_DIR / "VPACK", 0o755)

    log("Launcher build complete")

def copy_resources():
    """Copy additional resources"""
    log("Copying resources...")

    # Copy icon
    icon_src = SCRIPT_DIR / "resources" / "icon.icns"
    if icon_src.exists():
        shutil.copy2(icon_src, RESOURCES_DIR / "icon.icns")
    else:
        # Try to convert from .ico
        ico_src = SCRIPT_DIR / "resources" / "icon.ico"
        if ico_src.exists():
            # Simple copy - ideally convert to .icns
            shutil.copy2(ico_src, RESOURCES_DIR / "icon.icns")

    log("Resources copied")

def create_dmg():
    """Create DMG installer"""
    log("Creating DMG installer...")

    dmg_name = "VPACK-1.0.0-macOS"
    dmg_path = DIST_DIR / f"{dmg_name}.dmg"

    # Check if create-dmg is available
    try:
        run_command(["which", "create-dmg"])
    except:
        log("Warning: create-dmg not found")
        log("Install with: brew install create-dmg")
        log("Creating simple DMG with hdiutil instead...")

        # Fallback to hdiutil
        run_command([
            "hdiutil", "create",
            "-volname", "VPACK",
            "-srcfolder", str(OUTPUT_DIR),
            "-ov",
            "-format", "UDZO",
            str(dmg_path)
        ])

        log(f"DMG created: {dmg_path}")
        return

    # Use create-dmg for prettier installer
    run_command([
        "create-dmg",
        "--volname", "VPACK",
        "--volicon", str(RESOURCES_DIR / "icon.icns") if (RESOURCES_DIR / "icon.icns").exists() else "",
        "--window-pos", "200", "120",
        "--window-size", "600", "400",
        "--icon-size", "100",
        "--icon", "VPACK.app", "150", "190",
        "--hide-extension", "VPACK.app",
        "--app-drop-link", "450", "190",
        str(dmg_path),
        str(OUTPUT_DIR)
    ], check=False)

    log(f"DMG created: {dmg_path}")

def main():
    """Main build process"""
    if sys.platform != "darwin":
        log("Error: This script must run on macOS")
        sys.exit(1)

    log("=" * 50)
    log(f"VPACK macOS Build ({ARCH})")
    log("=" * 50)

    try:
        clean()
        create_info_plist()
        build_frontend()
        download_node()
        build_backend()
        build_launcher()
        copy_resources()
        create_dmg()

        log("=" * 50)
        log("BUILD COMPLETE!")
        log(f"Output: {OUTPUT_DIR}")
        log("=" * 50)

    except Exception as e:
        log(f"BUILD FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
