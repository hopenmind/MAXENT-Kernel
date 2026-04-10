# MaxEnt-Kernel

**Non-Markovian Quantum Dynamics Solver with Boltzmann Memory Kernel**

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.19486927-blue)](https://doi.org/10.5281/zenodo.19486927)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)
[![Python](https://img.shields.io/badge/Python-≥3.9-green)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-orange)](https://www.riverbankcomputing.com/software/pyqt/)

---

## Why This Solver Exists

Every quantum photonics lab measures the spectral density J(ω) of their environment — a cavity, a photonic crystal, a waveguide. Then, to predict how their qubit decoheres, they plug it into the Lindblad master equation. It's the default. Everybody does it.

The problem is that Lindblad assumes the environment forgets instantly. No memory. And everybody knows this is wrong as soon as the spectral density has structure — a sharp peak, a band edge, discrete modes. In those cases, the environment remembers, and Lindblad gives the wrong answer. Coherence decays too fast. Population revivals vanish. The prediction diverges from reality.

The reason people keep using Lindblad anyway is that the alternatives are painful. Full non-Markovian methods (Nakajima-Zwanzig, HEOM, process tensor) are either system-specific, computationally heavy, or require expertise that most experimentalists don't have time for.

**This solver is the missing middle ground.** You give it your J(ω) — measured, fitted, or theoretical — and it:

1. Computes the bath correlation function C(τ) from your spectral density
2. Builds a memory kernel K*(t,s) using the Maximum Entropy (Jaynes MaxEnt) principle — the least-biased kernel consistent with your environment's correlations
3. Solves the full integro-differential master equation with that kernel
4. Solves the standard Lindblad equation in parallel
5. Tells you exactly how much they disagree, where, and why

If the trace distance between the two solutions stays below 1%, Lindblad is fine for your system — you can stop worrying. If it's at 10% or more, your Lindblad predictions are wrong and the solver shows you what non-Markovian dynamics actually look like for your specific environment: population revivals, slower coherence decay, power-law tails instead of exponentials.

**It's a diagnostic tool.** Not a replacement for full theory, but a detector that says "here, Lindblad lies" — and shows you what the truth looks like.

---

## Theory in 3 Equations

**Equation 1** — Generalized master equation with memory:

$$\frac{d\rho}{dt} = -i[H, \rho(t)] + \int_0^t K(t,s)\,\mathcal{D}[\rho(s)]\,ds$$

**Equation 2** — Boltzmann kernel (derived from MaxEnt, not postulated):

$$K^*(t,s) = \frac{1}{Z(t)} \exp\!\left(-\frac{e(t,s)}{T}\right), \quad e(t,s) = \int_s^t |C(\tau-s)|^2 d\tau$$

**Equation 3** — Bath correlation from spectral density:

$$C(\tau) = g^2 \int_0^\infty J(\omega)\,e^{-i(\omega-\omega_0)\tau}\,d\omega$$

That's it. Input J(ω), get K*(t,s), solve dynamics.

---

## Install

```bash
pip install numpy scipy matplotlib
```

No other dependencies for the solver. For the GUI: `pip install PyQt6`.

---

## 3 Ways to Use It

### A. Desktop GUI (recommended for most users)

```bash
cd Program
python main.py
```

The GUI lets you choose from built-in spectral densities, type a custom formula, or import your own measured J(ω) from a CSV file. Results are auto-saved to the output folder after each run.

### B. Command Line (headless, scriptable)

```bash
cd Program
python main.py --cli -s lorentzian --g 0.3 --T 0.1 --omega0 5.0
python main.py --cli --csv my_data.csv --outdir ./results
python main.py --cli --formula '0.1 * w * np.exp(-w/10)'
```

Prints summary to stdout, saves plot + CSV + summary to the output directory.

### C. Standalone Executable (no Python needed)

Download `Installer/M-E-K.exe` and double-click. Everything is bundled.

---

## Bring Your Own Data

**Custom formula** — type any Python expression using `w` as the frequency variable:

```
0.05**1.5 / np.sqrt(w - 5) if w > 5 else 0
```

**CSV file** — 2 columns (omega, J), header row, comma/tab/space separated:

```csv
omega,J
0.1,0.003
1.0,0.089
5.0,0.034
```

The solver interpolates linearly between your data points.

---

## Where Results Go

After each run, three files are saved automatically:

| File | Content |
|------|---------|
| `comparison_TIMESTAMP.png` | 4-panel plot (populations, coherences, trace distance, kernel) |
| `data_TIMESTAMP.csv` | Full time series for post-processing |
| `summary_TIMESTAMP.txt` | Regime classification + all parameters |

Default folder: `MaxEnt-Kernel/Results/`. Changeable in the GUI or via `--outdir` in CLI.

---

## Project Structure

```
MaxEnt-Kernel/
├── Program/
│   ├── core/               # Solver engine
│   │   ├── kernel.py       # MemoryKernel (MaxEnt Boltzmann kernel)
│   │   ├── lindblad.py     # LindbladSolver (Markovian baseline)
│   │   └── compare.py      # Comparison + SpectralDensities library
│   ├── ui/
│   │   └── main_window.py  # PyQt6 desktop GUI
│   ├── Data/               # Example data + your CSV files
│   └── main.py             # Entry point (GUI or CLI)
├── Installer/
│   ├── build.py            # PyInstaller build script
│   └── readme.md           # Installer instructions
├── Results/                # Auto-generated output (plots, CSV, summaries)
│   └── *.png              # Example comparison plots included
├── README.md               # This file
├── SECURITY.md             # Security policy
├── LICENSE                 # Proprietary license
├── CONTRIBUTING.md         # Contribution policy (CLA required)
├── CODE_OF_CONDUCT.md      # Scientific integrity standards
└── CITATION.cff            # Citation metadata
```

---

## Built-in Spectral Densities

| Name | Formula | Use case |
|------|---------|----------|
| `SpectralDensities.ohmic(eta, wc, s)` | η ωˢ e^{-ω/ωc} | Generic thermal bath |
| `SpectralDensities.lorentzian(gamma, wc, width)` | Lorentzian peak | Single-mode cavity |
| `SpectralDensities.band_edge(beta, we)` | β^{3/2} / √(ω−ωe) | Photonic crystal edge |
| `SpectralDensities.photonic_crystal(beta, we, gap)` | Band edge + gap | PhC with band gap |
| `SpectralDensities.waveguide(gamma_1d, tau_rt, r)` | Periodic peaks | Waveguide QED with mirror |

---

## What the Results Tell You

- **Max trace distance < 0.01** → Lindblad is fine for your system. Stop worrying.
- **Max trace distance > 0.01** → Lindblad is wrong. The solver shows you by how much, where in time, and what the non-Markovian dynamics actually look like.
- **Memory parameter P < 0.1** → Markovian regime. P > 1 → strongly non-Markovian.
- **Memory kernel shape** → shows where the memory comes from: exponential decay (cavity), power-law tail (band edge), oscillatory revivals (waveguide modes).

---

## Use Your Own J(ω) in Python

```python
import numpy as np
from Program.core import MemoryKernel
from Program.core.lindblad import LindbladSolver

# YOUR measured spectral density
J = lambda w: 0.1 * w**3 * np.exp(-w / 10)

# Build memory kernel
K = MemoryKernel.from_spectral_density(J, g=0.1, T=0.05, omega0=5.0)

# Solve non-Markovian dynamics
rho0 = np.array([0, 0, 1])  # excited state
nm = K.solve(rho0, np.linspace(0, 50, 200))

# Compare with Lindblad
L = LindbladSolver.from_spectral_density(J, g=0.1, omega0=5.0)
m = L.solve(rho0, np.linspace(0, 50, 200))

print(f"Max deviation: {np.max(nm.trace_distance_from(m)):.4f}")
print(f"Non-Markovianity P = {K.non_markovianity():.4f}")
```

---

## Known Limitations

1. **Weak-coupling regime only.** The energy functional e(t,s) is computed using a mean-field factorization ρ_SE ≈ ρ_S ⊗ ρ_E, valid at order g << ω₀. At strong coupling (g > 1), the factorization breaks and the solver's predictions become unreliable. This is a stated domain of validity, not a bug.

2. **MaxEnt kernel is true by construction.** The kernel K*(t,s) is the least-biased distribution consistent with the bath correlations. You cannot falsify MaxEnt itself. What you CAN falsify is whether nature's memory kernel matches the MaxEnt prediction for a specific J(ω). If your measured decay curve disagrees with the solver's output, the MaxEnt kernel is wrong for that environment — and that's a publishable result.

3. **No experimental data included.** This solver is a theoretical diagnostic tool. It predicts what non-Markovian dynamics should look like given J(ω). Comparing its predictions with actual lab measurements is the researcher's job.

---

## Reference

DESVAUX G.J.Y. (2008-2026). *MaxEnt-Kernel: Non-Markovian Quantum Dynamics Solver with Boltzmann Memory Kernel.*
DOI: [10.5281/zenodo.19486927](https://doi.org/10.5281/zenodo.19486927)
ORCID: [0009-0008-9813-4627](https://orcid.org/0009-0008-9813-4627)

---

## License

**Proprietary** — Copyright (c) 2008 - 2026 Hope 'n Mind Research. All rights reserved.

A free scientific license is available on request for academic and non-profit research, subject to citation. Contact: contact@hopenmind.com

See [LICENSE](LICENSE) for full terms.
# MAXENT-Kernel
