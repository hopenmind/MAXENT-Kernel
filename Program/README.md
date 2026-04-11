# MaxEnt-Kernel — Program Guide

## Requirements

```
Python >= 3.9
numpy >= 1.24
scipy >= 1.10
matplotlib >= 3.7      (for plots)
PyQt6 >= 6.5           (for GUI only)
```

Install everything at once:

```bash
pip install numpy scipy matplotlib PyQt6
```

---

## Two Ways to Run

### 1. GUI Mode (default)

```bash
cd Program
python main.py
```

A desktop window opens with three tabs to define your spectral density:

| Tab | What it does |
|-----|-------------|
| **Built-in J(ω)** | Select a preset: Ohmic, Lorentzian, Band Edge, Photonic Crystal, Waveguide QED |
| **Custom Formula** | Type a Python expression, e.g. `0.1 * w**2 * np.exp(-w / 8)`. Variable is `w`. |
| **CSV Data** | Import your measured J(ω) from a file. Format: 2 columns (omega, J), header row skipped. |

Then set your parameters (coupling g, temperature T, frequency ω₀, simulation time, step size), click **Run Comparison**, and read the results.

### 2. CLI Mode (headless)

```bash
cd Program
python main.py --cli [options]
```

Full list of options:

```
Source (pick one):
  -s, --spectral {ohmic,super_ohmic,lorentzian,band_edge,photonic_crystal,waveguide}
  --csv PATH          Import measured J(ω) from CSV file
  -f, --formula EXPR  Custom formula, e.g. '0.1*w*np.exp(-w/10)'

Parameters:
  --g FLOAT           Coupling constant       (default: 0.3)
  --T FLOAT           Effective temperature    (default: 0.1)
  --omega0 FLOAT      Emitter frequency ω₀    (default: 5.0)
  --tmax FLOAT        Max simulation time      (default: 30.0)
  --dt FLOAT          Time step                (default: 0.2)

Output:
  -o, --outdir PATH   Output directory         (default: ../Results/)
  --no-plot           Skip plot generation
  --no-save           Print summary only, do not write files
```

---

## Examples

**Built-in Lorentzian cavity:**

```bash
python main.py --cli -s lorentzian --g 0.3 --T 0.1 --omega0 5.0
```

**Your own formula:**

```bash
python main.py --cli --formula '0.05**1.5 / np.sqrt(w - 5) if w > 5 else 0' --omega0 5.5
```

**Your measured data from a CSV:**

```bash
python main.py --cli --csv ../Data/my_measurement.csv --g 0.2 --T 0.05
```

**Save results to a specific folder:**

```bash
python main.py --cli -s waveguide --outdir /path/to/my/results
```

---

## Where Do Results Go?

After each run (GUI with auto-save enabled, or CLI without `--no-save`), three files are written:

| File | Content |
|------|---------|
| `comparison_YYYYMMDD_HHMMSS.png` | 4-panel plot: populations, coherences, trace distance, memory kernel |
| `data_YYYYMMDD_HHMMSS.csv` | Full time series: time, P_e (NM + Lindblad), coherences, trace distance |
| `summary_YYYYMMDD_HHMMSS.txt` | Text summary: regime, memory parameter P, spread σ_K, max deviation, all input parameters |

Default output folder: `MaxEnt-Kernel/Results/`

In the GUI, you can change this via **File → Set Output Folder** or the "Change..." button.

---

## CSV Input Format

If you have experimental J(ω) data, save it as a CSV:

```csv
omega,J
0.10,0.003
0.20,0.012
0.50,0.045
1.00,0.089
2.00,0.120
5.00,0.034
10.0,0.002
```

Rules:
- First row is a header (skipped automatically)
- Two columns: frequency (omega) and spectral density J(omega)
- Comma, tab, or space separation all work
- The solver interpolates linearly between your points
- Values outside your data range are set to 0

---

## How to Interpret Results

| Metric | Meaning |
|--------|---------|
| **Regime** | Markovian (P < 0.1), Weakly NM (0.1 < P < 1), Strongly NM (P > 1) |
| **Memory parameter P** | = g × τ_c (coupling × correlation time). Higher = more non-Markovian. |
| **Memory spread σ_K** | Width of the kernel distribution. Broader = longer-range memory. |
| **Max trace distance** | Largest difference between NM and Lindblad. If < 0.01, Lindblad is fine. |
| **Lindblad valid** | Yes/No based on the 1% trace distance threshold. |

---

## File Structure

```
Program/
├── main.py             ← Entry point (GUI or --cli)
├── core/
│   ├── __init__.py     ← Package init + version/DOI
│   ├── kernel.py       ← MemoryKernel class (Boltzmann kernel from MaxEnt)
│   ├── lindblad.py     ← LindbladSolver class (Markovian baseline)
│   └── compare.py      ← compare() function + SpectralDensities library
├── ui/
│   ├── __init__.py
│   └── main_window.py  ← PyQt6 GUI application
├── Data/               ← Place your CSV files here (optional)
└── README.md           ← This file
```

---

**Authors:** DESVAUX G.J.Y. et al.  
**DOI:** [10.5281/zenodo.19500872](https://doi.org/10.5281/zenodo.19500872)  
**License:** Proprietary — Scientific license on request with citation  
**Contact:** contact@hopenmind.com  
**Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.**
