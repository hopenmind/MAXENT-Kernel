"""
MaxEnt-Kernel — Non-Markovian quantum dynamics solver
=====================================================

Computes Boltzmann memory kernels from spectral densities
and solves the generalized master equation beyond Lindblad.

Theory (3 equations):

  1. Generalized master equation:
     dρ/dt = -i[H,ρ] + ∫₀ᵗ K(t,s) D[ρ(s)] ds

  2. Boltzmann kernel (MaxEnt derivation):
     K*(t,s) = (1/Z) exp(-e(t,s)/T)
     where e(t,s) = ∫ₛᵗ |C(τ-s)|² dτ

  3. Bath correlation from spectral density:
     C(τ) = g² ∫₀∞ J(ω) exp(-i(ω-ω₀)τ) dω

Usage:
    from Program.core import MemoryKernel, compare

    J = lambda w: 0.1 * w**3 * np.exp(-w/10)
    K = MemoryKernel.from_spectral_density(J, g=0.1, T=0.05)
    result = K.solve(rho0, tspan)

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19486927
ORCID: 0009-0008-9813-4627
License: Proprietary — Scientific license available on request with citation.
Contact: contact@hopenmind.com
"""

# NumPy 2.0 removed np.trapz — patch it back for scipy and internal use
import numpy as np
if not hasattr(np, 'trapz'):
    np.trapz = np.trapezoid

from .kernel import MemoryKernel, Result
from .lindblad import LindbladSolver
from .compare import compare, ComparisonResult, SpectralDensities

__version__ = "1.0.0"
__author__ = "DESVAUX G.J.Y. et al."
__copyright__ = "Copyright (c) 2026 Hope 'n Mind SASU - Research"
__license__ = "Proprietary — Scientific license on request with citation"
__doi__ = "10.5281/zenodo.19486927"
__contact__ = "contact@hopenmind.com"

__all__ = [
    "MemoryKernel", "Result",
    "LindbladSolver",
    "compare", "ComparisonResult", "SpectralDensities",
]
