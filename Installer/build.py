#!/usr/bin/env python3
"""
PyInstaller build script for MaxEnt-Kernel.

Usage:
    cd MaxEnt-Kernel/Installer
    python build.py

Produces: Installer/M-E-K.exe (Windows) or M-E-K (Linux/macOS)

Requirements:
    pip install pyinstaller PyQt6 numpy scipy matplotlib

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19486927
Contact: contact@hopenmind.com
"""

import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROGRAM_DIR = os.path.join(PROJECT_ROOT, "Program")
MAIN_SCRIPT = os.path.join(PROGRAM_DIR, "main.py")
DATA_DIR = os.path.join(PROGRAM_DIR, "Data")
OUTPUT_DIR = SCRIPT_DIR

EXE_NAME = "M-E-K"


def build():
    """Run PyInstaller to produce a one-file executable."""
    if not os.path.exists(MAIN_SCRIPT):
        print(f"ERROR: {MAIN_SCRIPT} not found.")
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        f"--name={EXE_NAME}",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath={os.path.join(OUTPUT_DIR, '_build')}",
        f"--specpath={os.path.join(OUTPUT_DIR, '_build')}",
        # Include core and ui packages
        f"--add-data={os.path.join(PROGRAM_DIR, 'core')}{os.pathsep}core",
        f"--add-data={os.path.join(PROGRAM_DIR, 'ui')}{os.pathsep}ui",
        # Hidden imports for PyQt6 + matplotlib + scipy
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_qtagg",
        "--hidden-import=scipy.integrate",
        "--hidden-import=scipy.interpolate",
        "--hidden-import=numpy",
        # Clean build
        "--clean",
        "--noconfirm",
        MAIN_SCRIPT,
    ]

    # Add data dir if it has content
    if os.path.isdir(DATA_DIR) and os.listdir(DATA_DIR):
        cmd.insert(-1, f"--add-data={DATA_DIR}{os.pathsep}Data")

    print("=" * 60)
    print("  MaxEnt-Kernel — Building executable")
    print("  Hope 'n Mind Research | DOI: 10.5281/zenodo.19486927")
    print("=" * 60)
    print(f"  Source:  {MAIN_SCRIPT}")
    print(f"  Output:  {OUTPUT_DIR}/{EXE_NAME}")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, cwd=PROGRAM_DIR)

    if result.returncode == 0:
        exe_ext = ".exe" if sys.platform == "win32" else ""
        exe_path = os.path.join(OUTPUT_DIR, f"{EXE_NAME}{exe_ext}")
        print()
        print("=" * 60)
        print(f"  BUILD SUCCESS: {exe_path}")
        print("=" * 60)
    else:
        print()
        print("BUILD FAILED — check output above.")
        sys.exit(1)


if __name__ == "__main__":
    build()
