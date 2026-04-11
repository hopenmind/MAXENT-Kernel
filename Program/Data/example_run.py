#!/usr/bin/env python3
"""
MaxEnt-Kernel — Example Script
================================

Demonstrates how to use the solver with:
  1. A built-in spectral density
  2. A custom formula
  3. Imported CSV data

This example uses GENERIC textbook parameters (Drude-Lorentz model),
not associated with any specific experimental research.

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
DOI: 10.5281/zenodo.19500872
Contact: contact@hopenmind.com
"""

import sys
import os
import numpy as np

# Make core importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core import compare, SpectralDensities, MemoryKernel
from core.lindblad import LindbladSolver


def example_builtin():
    """Example 1: Use a built-in spectral density."""
    print("=" * 60)
    print("  Example 1 — Built-in Ohmic spectral density")
    print("=" * 60)

    # Standard Ohmic bath (textbook parameters)
    J = SpectralDensities.ohmic(eta=0.05, wc=8.0, s=1)

    result = compare(J, g=0.2, T=0.08, omega0=3.0, t_max=25.0, dt=0.3)
    print(result.summary())

    # Save plot
    outdir = os.path.join(os.path.dirname(__file__), '..', '..', 'Results')
    os.makedirs(outdir, exist_ok=True)
    result.plot(show=False, save=os.path.join(outdir, "example_ohmic.png"))
    print(f"Plot saved to Results/example_ohmic.png\n")


def example_custom_formula():
    """Example 2: Use a custom spectral density formula."""
    print("=" * 60)
    print("  Example 2 — Custom Drude-Lorentz formula")
    print("=" * 60)

    # Drude-Lorentz model: J(ω) = η ω Γ / (ω² + Γ²)
    # This is a standard textbook model, not specific to any experiment.
    eta = 0.15
    Gamma = 2.0

    def J_drude(w):
        if w <= 0:
            return 0.0
        return eta * w * Gamma / (w**2 + Gamma**2)

    result = compare(J_drude, g=0.25, T=0.12, omega0=3.0, t_max=20.0, dt=0.3)
    print(result.summary())

    outdir = os.path.join(os.path.dirname(__file__), '..', '..', 'Results')
    result.plot(show=False, save=os.path.join(outdir, "example_drude.png"))
    print(f"Plot saved to Results/example_drude.png\n")


def example_csv():
    """Example 3: Import J(ω) from a CSV file."""
    print("=" * 60)
    print("  Example 3 — CSV import (synthetic Drude-Lorentz data)")
    print("=" * 60)

    csv_path = os.path.join(os.path.dirname(__file__), "example_spectral_density.csv")

    if not os.path.isfile(csv_path):
        print(f"CSV file not found: {csv_path}")
        return

    from scipy.interpolate import interp1d

    data = np.genfromtxt(csv_path, delimiter=',', skip_header=1)
    J_interp = interp1d(data[:, 0], data[:, 1], kind='linear',
                         fill_value=0.0, bounds_error=False)

    def J_csv(w):
        return float(J_interp(w))

    print(f"Loaded {data.shape[0]} data points from {os.path.basename(csv_path)}")

    result = compare(J_csv, g=0.2, T=0.1, omega0=3.0, t_max=20.0, dt=0.3)
    print(result.summary())

    outdir = os.path.join(os.path.dirname(__file__), '..', '..', 'Results')
    result.plot(show=False, save=os.path.join(outdir, "example_csv_import.png"))
    print(f"Plot saved to Results/example_csv_import.png\n")


def example_direct_api():
    """Example 4: Use the low-level API directly (no compare wrapper)."""
    print("=" * 60)
    print("  Example 4 — Direct API usage")
    print("=" * 60)

    # Define a simple spectral density
    J = lambda w: 0.1 * w * np.exp(-w / 6) if w > 0 else 0.0

    # Build memory kernel from spectral density
    K = MemoryKernel.from_spectral_density(J, g=0.2, T=0.1, omega0=3.0,
                                            t_max=20.0, dt=0.3)

    # Initial state: excited state on Bloch sphere
    rho0 = np.array([0.0, 0.0, 1.0])
    tspan = np.arange(0, 20.0, 0.3)

    # Solve non-Markovian
    nm = K.solve(rho0, tspan)

    # Solve Lindblad for comparison
    L = LindbladSolver.from_spectral_density(J, g=0.2, omega0=3.0)
    m = L.solve(rho0, tspan)

    # Metrics
    td = nm.trace_distance_from(m)
    print(f"  Max trace distance:    {np.max(td):.4f}")
    print(f"  Non-Markovianity P:    {K.non_markovianity():.4f}")
    print(f"  Memory spread σ_K:     {K.memory_spread():.4f}")
    print(f"  Markovian rate γ:      {K.gamma_markov:.4f}")
    print(f"  Final P_e (NM):        {nm.populations[-1]:.4f}")
    print(f"  Final P_e (Lindblad):  {m.populations[-1]:.4f}")
    print()


if __name__ == "__main__":
    example_builtin()
    example_custom_formula()
    example_csv()
    example_direct_api()

    print("=" * 60)
    print("  All examples completed successfully.")
    print("  Check Results/ folder for output plots.")
    print("=" * 60)
