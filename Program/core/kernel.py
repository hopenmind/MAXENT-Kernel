"""
Memory kernel computation from spectral densities.

Core class: MemoryKernel
  - from_spectral_density(J, g, T, omega0) → MemoryKernel
  - from_bath_correlation(C, T) → MemoryKernel
  - evaluate(t, s) → float
  - solve(rho0, tspan) → Result

Copyright (c) 2008-2026 Hope 'n Mind SASU - Research — All rights reserved.
Authors: DESVAUX G.J.Y. 
DOI: 10.5281/zenodo.19486927 | ORCID: 0009-0008-9813-4627
License: Proprietary — Scientific license on request with citation.
Contact: contact@hopenmind.com
"""

import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.interpolate import interp1d


class MemoryKernel:
    """
    Non-Markovian memory kernel K*(t,s) derived from MaxEnt variational principle.

    K*(t,s) = (1/Z(t)) exp(-e(t,s) / T_eff)

    where e(t,s) = ∫_s^t |C(τ-s)|² dτ  (accumulated correlation energy)
    and   C(τ)  = ∫ J(ω) exp(-i(ω-ω₀)τ) dω  (bath correlation function)
    """

    def __init__(self, e_func, T_eff, t_max=100.0, dt=0.1, omega0=1.0, g=1.0,
                 gamma_markov=None, C_func=None, J_func=None):
        """
        Parameters
        ----------
        e_func : callable(t, s) → float
            Accumulated energy density.
        T_eff : float
            Effective temperature of the environment.
        t_max : float
            Maximum simulation time.
        dt : float
            Time step for discretization.
        omega0 : float
            Emitter transition frequency.
        g : float
            Coupling constant.
        gamma_markov : float or None
            Markovian decay rate (Fermi golden rule). Computed if None.
        C_func : callable or None
            Bath correlation function C(τ).
        J_func : callable or None
            Spectral density J(ω).
        """
        self.e_func = e_func
        self.T_eff = T_eff
        self.t_max = t_max
        self.dt = dt
        self.omega0 = omega0
        self.g = g
        self.C_func = C_func
        self.J_func = J_func

        # Precompute time grid
        self.times = np.arange(0, t_max + dt, dt)
        self.n_times = len(self.times)

        # Precompute kernel on grid
        self._K_grid = np.zeros((self.n_times, self.n_times))
        self._Z = np.zeros(self.n_times)
        self._precompute_kernel()

        # Markovian rate
        if gamma_markov is not None:
            self.gamma_markov = gamma_markov
        else:
            self.gamma_markov = self._compute_markov_rate()

    def _precompute_kernel(self):
        """Precompute K*(t_i, t_j) on the time grid."""
        for i in range(1, self.n_times):
            t = self.times[i]
            unnorm = np.zeros(i)
            for j in range(i):
                s = self.times[j]
                e_val = self.e_func(t, s)
                unnorm[j] = np.exp(-e_val / max(self.T_eff, 1e-30))

            Z = np.trapz(unnorm, self.times[:i]) if i > 1 else unnorm[0] * self.dt
            self._Z[i] = max(Z, 1e-30)

            for j in range(i):
                self._K_grid[i, j] = unnorm[j] / self._Z[i]

    def _compute_markov_rate(self):
        """Compute Fermi golden rule rate: γ = 2π g² J(ω₀)."""
        if self.J_func is not None:
            return 2 * np.pi * self.g**2 * self.J_func(self.omega0)
        return 0.1  # fallback

    def evaluate(self, t, s):
        """Evaluate K*(t, s) at arbitrary times."""
        if s >= t or s < 0:
            return 0.0
        e_val = self.e_func(t, s)
        Z, _ = quad(lambda sp: np.exp(-self.e_func(t, sp) / max(self.T_eff, 1e-30)),
                     0, t, limit=100)
        if Z < 1e-30:
            return 0.0
        return np.exp(-e_val / max(self.T_eff, 1e-30)) / Z

    def solve(self, rho0, tspan=None, method="RK45", rtol=1e-6):
        """
        Solve the non-Markovian master equation.

        dρ/dt = -i[H, ρ(t)] + ∫₀ᵗ K(t,s) D[ρ(s)] ds

        For a two-level system, we track the Bloch vector (x, y, z)
        where ρ = (I + x σ_x + y σ_y + z σ_z) / 2.

        Parameters
        ----------
        rho0 : array (2,2) or (3,) Bloch vector
            Initial state. If (2,2), converted to Bloch vector.
        tspan : array or None
            Time points. If None, uses self.times.

        Returns
        -------
        Result with .t, .rho (Bloch vectors), .populations, .coherences
        """
        if tspan is None:
            tspan = self.times

        # Convert rho0 to Bloch vector
        if hasattr(rho0, 'shape') and rho0.shape == (2, 2):
            x0 = 2 * np.real(rho0[0, 1])
            y0 = 2 * np.imag(rho0[1, 0])
            z0 = np.real(rho0[0, 0] - rho0[1, 1])
            bloch0 = np.array([x0, y0, z0])
        else:
            bloch0 = np.asarray(rho0, dtype=float)

        # Solve via discretized integro-differential equation
        n = len(tspan)
        dt = tspan[1] - tspan[0] if n > 1 else self.dt
        bloch = np.zeros((n, 3))
        bloch[0] = bloch0

        for i in range(1, n):
            t = tspan[i]

            integral_x = 0.0
            integral_y = 0.0
            integral_z_decay = 0.0
            integral_z_pump = 0.0

            for j in range(i):
                s = tspan[j]
                ti_idx = min(int(t / self.dt), self.n_times - 1)
                sj_idx = min(int(s / self.dt), self.n_times - 1)
                if ti_idx < self.n_times and sj_idx < ti_idx:
                    K_val = self._K_grid[ti_idx, sj_idx]
                else:
                    K_val = self.evaluate(t, s)

                integral_x += K_val * bloch[j, 0] * dt
                integral_y += K_val * bloch[j, 1] * dt
                integral_z_decay += K_val * bloch[j, 2] * dt
                integral_z_pump += K_val * dt

            gamma = self.gamma_markov
            bloch[i, 0] = bloch[i-1, 0] - 0.5 * gamma * integral_x * dt
            bloch[i, 1] = bloch[i-1, 1] - 0.5 * gamma * integral_y * dt
            bloch[i, 2] = bloch[i-1, 2] - gamma * (integral_z_decay + integral_z_pump) * dt

            # Clamp to Bloch sphere
            norm = np.sqrt(bloch[i, 0]**2 + bloch[i, 1]**2 + bloch[i, 2]**2)
            if norm > 1.0:
                bloch[i] /= norm

        return Result(tspan, bloch, self)

    @classmethod
    def from_spectral_density(cls, J, g=1.0, T=0.05, omega0=1.0, t_max=100.0, dt=0.1):
        """
        Construct a MemoryKernel from a spectral density J(ω).

        Parameters
        ----------
        J : callable(omega) → float
            Spectral density of the photonic environment.
        g : float
            System-environment coupling constant.
        T : float
            Effective temperature (energy units, ℏ=k_B=1).
        omega0 : float
            Emitter transition frequency.
        t_max : float
            Maximum simulation time.
        dt : float
            Time step.

        Returns
        -------
        MemoryKernel instance.
        """
        tau_grid = np.arange(0, t_max + dt, dt)
        C_real = np.zeros(len(tau_grid))
        C_imag = np.zeros(len(tau_grid))

        # Find J support
        w_test = np.linspace(0, 10 * omega0, 1000)
        J_test = np.array([J(w) for w in w_test])
        mask = J_test > 1e-10 * np.max(J_test) if np.max(J_test) > 0 else np.zeros_like(J_test, dtype=bool)
        w_max = w_test[mask][-1] if np.any(mask) else 10 * omega0
        w_min = max(0, w_test[mask][0]) if np.any(mask) else 0

        for idx, tau in enumerate(tau_grid):
            re_part, _ = quad(lambda w: g**2 * J(w) * np.cos((w - omega0) * tau),
                              w_min, w_max, limit=200)
            im_part, _ = quad(lambda w: -g**2 * J(w) * np.sin((w - omega0) * tau),
                              w_min, w_max, limit=200)
            C_real[idx] = re_part
            C_imag[idx] = im_part

        C_abs2 = C_real**2 + C_imag**2

        C_abs2_interp = interp1d(tau_grid, C_abs2, fill_value=0.0, bounds_error=False)

        E_cumul = np.zeros(len(tau_grid))
        for idx in range(1, len(tau_grid)):
            E_cumul[idx] = E_cumul[idx-1] + C_abs2[idx-1] * dt
        E_interp = interp1d(tau_grid, E_cumul, fill_value=(0, E_cumul[-1]), bounds_error=False)

        def e_func(t, s):
            lag = t - s
            if lag <= 0:
                return 0.0
            return float(E_interp(min(lag, t_max)))

        C_r_interp = interp1d(tau_grid, C_real, fill_value=0.0, bounds_error=False)
        C_i_interp = interp1d(tau_grid, C_imag, fill_value=0.0, bounds_error=False)
        def C_func(tau):
            return complex(C_r_interp(tau), C_i_interp(tau))

        return cls(e_func=e_func, T_eff=T, t_max=t_max, dt=dt,
                   omega0=omega0, g=g, C_func=C_func, J_func=J)

    @classmethod
    def from_bath_correlation(cls, C, T=0.05, t_max=100.0, dt=0.1, omega0=1.0, g=1.0):
        """
        Construct a MemoryKernel from a bath correlation function C(τ).
        """
        tau_grid = np.arange(0, t_max + dt, dt)
        C_abs2 = np.array([abs(C(tau))**2 for tau in tau_grid])

        E_cumul = np.zeros(len(tau_grid))
        for idx in range(1, len(tau_grid)):
            E_cumul[idx] = E_cumul[idx-1] + C_abs2[idx-1] * dt
        E_interp = interp1d(tau_grid, E_cumul, fill_value=(0, E_cumul[-1]), bounds_error=False)

        def e_func(t, s):
            lag = t - s
            if lag <= 0:
                return 0.0
            return float(E_interp(min(lag, t_max)))

        return cls(e_func=e_func, T_eff=T, t_max=t_max, dt=dt,
                   omega0=omega0, g=g, C_func=C)

    def non_markovianity(self):
        """
        Compute the non-Markovianity parameter P = g × τ_c
        where τ_c = ∫ τ K*(τ) dτ is the memory correlation time.
        """
        t_idx = self.n_times // 2
        if t_idx < 2:
            return 0.0

        K_slice = self._K_grid[t_idx, :t_idx]
        t_slice = self.times[:t_idx]

        if len(K_slice) < 2 or np.sum(K_slice) < 1e-30:
            return 0.0

        lags = self.times[t_idx] - t_slice
        tau_c = np.trapz(lags * K_slice, t_slice) / max(np.trapz(K_slice, t_slice), 1e-30)

        return self.g * tau_c

    def memory_spread(self):
        """Compute σ_K — the std dev of the kernel as a distribution over lag times."""
        t_idx = self.n_times // 2
        if t_idx < 2:
            return 0.0

        K_slice = self._K_grid[t_idx, :t_idx]
        t_slice = self.times[:t_idx]
        lags = self.times[t_idx] - t_slice
        norm = np.trapz(K_slice, t_slice)
        if norm < 1e-30:
            return 0.0

        mean_lag = np.trapz(lags * K_slice, t_slice) / norm
        var_lag = np.trapz((lags - mean_lag)**2 * K_slice, t_slice) / norm
        return np.sqrt(max(var_lag, 0))

    def kernel_at(self, t):
        """Return K*(t, s) as arrays (s_values, K_values) for plotting."""
        t_idx = min(int(t / self.dt), self.n_times - 1)
        if t_idx < 1:
            return np.array([0]), np.array([0])
        s_vals = self.times[:t_idx]
        K_vals = self._K_grid[t_idx, :t_idx]
        return s_vals, K_vals


class Result:
    """Container for solver output."""

    def __init__(self, t, bloch, kernel):
        self.t = np.asarray(t)
        self.bloch = np.asarray(bloch)
        self.kernel = kernel

    @property
    def x(self):
        return self.bloch[:, 0]

    @property
    def y(self):
        return self.bloch[:, 1]

    @property
    def z(self):
        return self.bloch[:, 2]

    @property
    def populations(self):
        """Excited state population P_e = (1+z)/2."""
        return (1 + self.z) / 2

    @property
    def coherences(self):
        """Off-diagonal |ρ₀₁| = sqrt(x² + y²)/2."""
        return np.sqrt(self.x**2 + self.y**2) / 2

    def trace_distance_from(self, other):
        """Trace distance D(ρ_self, ρ_other) at each time step."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return 0.5 * np.sqrt(dx**2 + dy**2 + dz**2)
