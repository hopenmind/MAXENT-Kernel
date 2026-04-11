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
DOI: 10.5281/zenodo.19500872
Contact: contact@hopenmind.com
"""

import os
import sys
import subprocess

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PROGRAM_DIR  = os.path.join(PROJECT_ROOT, "Program")
MAIN_SCRIPT  = os.path.join(PROGRAM_DIR, "main.py")
DATA_DIR     = os.path.join(PROGRAM_DIR, "Data")
ICON_FILE    = os.path.join(PROGRAM_DIR, "ui", "assets", "logo.ico")
OUTPUT_DIR   = SCRIPT_DIR

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
        # Tell PyInstaller where to find our packages
        f"--paths={PROGRAM_DIR}",
        # Collect core, ui, and branding as proper Python packages
        "--collect-submodules=core",
        "--collect-submodules=ui",
        # Hidden imports — our packages
        "--hidden-import=core",
        "--hidden-import=core.kernel",
        "--hidden-import=core.lindblad",
        "--hidden-import=core.compare",
        "--hidden-import=ui",
        "--hidden-import=ui.main_window",
        "--hidden-import=branding",
        # Hidden imports — PyQt6
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        # Hidden imports — matplotlib (main + all export backends)
        "--hidden-import=matplotlib",
        "--hidden-import=matplotlib.backends.backend_qtagg",
        "--hidden-import=matplotlib.backends.backend_pdf",
        "--hidden-import=matplotlib.backends.backend_svg",
        "--hidden-import=matplotlib.backends.backend_ps",
        "--hidden-import=matplotlib.backends.backend_agg",
        # Hidden imports — scipy
        "--hidden-import=scipy.integrate",
        "--hidden-import=scipy.interpolate",
        "--hidden-import=scipy.special",
        "--hidden-import=scipy.special._ufuncs",
        # Hidden imports — numpy
        "--hidden-import=numpy",
        # Exclude heavy packages pulled in via system Python path
        "--exclude-module=torch",
        "--exclude-module=tensorflow",
        "--exclude-module=pandas",
        "--exclude-module=pytest",
        "--exclude-module=sqlalchemy",
        "--exclude-module=pyarrow",
        "--exclude-module=cryptography",
        "--exclude-module=openpyxl",
        "--exclude-module=lxml",
        # Clean build
        "--clean",
        "--noconfirm",
        MAIN_SCRIPT,
    ]

    # Application icon (exe icon + taskbar icon + runtime logo)
    if os.path.isfile(ICON_FILE):
        cmd.insert(-1, f"--icon={ICON_FILE}")
        assets_dir = os.path.dirname(ICON_FILE)
        cmd.insert(-1, f"--add-data={assets_dir}{os.pathsep}ui/assets")

    # Bundle example data files if present
    if os.path.isdir(DATA_DIR) and os.listdir(DATA_DIR):
        cmd.insert(-1, f"--add-data={DATA_DIR}{os.pathsep}Data")

    print("=" * 60)
    print("  MaxEnt-Kernel — Building executable")
    print("  Hope 'n Mind SASU - Research | DOI: 10.5281/zenodo.19500872")
    print("=" * 60)
    print(f"  Source:  {MAIN_SCRIPT}")
    print(f"  Output:  {OUTPUT_DIR}/{EXE_NAME}")
    print("=" * 60)
    print()

    result = subprocess.run(cmd, cwd=PROGRAM_DIR)

    if result.returncode == 0:
        exe_ext  = ".exe" if sys.platform == "win32" else ""
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
