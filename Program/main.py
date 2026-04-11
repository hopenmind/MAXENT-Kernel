#!/usr/bin/env python3
"""
MaxEnt-Kernel — Application entry point.

Two modes:
  python main.py          → Launch PyQt6 GUI
  python main.py --cli    → Run comparison from command line

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19500872
Contact: contact@hopenmind.com
"""

import sys
import os
import time
import argparse
import numpy as np


def cli_run():
    """
    Command-line comparison (headless mode).

    Supports built-in spectral densities, custom formulas, and CSV import.
    Saves plot + CSV + summary to the output directory.
    """
    # Ensure core is importable (supports both normal and PyInstaller frozen mode)
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)
    from core import compare, SpectralDensities, MemoryKernel
    from branding import BrandingConfig

    parser = argparse.ArgumentParser(
        prog="MaxEnt-Kernel CLI",
        description=(
            "Non-Markovian vs Lindblad comparison solver.\n"
            "Hope 'n Mind SASU - Research — DOI: 10.5281/zenodo.19500872"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --cli -s lorentzian --g 0.3 --T 0.1\n"
            "  python main.py --cli --csv measured_J.csv --omega0 5.0\n"
            "  python main.py --cli --formula '0.1 * w * np.exp(-w/10)'\n"
            "  python main.py --cli -s band_edge --outdir ./my_results\n"
            "\n"
            "Output files (written to --outdir):\n"
            "  comparison_TIMESTAMP.png  — 4-panel plot\n"
            "  data_TIMESTAMP.csv        — full time series\n"
            "  summary_TIMESTAMP.txt     — regime + parameters\n"
            "\n"
            "CSV format for --csv:\n"
            "  First row = header (skipped)\n"
            "  Column 1 = omega (frequency)\n"
            "  Column 2 = J(omega) (spectral density)\n"
            "  Separators: comma, tab, or space\n"
        )
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--spectral", "-s", default=None,
        choices=["ohmic", "super_ohmic", "lorentzian", "band_edge",
                 "photonic_crystal", "waveguide"],
        help="Built-in spectral density type (default: lorentzian)"
    )
    source_group.add_argument(
        "--csv", type=str, default=None,
        help="Path to CSV file with measured J(ω) [2 columns: omega, J]"
    )
    source_group.add_argument(
        "--formula", "-f", type=str, default=None,
        help="Custom J(ω) as Python expression. Variable: w. Example: '0.1*w*np.exp(-w/10)'"
    )

    parser.add_argument("--g", type=float, default=0.3, help="Coupling constant (default: 0.3)")
    parser.add_argument("--T", type=float, default=0.1, help="Effective temperature (default: 0.1)")
    parser.add_argument("--omega0", type=float, default=5.0, help="Emitter frequency (default: 5.0)")
    parser.add_argument("--tmax", type=float, default=30.0, help="Max simulation time (default: 30.0)")
    parser.add_argument("--dt", type=float, default=0.2, help="Time step (default: 0.2)")
    parser.add_argument("--outdir", "-o", type=str, default=None,
                        help="Output directory (default: ../Results/)")
    parser.add_argument("--no-plot", action="store_true",
                        help="Skip plot generation (text summary only)")
    parser.add_argument("--no-save", action="store_true",
                        help="Do not auto-save files (print to stdout only)")

    args = parser.parse_args()

    # ── Determine spectral density ──

    source_label = ""

    if args.csv:
        from scipy.interpolate import interp1d
        if not os.path.isfile(args.csv):
            print(f"ERROR: File not found: {args.csv}")
            sys.exit(1)
        data = np.genfromtxt(args.csv, delimiter=',', skip_header=1)
        if data.ndim == 1:
            data = np.genfromtxt(args.csv, skip_header=1)
        if data.ndim == 1 or data.shape[1] < 2:
            print("ERROR: CSV must have 2 columns: omega, J(omega)")
            sys.exit(1)
        J_interp = interp1d(data[:, 0], data[:, 1], kind='linear',
                             fill_value=0.0, bounds_error=False)
        J = lambda w: float(J_interp(w))
        source_label = f"CSV: {os.path.basename(args.csv)} ({data.shape[0]} pts)"
        print(f"Loaded CSV: {args.csv} ({data.shape[0]} data points)")

    elif args.formula:
        formula = args.formula
        def J(w):
            try:
                return float(eval(formula, {"__builtins__": {}},
                                  {"w": w, "np": np, "pi": np.pi,
                                   "exp": np.exp, "sqrt": np.sqrt,
                                   "sin": np.sin, "cos": np.cos,
                                   "log": np.log, "abs": abs}))
            except Exception:
                return 0.0
        # Quick validation
        test = J(1.0)
        if not np.isfinite(test):
            print(f"ERROR: Formula returned non-finite at ω=1: {test}")
            sys.exit(1)
        source_label = f"Formula: {formula[:50]}"
        print(f"Using custom formula: {formula}")

    else:
        # Built-in (default to lorentzian)
        sd_name = args.spectral or "lorentzian"
        sd_map = {
            "ohmic": SpectralDensities.ohmic(eta=0.1, wc=10.0, s=1),
            "super_ohmic": SpectralDensities.ohmic(eta=0.01, wc=10.0, s=3),
            "lorentzian": SpectralDensities.lorentzian(gamma=0.5, wc=5.0, width=0.3),
            "band_edge": SpectralDensities.band_edge(beta=0.05, we=5.0),
            "photonic_crystal": SpectralDensities.photonic_crystal(beta=0.05, we=5.0),
            "waveguide": SpectralDensities.waveguide(gamma_1d=0.5, tau_rt=1.0, r=0.9),
        }
        J = sd_map[sd_name]
        source_label = f"Built-in: {sd_name}"
        print(f"Using built-in spectral density: {sd_name}")

    # ── Load branding ──
    branding = BrandingConfig.load()

    # ── Run solver ──

    print(f"Parameters: g={args.g}, T={args.T}, ω₀={args.omega0}, "
          f"t_max={args.tmax}, dt={args.dt}")
    print("Computing...")

    result = compare(J, g=args.g, T=args.T, omega0=args.omega0,
                     t_max=args.tmax, dt=args.dt)

    print()
    print(result.summary())

    # ── Output ──

    if args.no_save:
        if not args.no_plot:
            result.plot(show=True)
        return

    # Determine output directory
    if args.outdir:
        outdir = os.path.abspath(args.outdir)
    else:
        outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Results'))

    os.makedirs(outdir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Save plot
    if not args.no_plot:
        plot_path = os.path.join(outdir, f"comparison_{timestamp}.png")
        result.plot(show=False, save=plot_path, branding=branding,
                    source_label=source_label)
        print(f"\nPlot saved:    {plot_path}")

    # Save CSV
    csv_path = os.path.join(outdir, f"data_{timestamp}.csv")
    t = result.t
    header = "time,P_e_NM,P_e_Lindblad,coherence_NM,coherence_Lindblad,trace_distance"
    out_data = np.column_stack([
        t, result.nm.populations, result.markov.populations,
        result.nm.coherences, result.markov.coherences,
        result.trace_distance
    ])
    np.savetxt(csv_path, out_data, delimiter=',', header=header, comments='')
    print(f"Data saved:    {csv_path}")

    # Save summary
    summary_path = os.path.join(outdir, f"summary_{timestamp}.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(branding.summary_header())
        f.write("\n\n")
        f.write(result.summary())
        f.write(f"\n\nSource: {source_label}\n")
        f.write(f"Parameters: g={args.g}, T={args.T}, omega0={args.omega0}, "
                f"t_max={args.tmax}, dt={args.dt}\n")
        f.write(f"Output dir: {outdir}\n")
        if branding.footer_text:
            f.write(f"\n{branding.footer_text}\n")
    print(f"Summary saved: {summary_path}")

    print(f"\nAll output files in: {outdir}")


def gui_run():
    """Launch the PyQt6 GUI."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)
    from ui.main_window import main
    main()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        sys.argv.remove("--cli")
        cli_run()
    else:
        gui_run()
