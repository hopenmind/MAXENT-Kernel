"""
MaxEnt-Kernel — PyQt6 Desktop GUI
===================================

Desktop application for non-Markovian quantum dynamics simulation.
Researchers can:
  - Select built-in spectral densities OR enter a custom formula
  - Import measured J(ω) from CSV files
  - Adjust all physical parameters
  - Choose an output folder for results
  - Run NM vs Lindblad comparisons
  - Export plots (PNG/PDF/SVG) and data (CSV)

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19486927
Contact: contact@hopenmind.com
"""

import sys
import os
import time
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QComboBox, QDoubleSpinBox, QPushButton,
    QTextEdit, QLineEdit, QSplitter, QStatusBar, QMenuBar,
    QFileDialog, QMessageBox, QProgressBar, QGridLayout,
    QTabWidget, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Resolve base directory (supports both normal and PyInstaller frozen mode)
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

from core import compare, SpectralDensities, MemoryKernel
from core.lindblad import LindbladSolver


# ─────────────────────────────────────────────────────────
# Worker thread
# ─────────────────────────────────────────────────────────

class SimulationWorker(QThread):
    """Run simulation in background thread."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, J, g, T, omega0, t_max, dt):
        super().__init__()
        self.J = J
        self.g = g
        self.T = T
        self.omega0 = omega0
        self.t_max = t_max
        self.dt = dt

    def run(self):
        try:
            result = compare(self.J, g=self.g, T=self.T, omega0=self.omega0,
                             t_max=self.t_max, dt=self.dt)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────
# Matplotlib canvas
# ─────────────────────────────────────────────────────────

class PlotCanvas(FigureCanvas):
    """Embedded matplotlib figure."""

    def __init__(self, parent=None, width=10, height=8):
        self.fig = Figure(figsize=(width, height), dpi=100)
        super().__init__(self.fig)
        self.setParent(parent)

    def plot_result(self, result):
        self.fig.clear()
        self.fig.suptitle(
            "Non-Markovian vs Lindblad Dynamics\n"
            "Hope 'n Mind SASU - Research — DOI: 10.5281/zenodo.19486927",
            fontsize=11, fontweight='bold'
        )

        ax1 = self.fig.add_subplot(221)
        ax1.plot(result.t, result.nm.populations, 'b-', lw=2, label='Non-Markovian')
        ax1.plot(result.t, result.markov.populations, 'r--', lw=2, label='Lindblad')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('P_e(t)')
        ax1.set_title('Excited State Population')
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        ax2 = self.fig.add_subplot(222)
        ax2.plot(result.t, result.nm.coherences, 'b-', lw=2, label='Non-Markovian')
        ax2.plot(result.t, result.markov.coherences, 'r--', lw=2, label='Lindblad')
        ax2.set_xlabel('Time')
        ax2.set_ylabel('|ρ₀₁(t)|')
        ax2.set_title('Coherence')
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)

        ax3 = self.fig.add_subplot(223)
        td = result.trace_distance
        ax3.plot(result.t, td, 'k-', lw=2)
        ax3.axhline(0.01, color='orange', ls='--', label='1% threshold')
        ax3.fill_between(result.t, 0, td, alpha=0.2, color='purple')
        ax3.set_xlabel('Time')
        ax3.set_ylabel('D(ρ_NM, ρ_M)')
        ax3.set_title(f'Trace Distance — Max: {result.max_deviation:.4f}')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)

        ax4 = self.fig.add_subplot(224)
        t_mid = result.kernel.t_max / 2
        s_vals, K_vals = result.kernel.kernel_at(t_mid)
        if len(s_vals) > 1:
            lags = t_mid - s_vals
            ax4.plot(lags, K_vals, 'g-', lw=2)
            ax4.set_xlabel('Lag (t - s)')
            ax4.set_ylabel('K*(t, s)')
            ax4.set_title(f'Memory Kernel at t={t_mid:.1f}')
        else:
            ax4.text(0.5, 0.5, 'Kernel too short', ha='center', va='center',
                     transform=ax4.transAxes)
        ax4.grid(True, alpha=0.3)

        self.fig.tight_layout(rect=[0, 0, 1, 0.93])
        self.draw()

    def save_figure(self, path):
        self.fig.savefig(path, dpi=150, bbox_inches='tight')


# ─────────────────────────────────────────────────────────
# CSV interpolation helper
# ─────────────────────────────────────────────────────────

def load_csv_spectral_density(filepath):
    """
    Load a measured spectral density from a CSV file.

    Expected format:
        omega,J
        0.1,0.003
        0.2,0.012
        ...

    First column = frequency (omega), second column = J(omega).
    Returns a callable J(omega) via linear interpolation.
    """
    from scipy.interpolate import interp1d

    data = np.genfromtxt(filepath, delimiter=',', skip_header=1)
    if data.ndim == 1:
        # Try tab or space separation
        data = np.genfromtxt(filepath, skip_header=1)
    if data.ndim == 1 or data.shape[1] < 2:
        raise ValueError(
            "CSV must have 2 columns: omega, J(omega).\n"
            "Accepted separators: comma, tab, space.\n"
            "First row is treated as header and skipped."
        )

    omega = data[:, 0]
    J_vals = data[:, 1]

    J_interp = interp1d(omega, J_vals, kind='linear',
                         fill_value=0.0, bounds_error=False)

    def J(w):
        return float(J_interp(w))

    J.__doc__ = f"CSV: {os.path.basename(filepath)} ({len(omega)} points)"
    return J


# ─────────────────────────────────────────────────────────
# Built-in spectral densities
# ─────────────────────────────────────────────────────────

BUILTIN_SD = {
    "Ohmic (generic bath)":          lambda: SpectralDensities.ohmic(eta=0.1, wc=10.0, s=1),
    "Super-Ohmic (s=3)":             lambda: SpectralDensities.ohmic(eta=0.01, wc=10.0, s=3),
    "Lorentzian (cavity)":           lambda: SpectralDensities.lorentzian(gamma=0.5, wc=5.0, width=0.3),
    "Band Edge (photonic crystal)":  lambda: SpectralDensities.band_edge(beta=0.05, we=5.0),
    "Photonic Crystal (with gap)":   lambda: SpectralDensities.photonic_crystal(beta=0.05, we=5.0, gap_width=2.0),
    "Waveguide QED (mirror)":        lambda: SpectralDensities.waveguide(gamma_1d=0.5, tau_rt=1.0, r=0.9),
}


# ─────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """MaxEnt-Kernel main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MaxEnt-Kernel — Non-Markovian Quantum Solver")
        self.setMinimumSize(1280, 800)

        # Set window & taskbar icon
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'ui', 'assets', 'logo.png')
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.result = None
        self.worker = None
        self.csv_J = None
        self.output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Results')
        self.output_dir = os.path.abspath(self.output_dir)

        self._build_menu()
        self._build_ui()
        self._build_statusbar()

    # ── Menu ──

    def _build_menu(self):
        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("&File")

        import_act = QAction("&Import CSV J(ω)...", self)
        import_act.setShortcut("Ctrl+I")
        import_act.triggered.connect(self._import_csv)
        file_menu.addAction(import_act)

        file_menu.addSeparator()

        save_act = QAction("&Save Plot...", self)
        save_act.setShortcut("Ctrl+S")
        save_act.triggered.connect(self._save_plot)
        file_menu.addAction(save_act)

        export_act = QAction("&Export Data (CSV)...", self)
        export_act.setShortcut("Ctrl+E")
        export_act.triggered.connect(self._export_data)
        file_menu.addAction(export_act)

        file_menu.addSeparator()

        outdir_act = QAction("Set &Output Folder...", self)
        outdir_act.triggered.connect(self._set_output_dir)
        file_menu.addAction(outdir_act)

        file_menu.addSeparator()

        quit_act = QAction("&Quit", self)
        quit_act.setShortcut("Ctrl+Q")
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        # Help
        help_menu = menubar.addMenu("&Help")

        guide_act = QAction("&User Guide", self)
        guide_act.triggered.connect(self._show_guide)
        help_menu.addAction(guide_act)

        about_act = QAction("&About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    # ── UI ──

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ── Left panel ──
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(420)

        # --- Tab widget for data source ---
        self.source_tabs = QTabWidget()

        # Tab 1: Built-in spectral densities
        tab_builtin = QWidget()
        tab_bl = QVBoxLayout(tab_builtin)
        self.sd_combo = QComboBox()
        for name in BUILTIN_SD:
            self.sd_combo.addItem(name)
        tab_bl.addWidget(QLabel("Select a pre-defined spectral density:"))
        tab_bl.addWidget(self.sd_combo)
        tab_bl.addStretch()
        self.source_tabs.addTab(tab_builtin, "Built-in J(ω)")

        # Tab 2: Custom formula
        tab_custom = QWidget()
        tab_cl = QVBoxLayout(tab_custom)
        tab_cl.addWidget(QLabel("Enter your spectral density as a Python expression:"))
        tab_cl.addWidget(QLabel("Variable: w (frequency). Use numpy as np."))
        self.formula_input = QLineEdit()
        self.formula_input.setPlaceholderText("e.g.  0.1 * w**2 * np.exp(-w / 8)")
        self.formula_input.setFont(QFont("Consolas", 11))
        tab_cl.addWidget(self.formula_input)
        tab_cl.addWidget(QLabel(
            "Examples:\n"
            "  0.1 * w * np.exp(-w/10)           — Ohmic\n"
            "  0.5 * 0.3**2 / ((w-5)**2 + 0.3**2) — Lorentzian\n"
            "  0.05**1.5 / np.sqrt(w - 5) if w > 5 else 0  — Band edge"
        ))
        tab_cl.addStretch()
        self.source_tabs.addTab(tab_custom, "Custom Formula")

        # Tab 3: CSV import
        tab_csv = QWidget()
        tab_csvl = QVBoxLayout(tab_csv)
        tab_csvl.addWidget(QLabel("Import measured J(ω) from a CSV file:"))
        tab_csvl.addWidget(QLabel(
            "Format: 2 columns (omega, J), comma/tab/space separated.\n"
            "First row = header (skipped)."
        ))
        csv_row = QHBoxLayout()
        self.csv_path_label = QLabel("No file loaded")
        self.csv_path_label.setStyleSheet("color: #666;")
        csv_btn = QPushButton("Browse...")
        csv_btn.clicked.connect(self._import_csv)
        csv_row.addWidget(self.csv_path_label, stretch=1)
        csv_row.addWidget(csv_btn)
        tab_csvl.addLayout(csv_row)
        self.csv_points_label = QLabel("")
        tab_csvl.addWidget(self.csv_points_label)
        tab_csvl.addStretch()
        self.source_tabs.addTab(tab_csv, "CSV Data")

        left_layout.addWidget(self.source_tabs)

        # --- Physical parameters ---
        param_group = QGroupBox("Physical Parameters")
        param_grid = QGridLayout()

        self.spin_g = self._make_spin(0.001, 10.0, 0.3, 3, "Coupling constant g")
        self.spin_T = self._make_spin(0.0001, 10.0, 0.1, 4, "Effective temperature T (ℏ=k_B=1)")
        self.spin_omega0 = self._make_spin(0.01, 100.0, 5.0, 2, "Emitter transition frequency ω₀")
        self.spin_tmax = self._make_spin(1.0, 500.0, 30.0, 1, "Maximum simulation time")
        self.spin_dt = self._make_spin(0.01, 5.0, 0.2, 2, "Time step (smaller = more accurate but slower)")

        params = [
            ("Coupling g:", self.spin_g),
            ("Temperature T:", self.spin_T),
            ("Frequency ω₀:", self.spin_omega0),
            ("Max time:", self.spin_tmax),
            ("Time step dt:", self.spin_dt),
        ]
        for row, (label, spin) in enumerate(params):
            param_grid.addWidget(QLabel(label), row, 0)
            param_grid.addWidget(spin, row, 1)

        param_group.setLayout(param_grid)
        left_layout.addWidget(param_group)

        # --- Output folder ---
        out_group = QGroupBox("Output Folder")
        out_layout = QHBoxLayout()
        self.outdir_label = QLabel(self._short_path(self.output_dir))
        self.outdir_label.setToolTip(self.output_dir)
        out_btn = QPushButton("Change...")
        out_btn.clicked.connect(self._set_output_dir)
        out_layout.addWidget(self.outdir_label, stretch=1)
        out_layout.addWidget(out_btn)
        out_group.setLayout(out_layout)
        left_layout.addWidget(out_group)

        # --- Auto-save checkbox ---
        self.auto_save_cb = QCheckBox("Auto-save plot + CSV after each run")
        self.auto_save_cb.setChecked(True)
        left_layout.addWidget(self.auto_save_cb)

        # --- Run button ---
        self.run_btn = QPushButton("▶  Run Comparison")
        self.run_btn.setStyleSheet(
            "QPushButton { background-color: #2563eb; color: white; "
            "font-weight: bold; padding: 12px; border-radius: 5px; font-size: 14px; }"
            "QPushButton:hover { background-color: #1d4ed8; }"
            "QPushButton:disabled { background-color: #94a3b8; }"
        )
        self.run_btn.clicked.connect(self._run_simulation)
        left_layout.addWidget(self.run_btn)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        left_layout.addWidget(self.progress)

        # --- Results text ---
        result_group = QGroupBox("Results")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setFont(QFont("Consolas", 10))
        self.result_text.setMaximumHeight(220)
        result_layout.addWidget(self.result_text)
        result_group.setLayout(result_layout)
        left_layout.addWidget(result_group)

        left_layout.addStretch()

        # ── Right panel: plot ──
        self.canvas = PlotCanvas(width=9, height=7)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.canvas)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter)

    def _build_statusbar(self):
        self.statusBar().showMessage(
            f"Hope 'n Mind SASU - Research — MaxEnt-Kernel v1.0.0 — Output: {self.output_dir}"
        )

    def _make_spin(self, vmin, vmax, default, decimals, tooltip):
        spin = QDoubleSpinBox()
        spin.setRange(vmin, vmax)
        spin.setValue(default)
        spin.setDecimals(decimals)
        spin.setSingleStep(10 ** (-decimals))
        spin.setToolTip(tooltip)
        return spin

    def _short_path(self, path):
        """Shorten path for display."""
        if len(path) > 45:
            return "..." + path[-42:]
        return path

    # ── Build spectral density from current tab ──

    def _get_spectral_density(self):
        """
        Return a callable J(omega) based on the active tab.
        Raises ValueError with user-facing message if input is invalid.
        """
        tab_idx = self.source_tabs.currentIndex()

        if tab_idx == 0:
            # Built-in
            name = self.sd_combo.currentText()
            return BUILTIN_SD[name](), name

        elif tab_idx == 1:
            # Custom formula
            formula = self.formula_input.text().strip()
            if not formula:
                raise ValueError("Please enter a formula for J(ω).")

            # Build safe callable
            def J(w):
                try:
                    return float(eval(formula, {"__builtins__": {}},
                                      {"w": w, "np": np, "pi": np.pi,
                                       "exp": np.exp, "sqrt": np.sqrt,
                                       "sin": np.sin, "cos": np.cos,
                                       "log": np.log, "abs": abs}))
                except Exception:
                    return 0.0

            # Test it
            test_val = J(1.0)
            if not np.isfinite(test_val):
                raise ValueError(f"Formula returned non-finite at ω=1: {test_val}")

            return J, f"Custom: {formula[:40]}"

        elif tab_idx == 2:
            # CSV
            if self.csv_J is None:
                raise ValueError(
                    "No CSV file loaded.\n\n"
                    "Click 'Browse...' to load a file with 2 columns:\n"
                    "  omega, J(omega)\n\n"
                    "Example:\n"
                    "  omega,J\n"
                    "  0.1,0.003\n"
                    "  0.2,0.012\n"
                    "  ..."
                )
            return self.csv_J, f"CSV data"

        raise ValueError("Unknown data source tab.")

    # ── Actions ──

    def _run_simulation(self):
        try:
            J, source_name = self._get_spectral_density()
        except ValueError as e:
            QMessageBox.warning(self, "Input Error", str(e))
            return

        g = self.spin_g.value()
        T = self.spin_T.value()
        omega0 = self.spin_omega0.value()
        t_max = self.spin_tmax.value()
        dt = self.spin_dt.value()

        self.run_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.result_text.setPlainText(f"Computing ({source_name})...")
        self.statusBar().showMessage("Simulation running...")
        self._current_source_name = source_name

        self.worker = SimulationWorker(J, g, T, omega0, t_max, dt)
        self.worker.finished.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_result(self, result):
        self.result = result
        self.canvas.plot_result(result)
        self.result_text.setPlainText(result.summary())
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)

        # Auto-save if enabled
        if self.auto_save_cb.isChecked():
            self._auto_save(result)

        self.statusBar().showMessage(
            f"Done — {result.regime} | Max ΔD = {result.max_deviation:.4f} | "
            f"Output: {self.output_dir}"
        )

    def _on_error(self, msg):
        self.run_btn.setEnabled(True)
        self.progress.setVisible(False)
        self.result_text.setPlainText(f"ERROR: {msg}")
        self.statusBar().showMessage("Simulation failed.")

    def _auto_save(self, result):
        """Auto-save plot and CSV to output folder."""
        os.makedirs(self.output_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # Save plot
        plot_path = os.path.join(self.output_dir, f"comparison_{timestamp}.png")
        self.canvas.save_figure(plot_path)

        # Save CSV
        csv_path = os.path.join(self.output_dir, f"data_{timestamp}.csv")
        t = result.t
        nm_pop = result.nm.populations
        m_pop = result.markov.populations
        nm_coh = result.nm.coherences
        m_coh = result.markov.coherences
        td = result.trace_distance
        header = "time,P_e_NM,P_e_Lindblad,coherence_NM,coherence_Lindblad,trace_distance"
        data = np.column_stack([t, nm_pop, m_pop, nm_coh, m_coh, td])
        np.savetxt(csv_path, data, delimiter=',', header=header, comments='')

        # Save summary
        summary_path = os.path.join(self.output_dir, f"summary_{timestamp}.txt")
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(result.summary())
            f.write(f"\n\nSource: {getattr(self, '_current_source_name', 'N/A')}\n")
            f.write(f"Parameters: g={self.spin_g.value()}, T={self.spin_T.value()}, "
                    f"omega0={self.spin_omega0.value()}, t_max={self.spin_tmax.value()}, "
                    f"dt={self.spin_dt.value()}\n")
            f.write(f"\nFiles:\n  Plot: {plot_path}\n  Data: {csv_path}\n")

        self.result_text.append(
            f"\n--- Auto-saved to {self.output_dir} ---\n"
            f"  Plot:    comparison_{timestamp}.png\n"
            f"  Data:    data_{timestamp}.csv\n"
            f"  Summary: summary_{timestamp}.txt"
        )

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Spectral Density CSV", "",
            "CSV files (*.csv *.txt *.dat);;All files (*)"
        )
        if not path:
            return
        try:
            self.csv_J = load_csv_spectral_density(path)
            fname = os.path.basename(path)
            self.csv_path_label.setText(fname)
            self.csv_path_label.setStyleSheet("color: #16a34a; font-weight: bold;")
            # Count points
            data = np.genfromtxt(path, delimiter=',', skip_header=1)
            if data.ndim == 1:
                data = np.genfromtxt(path, skip_header=1)
            n_pts = data.shape[0] if data.ndim > 1 else 1
            self.csv_points_label.setText(f"Loaded: {n_pts} data points")
            self.csv_points_label.setStyleSheet("color: #16a34a;")
            # Switch to CSV tab
            self.source_tabs.setCurrentIndex(2)
            self.statusBar().showMessage(f"CSV loaded: {fname} ({n_pts} points)")
        except Exception as e:
            QMessageBox.warning(self, "CSV Import Error", str(e))

    def _save_plot(self):
        if self.result is None:
            QMessageBox.information(self, "No data", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", os.path.join(self.output_dir, "comparison.png"),
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
        )
        if path:
            self.canvas.save_figure(path)
            self.statusBar().showMessage(f"Plot saved: {path}")

    def _export_data(self):
        if self.result is None:
            QMessageBox.information(self, "No data", "Run a simulation first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Data", os.path.join(self.output_dir, "data.csv"),
            "CSV (*.csv)"
        )
        if path:
            t = self.result.t
            nm_pop = self.result.nm.populations
            m_pop = self.result.markov.populations
            nm_coh = self.result.nm.coherences
            m_coh = self.result.markov.coherences
            td = self.result.trace_distance
            header = "time,P_e_NM,P_e_Lindblad,coherence_NM,coherence_Lindblad,trace_distance"
            data = np.column_stack([t, nm_pop, m_pop, nm_coh, m_coh, td])
            np.savetxt(path, data, delimiter=',', header=header, comments='')
            self.statusBar().showMessage(f"Data exported: {path}")

    def _set_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Output Folder", self.output_dir)
        if d:
            self.output_dir = d
            self.outdir_label.setText(self._short_path(d))
            self.outdir_label.setToolTip(d)
            self.statusBar().showMessage(f"Output folder: {d}")

    def _show_guide(self):
        QMessageBox.information(
            self,
            "User Guide — MaxEnt-Kernel",
            "<h3>How to use MaxEnt-Kernel</h3>"
            "<h4>1. Choose your spectral density</h4>"
            "<p><b>Built-in:</b> Select a preset from the dropdown (Ohmic, Lorentzian, etc.)</p>"
            "<p><b>Custom formula:</b> Type a Python expression using <code>w</code> as the "
            "frequency variable. Example: <code>0.1 * w * np.exp(-w/10)</code></p>"
            "<p><b>CSV data:</b> Import a file with 2 columns: omega and J(omega). "
            "The solver interpolates linearly between your data points.</p>"
            "<h4>2. Set physical parameters</h4>"
            "<p>Adjust coupling g, temperature T, emitter frequency ω₀, "
            "simulation time t_max, and time step dt.</p>"
            "<h4>3. Run the comparison</h4>"
            "<p>Click <b>Run Comparison</b>. The solver computes both non-Markovian "
            "(Boltzmann kernel) and Lindblad (Markovian) dynamics.</p>"
            "<h4>4. Collect results</h4>"
            "<p>If auto-save is enabled, three files are written to the output folder "
            "after each run:</p>"
            "<ul>"
            "<li><b>comparison_TIMESTAMP.png</b> — 4-panel plot</li>"
            "<li><b>data_TIMESTAMP.csv</b> — full time series</li>"
            "<li><b>summary_TIMESTAMP.txt</b> — regime, parameters, metrics</li>"
            "</ul>"
            "<p>You can also manually save plots (Ctrl+S) and export data (Ctrl+E) "
            "to any location.</p>"
            "<h4>5. Interpret</h4>"
            "<p>If <b>max trace distance &lt; 0.01</b>: Lindblad is valid for your system.<br>"
            "If <b>memory parameter P &gt; 1</b>: strongly non-Markovian regime.</p>"
        )

    def _show_about(self):
        QMessageBox.about(
            self,
            "About MaxEnt-Kernel",
            "<h3>MaxEnt-Kernel v1.0.0</h3>"
            "<p>Non-Markovian Quantum Dynamics Solver<br>"
            "with Boltzmann Memory Kernel</p>"
            "<p><b>Authors:</b> DESVAUX G.J.Y. et al.</p>"
            "<p><b>DOI:</b> <a href='https://doi.org/10.5281/zenodo.19486927'>"
            "10.5281/zenodo.19486927</a></p>"
            "<p><b>License:</b> Proprietary — Scientific license on request</p>"
            "<p><b>Contact:</b> contact@hopenmind.com</p>"
            "<hr>"
            "<p>&copy; 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.</p>"
        )


# ─────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MaxEnt-Kernel")
    app.setOrganizationName("Hope 'n Mind SASU - Research")
    app.setStyle("Fusion")

    # App-level icon (taskbar grouping on Windows)
    icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'logo.png')
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, 'ui', 'assets', 'logo.png')
    if os.path.isfile(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
