# MaxEnt-Kernel — Standalone Installer

**For users who prefer not to use GitHub or Python directly.**

---

## Quick Start

1. Download `M-E-K.exe` from this folder
2. Double-click to launch
3. Select a spectral density, adjust parameters, click **Run Comparison**

No Python installation required. Everything is bundled.

---

## Building from Source

If you want to rebuild the executable yourself:

```bash
# Install dependencies
pip install pyinstaller PyQt6 numpy scipy matplotlib

# Run the build script
cd MaxEnt-Kernel/Installer
python build.py
```

The executable appears in this folder as `M-E-K.exe` (Windows) or `M-E-K` (Linux/macOS).

---

## System Requirements

- **Windows** 10/11 (64-bit) or Linux (64-bit) or macOS 12+
- 200 MB disk space
- No internet required after download

---

## What It Does

The solver compares non-Markovian quantum dynamics (with Boltzmann memory kernel derived from MaxEnt) against the standard Lindblad master equation. It shows you when and how much Lindblad fails for structured photonic environments.

---

**Authors:** DESVAUX G.J.Y.  
**DOI:** [10.5281/zenodo.19486927](https://doi.org/10.5281/zenodo.19486927)  
**License:** Proprietary — Scientific license on request with citation  
**Contact:** contact@hopenmind.com  
Copyright (c) 2008-2026 Hope 'n Mind SASU - Research
