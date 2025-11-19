#!/usr/bin/env python3
"""
VPACK Windows Build Script
Build .exe installer cho Windows

Yêu cầu:
- Python 3.10+
- Node.js 18+
- Inno Setup 6+ (iscc.exe trong PATH)

Chạy từ thư mục desktop/:
    python build_windows.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import urllib.request
import zipfile

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = SCRIPT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
BUILD_DIR = SCRIPT_DIR / "build"
DIST_DIR = SCRIPT_DIR / "dist"
OUTPUT_DIR = DIST_DIR / "VPACK"

# Node.js portable version for bundling
NODE_VERSION = "18.19.0"
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip"

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
    BUILD_DIR.mkdir(parents=True)
    DIST_DIR.mkdir(parents=True)
    OUTPUT_DIR.mkdir(parents=True)

def build_frontend():
    """Build Next.js frontend in standalone mode"""
    log("Building frontend...")

    # Install dependencies
    run_command(["npm", "ci", "--legacy-peer-deps"], cwd=FRONTEND_DIR)

    # Build
    run_command(["npm", "run", "build"], cwd=FRONTEND_DIR)

    # Copy standalone output
    standalone_src = FRONTEND_DIR / ".next" / "standalone"
    standalone_dst = OUTPUT_DIR / "frontend" / "standalone"

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
    """Download portable Node.js for Windows"""
    log(f"Downloading Node.js v{NODE_VERSION}...")

    node_zip = BUILD_DIR / "node.zip"
    node_extract = BUILD_DIR / "node"

    # Download
    urllib.request.urlretrieve(NODE_URL, node_zip)

    # Extract
    with zipfile.ZipFile(node_zip, 'r') as zip_ref:
        zip_ref.extractall(node_extract)

    # Find node.exe
    node_dir = list(node_extract.glob("node-*"))[0]
    node_exe_src = node_dir / "node.exe"
    node_exe_dst = OUTPUT_DIR / "frontend" / "node.exe"

    log(f"Copying node.exe to {node_exe_dst}")
    shutil.copy2(node_exe_src, node_exe_dst)

    log("Node.js download complete")

def build_backend():
    """Build backend with PyInstaller"""
    log("Building backend with PyInstaller...")

    # Install PyInstaller if needed
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

    # Copy to output
    backend_src = BUILD_DIR / "backend_dist" / "vpack-backend"
    backend_dst = OUTPUT_DIR / "backend"
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

    # Copy to output
    launcher_exe = BUILD_DIR / "launcher_dist" / "VPACK.exe"
    if launcher_exe.exists():
        shutil.copy2(launcher_exe, OUTPUT_DIR / "VPACK.exe")
    else:
        # One-dir mode
        launcher_dir = BUILD_DIR / "launcher_dist" / "VPACK"
        for item in launcher_dir.iterdir():
            dst = OUTPUT_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)

    log("Launcher build complete")

def copy_resources():
    """Copy additional resources"""
    log("Copying resources...")

    # Create resources directory
    resources_dst = OUTPUT_DIR / "resources"
    resources_dst.mkdir(exist_ok=True)

    # Copy icon if exists
    icon_src = SCRIPT_DIR / "resources" / "icon.ico"
    if icon_src.exists():
        shutil.copy2(icon_src, resources_dst / "icon.ico")

    # Create default directories
    for dir_name in ["data", "logs"]:
        (OUTPUT_DIR / dir_name).mkdir(exist_ok=True)

    log("Resources copied")

def create_installer():
    """Create installer using Inno Setup"""
    log("Creating installer with Inno Setup...")

    iss_file = SCRIPT_DIR / "inno_setup.iss"
    if not iss_file.exists():
        log("Warning: inno_setup.iss not found, skipping installer creation")
        return

    # Check if iscc is available
    try:
        run_command(["iscc", "/?"])
    except:
        log("Warning: Inno Setup (iscc) not found in PATH")
        log("Please install Inno Setup from https://jrsoftware.org/isinfo.php")
        return

    # Run Inno Setup
    run_command(["iscc", str(iss_file)], cwd=SCRIPT_DIR)

    log("Installer created successfully")

def main():
    """Main build process"""
    log("=" * 50)
    log("VPACK Windows Build")
    log("=" * 50)

    try:
        clean()
        build_frontend()
        download_node()
        build_backend()
        build_launcher()
        copy_resources()
        create_installer()

        log("=" * 50)
        log("BUILD COMPLETE!")
        log(f"Output directory: {OUTPUT_DIR}")
        log("=" * 50)

        # List output
        log("Contents:")
        for item in sorted(OUTPUT_DIR.rglob("*")):
            if item.is_file():
                rel_path = item.relative_to(OUTPUT_DIR)
                size_mb = item.stat().st_size / (1024 * 1024)
                log(f"  {rel_path} ({size_mb:.1f} MB)")

    except Exception as e:
        log(f"BUILD FAILED: {e}")
        raise

if __name__ == "__main__":
    main()
