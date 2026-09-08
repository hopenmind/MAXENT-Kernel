# BoltZ-Kernel - Analytical Companion

**Mathematical derivations and convergence statements for the
backends, decompositions, and order-selection criteria implemented in
BoltZ-Kernel v1.1.0.**

DESVAUX G.J.Y. (2026) · DOI 10.5281/zenodo.19648837 · Apache-2.0

---

## 0. Purpose of this document

This is the *theoretical companion* to the BoltZ-Kernel software. The
software is the empirical evidence that the formalism works
numerically; this document is the formal statement of *why* it works
and *under which conditions*. The two are designed to be read in
parallel: every section here cites the source file and tests where the
claims are exercised.

It is not a peer-reviewed paper. It is a working derivation set,
written so that an external reader can:

1. Verify that each numerical method has a defensible mathematical
   foundation (no algorithmic black-magic).
2. Reproduce the boundary conditions of validity (so a reviewer cannot
   misuse the tool outside its domain).
3. Identify the original contributions distinct from the standard
   literature (one in particular - the **MaxEnt order selector for
   Prony decomposition** - is novel and is the locus of this work's
   originality claim beyond engineering integration).

Intellectual lineage: this work extends the Nakajima-Zwanzig
projection-operator formalism with a Maximum-Entropy variational
selection of the memory kernel
[DESVAUX 2023, *"Extension non-markovienne de la mécanique quantique"*].
The companion software is the operational implementation of that
extension for the open-quantum-systems community.

---

## 1. Notation and physical setting

We consider an open quantum system: a two-level emitter with bare
Hamiltonian H₀ = (ω₀/2)·σ_z coupled to a bosonic bath via

```
H_int = g · (a · σ₊ + a† · σ₋)
```

The bath is fully characterised by its spectral density `J(ω) ≥ 0`,
defined for `ω ≥ 0`. The bath correlation function in the interaction
picture is

```
C(τ) = g² · ∫₀^∞ J(ω) · exp(-i (ω - ω₀) τ) dω        (Eq. 1)
```

The reduced dynamics of the emitter follows the generalised master
equation (Nakajima-Zwanzig)

```
dρ/dt = -i [H₀, ρ] + ∫₀^t K(t, s) · D[ρ(s)] ds      (Eq. 2)
```

where `D[·]` is the amplitude-damping dissipator
`D[ρ] = σ₋ ρ σ₊ - ½{σ₊σ₋, ρ}` and `K(t, s)` is the memory kernel - the
object the framework is built around.

In the MaxEnt-Jaynes selection adopted by BoltZ-Kernel,

```
K*(t, s) = exp(-e(t, s) / T_eff) / Z(t)              (Eq. 3)
e(t, s) = ∫_s^t |C(τ - s)|² dτ                       (Eq. 4)
```

This selection is the unique kernel that maximises the Shannon entropy
of the kernel-as-distribution-over-history under the constraint that it
reproduces the bath energy-correlation profile `e(t, s)`. The
derivation is given in
[DESVAUX 2023] and is not re-derived here.

---

## 2. FFT-based evaluation of `C(τ)`

**Source:** `src/boltz_kernel/core/kernel.py`,
`_compute_bath_correlation_fft`.
**Test:** `tests/test_analytical.py::test_fft_bath_correlation_matches_lorentzian_analytical`.

### 2.1 Statement

For a smooth `J(ω)` with rapidly decaying tails, the bath correlation

```
C(τ) = g² · ∫₀^∞ J(ω) exp(-i(ω-ω₀)τ) dω
```

can be evaluated by uniform sampling on `ω ∈ [0, ω_max]` and a single
FFT, with controlled discretisation error.

### 2.2 Discretisation

Choose `N` uniform samples `ω_k = k · Δω`, `k = 0, …, N-1`,
`Δω = ω_max / N`. The Riemann sum

```
C(τ_m) ≈ g² · Δω · exp(+i ω₀ τ_m) · Σ_k J(ω_k) · exp(-i ω_k τ_m)
```

is *exactly* a discrete Fourier transform if we identify
`τ_m = 2π m / (N · Δω)`. Hence

```
C[τ_m] = g² · Δω · exp(+i ω₀ τ_m) · FFT[J(ω_k)][m]   (Eq. 5)
```

The phase factor `exp(+i ω₀ τ)` accounts for the centring of the
integrand around `ω₀` (interaction-picture frame).

### 2.3 Auto-selection of `ω_max`

`_auto_omega_max(J, ω₀, τ_max)` chooses `ω_max` to satisfy two
constraints:

1. **Spectral support coverage.** Probe `J` on a coarse grid; pick
   `ω_max = 1.2 · sup{ω : J(ω) > 10⁻⁶ · max J}`. This guarantees
   `J(ω_max) ≤ 10⁻⁶ · ‖J‖_∞`, bounding the truncation contribution.
2. **Nyquist condition for τ resolution.**
   `Δτ_FFT = 2π / (N · Δω) ≤ Δτ_user`, equivalently
   `N ≥ ω_max · τ_max / π`. The implementation enforces this by
   bumping `N` to the next power of 2 if needed.

### 2.4 Convergence theorem (Lorentzian case)

For the Lorentzian density
`J(ω) = (γ/2π) · Δ² / ((ω - ωc)² + Δ²)`
with `ωc ≫ Δ` (so the negative-frequency contribution to the
two-sided integral is negligible), the exact correlation is

```
C_exact(τ) = g² · (γ Δ / 2) · exp(-Δ |τ|) · exp(-i (ωc - ω₀) τ)   (Eq. 6)
```

The FFT-discretised value `C_FFT(τ)` satisfies, for `N` large enough
that `J(ω_max) < ε · ‖J‖_∞`:

```
| C_FFT(τ) - C_exact(τ) | ≤ K · (ε + 1/N²) · |C_exact(τ)|       (Eq. 7)
```

with `K` an `O(1)` constant depending on the smoothness of `J`. The
`1/N²` term is the trapezoidal-rule error on a smooth integrand; the
`ε` term is the truncation. Empirically (Lorentzian, default
parameters, `N = 2^14`) the test suite verifies an L^∞ error
≤ 5 % of `‖C‖_∞` over the full τ range, dominated by the cubic
interpolation onto the user grid rather than the FFT itself.

### 2.5 Domain of validity

The FFT path requires `J` to be:

- Non-negative (physical spectral density)
- Sufficiently smooth that uniform sampling at `Δω` resolves all
  features (rule of thumb: `Δω ≤ width_of_narrowest_feature / 8`)
- Decaying on the high-ω end (otherwise `ω_max` cannot be chosen)

It fails (or rings) when `J` has:

- A 1/√(ω-ωe) singularity (band-edge densities)
- A step discontinuity (photonic-crystal hard gap)

These cases are deferred to the NUFFT backend (Phase C).

---

## 3. Matrix-Pencil exponential decomposition of `C(τ)`

**Source:** `src/boltz_kernel/core/prony.py`, `prony_decompose`.
**Tests:** `tests/test_analytical.py::test_prony_backend_*`.

### 3.1 Statement

If `C(τ)` admits a finite-rank exponential representation

```
C(τ) = Σ_{k=1}^K α_k · exp(-β_k τ)        (Re β_k ≥ 0)        (Eq. 8)
```

then the rates `{β_k}` and amplitudes `{α_k}` can be recovered from
uniform samples `C[n] = C(n · Δτ)` by the Matrix-Pencil method
(Hua & Sarkar 1990).

### 3.2 Algorithm

For a uniform grid of `N` samples:

1. Build the Hankel matrix
   `H[i, j] = C[i + j]`, shape `(L+1) × (N - L)`, with `L = ⌊N/2⌋`.
2. SVD: `H = U Σ V^H`. Truncate to rank `K`.
3. Form `U_1 = U_K[:-1, :]` and `U_2 = U_K[1:, :]`.
4. Solve the generalised eigenvalue problem
   `(U_1)^+ U_2 v = z v`, yielding `K` complex *poles* `z_k`.
5. Recover rates: `β_k = -log(z_k) / Δτ`.
6. Recover amplitudes by least squares on the Vandermonde system
   `C[n] = Σ_k α_k · z_k^n`.

### 3.3 The "U vs V" subtlety (debugging note)

The implementation uses **left** singular vectors `U`, not right
singular vectors `V`. The reason - easily missed and a source of a
debugging cycle in the implementation - is that for a Hankel matrix
built from `C[n] = α z^n`, the rank-1 decomposition is

```
H[i, j] = α · z^{i+j} = (z^i) · (α z^j) = a[i] · b[j]
```

The SVD writes `H = σ · u v^H`, with `v_hat[j] ∝ conj(b[j])`
because of the Hermitian transpose. Thus `V[:, 0][j] ∝ conj(z)^j`
and the ratio `V[1]/V[0] = conj(z)`. Using `U` recovers `z`
directly: `U[:, 0][i] ∝ z^i`. This is consistent with the standard
Hua-Sarkar formulation but is a frequent off-by-conjugation error in
ad-hoc implementations.

### 3.4 Stability projection

For physical bath correlations, all `β_k` must satisfy `Re β_k ≥ 0`
(decaying or marginally stable modes - no exponential growth). The
implementation enforces this by projecting any `β_k` with `Re β_k < 0`
onto the imaginary axis (`Re β_k → 0`) before solving for `α_k`. This
is a documented "physically-stable mode" option and can be disabled
for diagnostic use.

### 3.5 Equivalence to ESPRIT in the noise-free limit

Matrix Pencil and ESPRIT (Estimation of Signal Parameters via
Rotational Invariance Techniques, Roy & Kailath 1989) are
mathematically equivalent for noise-free, exact-rank-K signals: both
extract `{z_k}` from the rotational invariance between consecutive
columns of the truncated singular subspace. They can differ in
numerical conditioning under heavy noise (ESPRIT uses a TLS step;
Matrix Pencil uses a pseudo-inverse). For BoltZ-Kernel's intended
regime (FFT-derived `C(τ)` with controllable noise floor), Matrix
Pencil is sufficient and slightly simpler.

---

## 4. MaxEnt order selection (novel contribution)

**Source:** `src/boltz_kernel/core/prony.py`, `maxent_select_order`.
**CLI:** `boltz-kernel run ... --backend prony --prony-maxent`.

### 4.1 The problem

Given the singular values `σ_1 ≥ σ_2 ≥ … ≥ σ_M ≥ 0` of the Hankel
pencil, choose the truncation order `K`. The standard choices are:

- **Hard threshold:** keep `σ_k` such that `σ_k > tolerance`.
  Sensitive to the tolerance choice; brittle.
- **Variance ratio (PCA-style):** smallest `K` such that
  `Σ_{i ≤ K} σ_i² ≥ θ · Σ_i σ_i²` for `θ` close to 1
  (e.g. 0.999). Implemented as the default in `_auto_select_order`.
- **AIC / BIC:** information criterion penalising model complexity
  (Akaike 1974; Schwarz 1978). Standard but requires a noise model.

### 4.2 The MaxEnt criterion

We propose the following alternative, consistent with the Maximum
Entropy principle that already underpins the BoltZ-Kernel formalism.

Define the **normalised mode-weight distribution**

```
p_i = σ_i² / Σ_j σ_j²                    (Eq. 9)
```

and its **Shannon entropy**

```
H = - Σ_i p_i · log p_i                  (Eq. 10)
```

The **effective number of modes** (perplexity / ENC) is `N_eff = exp H`:
a rank-1 signal has `N_eff = 1`; a perfectly flat K-mode signal has
`N_eff = K`.

For the truncated subset of the top `K` modes, define the truncated
distribution `p^{(K)}_i = σ_i² / Σ_{j ≤ K} σ_j²` and its entropy
`H_K = -Σ_{i ≤ K} p^{(K)}_i log p^{(K)}_i`.

**Selection criterion:** smallest `K` such that

```
H_K ≥ θ_H · H_full           (Eq. 11)
```

with `θ_H ∈ (0, 1]` a user threshold (default 0.95).

### 4.3 Why this is a "MaxEnt" criterion

Among all rank-`K` truncations of the signal that respect the data,
the one whose retained-mode distribution carries maximum Shannon
entropy is the **least biased** in the Jaynes sense: it minimises the
information-theoretic commitment beyond what the data has revealed.
The criterion (Eq. 11) selects the smallest `K` for which the
truncation already preserves a fraction `θ_H` of the full-spectrum
entropy - i.e. *the smallest model that does not artificially
concentrate the explanatory weight on a few dominant modes*.

### 4.4 Comparison with variance-ratio

Variance-ratio (Eq.: `Σ_{i≤K} σ_i² ≥ θ · total`) is biased toward
keeping the dominant modes. A signal with a single strong mode plus
many small modes carrying *real* but spread structure will yield
`K = 1` under variance-ratio (one mode already covers 99.9 % of the
energy) - *but the entropy criterion will detect that the residual
has structure and select a larger `K`*. Conversely, if the residual is
genuine white noise, both criteria converge to the same `K`.

The empirical regime where the two diverge is precisely where
exponential-decomposition methods are most brittle: noise spread
across many small modes that conventional thresholding either
ignores (false negatives in the residual) or over-fits (chasing
noise eigenvalues). The MaxEnt criterion provides a principled,
parameter-light middle ground.

### 4.5 Status in the literature

The MaxEnt order selector for Prony / Matrix-Pencil decompositions, in
the form (Eqs. 9-11), is **not present in the standard signal-
processing literature** to the author's knowledge. Related but
distinct ideas exist:

- Maximum-Entropy spectral estimation (Burg 1975) - uses entropy in a
  different role (spectrum reconstruction, not order selection).
- Information-criterion order selection (AIC, BIC, MDL) - uses
  likelihood and complexity penalties, not the entropy of the singular
  spectrum directly.
- Hyvärinen's negentropy in ICA - entropy-based but targeting
  non-Gaussianity, not model order.

This contribution is therefore claimed as novel by BoltZ-Kernel. The
reference implementation is `prony.maxent_select_order` and the
exposed CLI / API option is `--prony-maxent`.

---

## 5. Pseudomode TCL2 reduction

**Source:** `src/boltz_kernel/core/pseudomode.py`, `solve_pseudomode`.
**Test:** `tests/test_analytical.py::test_prony_backend_solve_dispatches_to_pseudomode`.

### 5.1 The reduction

Given the Prony decomposition (Eq. 8), define `K` *auxiliary
variables*

```
A_k(t) = ∫₀^t α_k · exp(-β_k (t - s)) · 1 ds = α_k · (1 - exp(-β_k t)) / β_k   (Eq. 12)
```

By construction these satisfy the local-in-time ODE

```
dA_k/dt = -β_k · A_k(t) + α_k     (Eq. 13)
A_k(0) = 0
```

The integrated bath rate at time `t` is then

```
γ(t) = ∫₀^t C(τ) dτ = Σ_k A_k(t)         (Eq. 14)
```

In the second-order time-convolutionless (TCL2) approximation, valid
in the weak-coupling regime, the master equation (Eq. 2) becomes:

```
dρ_ee/dt = -2 Re γ(t) · ρ_ee
dρ_01/dt = -i ω₀ ρ_01 - Re γ(t) · ρ_01
```

In Bloch coordinates (z = ⟨σ_z⟩, x + iy = 2 ⟨σ₋⟩):

```
dx/dt = + ω₀ y - Re γ(t) · x
dy/dt = - ω₀ x - Re γ(t) · y
dz/dt = -2 Re γ(t) · (z + 1)             (Eq. 15)
```

Equations (13) and (15) form a closed system of `3 + 2K` real ODEs
(complex `A_k` split into real/imaginary parts). They are solved by
standard adaptive Runge-Kutta (`scipy.integrate.solve_ivp`).

### 5.2 Computational complexity

- **Original integro-differential equation (Eq. 2):** `O(N²)` - each
  step `t_i` integrates over the full history `[0, t_i]`.
- **Pseudomode reduction (Eqs. 13 + 15):** `O(N · K)` - each step
  updates `K` auxiliary variables locally.

For typical `K ∈ [1, 16]` (Lorentzian, sum of Lorentzians) and
`N ∈ [10², 10⁴]`, the speed-up is **14×-450×** as measured in the
Phase B benchmark.

### 5.3 Domain of validity

TCL2 is **second-order in the coupling**. It is valid for `g·τ_c ≪ 1`
where `τ_c = 1/min Re β_k` is the longest bath-correlation time. In
the strong-coupling regime, fourth-order TCL or HEOM (Tanimura) is
required.

The MaxEnt-kernel direct integro-differential solver (`backend="fft"`
or `"quad"`) is *not* a TCL2 approximation but a different
non-perturbative ansatz; the two methods agree in the weak-coupling
limit and diverge by ~5 % in the moderate-coupling cases tested
(observed in `test_prony_backend_solve_dispatches_to_pseudomode`).
This is *not* a bug; it is the documented divergence between the
MaxEnt-Jaynes kernel selection and TCL2.

### 5.4 Why pseudomode `≠` HEOM

The pseudomode reduction (Eqs. 13, 15) is the *weak-coupling /
single-excitation* version. The full Hierarchical Equations of Motion
(HEOM, Tanimura 2020) extends to arbitrary coupling and Matsubara
frequencies for thermal baths, at the cost of a deeper hierarchy of
auxiliary tensors. BoltZ-Kernel does not currently implement HEOM - 
it implements the pseudomode bridge that *would extend to HEOM* by
adding hierarchy levels, which is reserved for a future major version.

---

## 6. Backend equivalences and disagreement zones

| Pair                  | Agreement regime                          | Divergence regime                        | Documented gap |
|-----------------------|-------------------------------------------|------------------------------------------|----------------|
| `quad` ↔ `fft`        | Smooth `J`, short τ                       | Large τ (quad fails to converge)         | Tested ≤ 5 % at short τ |
| `fft` ↔ `prony`       | `J` admits low-K exponential rep          | High-K or non-decaying baths             | Tested at single-Lorentzian |
| MaxEnt-K ↔ Prony      | Same physics object (`C(τ)`)              | MaxEnt-K is the integro-diff K*; Prony decomposes C - different uses | ≈ 5 % observable on `P_e` |
| MaxEnt-kernel ↔ TCL2  | Both weak-coupling                        | At moderate coupling, ~5 % gap on `P_e`  | Documented & tested |
| Pseudomode ↔ TCL2-analytical | Per construction                   | None                                     | Tested to 6 decimals |

The point of having multiple backends in BoltZ-Kernel is **not
redundancy** - it is *cross-validation*. Two backends agreeing on a
given `J(ω)` strongly constrains the result against numerical
artefact; two backends disagreeing flags a regime where physical
assumptions (weak coupling, smoothness, bath structure) are being
strained.

---

## 7. Empirical validation cross-reference

| Test name                                                  | What it proves                                                    |
|------------------------------------------------------------|-------------------------------------------------------------------|
| `test_lindblad_exponential_decay`                          | Markov solver matches `exp(-γt)` exactly                          |
| `test_markov_limit_small_correlation_time`                 | NM solver collapses to Lindblad as τ_c → 0                        |
| `test_bloch_vector_bounded`                                | CPTP invariant `‖(x,y,z)‖ ≤ 1` preserved                          |
| `test_population_physical_range`                           | `P_e ∈ [0, 1]`                                                    |
| `test_regime_label_matches_P` (parametrised x4)            | Regime classifier consistent with computed `P`                    |
| `test_fft_bath_correlation_matches_lorentzian_analytical`  | FFT path verified vs Eq. 6 to ≤ 5 % rel                           |
| `test_backends_agree_in_convergent_regime`                 | `quad` and `fft` agree where `quad` converges (≤ 5 %)             |
| `test_unknown_backend_raises`                              | Input validation                                                  |
| `test_nufft_backend_not_yet_implemented`                   | Phase-C placeholder behaves as documented                         |
| `test_prony_backend_builds_decomposition`                  | `backend="prony"` attaches a valid PronyResult                    |
| `test_prony_backend_solve_dispatches_to_pseudomode`        | `.solve()` uses pseudomode path; physics preserved                |

Plus 8 MCP integration tests (`tests/test_mcp.py`) verifying the
agent-callable surface produces identical artefacts to the CLI and
Python API paths.

**Total: 26 tests passing as of v1.1.0.**

---

## 8. Open questions and future work

### 8.1 NUFFT backend (Phase C, planned)

The current FFT path requires uniform sampling and a smooth integrand.
For physically interesting densities with sharp features - 
band-edge `J(ω) ∝ 1/√(ω - ω_e)` for ω > ω_e (photonic crystal),
photonic-crystal hard gap at `[ω_e, ω_e + δ]` - the uniform FFT
either rings or undersamples the singularity.

The **non-uniform FFT** (NUFFT, Greengard & Lee 2004) handles this
by allowing `ω` samples concentrated near singularities. The intended
implementation in `_compute_bath_correlation_nufft` would:

1. Detect the singularity location from `J`'s symbolic form or
   numerical gradient.
2. Distribute `ω` samples with adaptive density (logarithmic near
   singularities, linear far away).
3. Apply the FINUFFT type-1 transform to obtain `C(τ)`.

Estimated effort: 2-3 hours including the test for the analytical
band-edge correlation.

### 8.2 Strong-coupling extension via HEOM-pseudomode

For `g · τ_c ≳ 1`, TCL2 underestimates non-Markovian effects (revival
amplitudes, coherence preservation). A natural extension is to
*hierarchicalise* the pseudomode equations à la Tanimura - adding a
second-tier auxiliary `A_k^{(2)}(t)` that captures the response of
the bath to its own response to the system. This raises the
complexity from `O(N · K)` to `O(N · K^L)` for hierarchy depth `L`,
typically `L ∈ {2, 3}`.

### 8.3 Multi-level systems (qudits)

The current `MemoryKernel.solve` and `solve_pseudomode` are written
for a two-level emitter (Bloch sphere). Extension to a `d`-level
qudit requires:

1. Replacing the Bloch-vector parametrisation with the full `d² - 1`
   generalised Bloch coordinates (or directly the density matrix).
2. Generalising the dissipator to a multi-mode Lindblad form with
   bath-mediated transitions among levels.

The pseudomode auxiliary structure (Eq. 13) is dimension-independent
 - it generalises trivially. The bath-system coupling and dissipator
contain the qudit-specific structure.

### 8.4 Critical assessment of Eq. 11 (MaxEnt criterion)

The threshold `θ_H = 0.95` is a default chosen to match the
conventional "95 % of the information" heuristic used in PCA and
related methods. A principled determination (e.g. via cross-validation
on synthetic baths, or by anchoring `θ_H` to a target reconstruction
RMS) is left as future work. The current default is empirically
robust on the test set but is not theoretically privileged.

---

## 9. Reproduction summary

To independently verify all claims in this document:

```bash
git clone https://github.com/hopenmind/MaxEnt-Kernel
cd MaxEnt-Kernel
pip install -e ".[test]"
pytest -v                # 26 tests, all passing
python _bench_phaseA.py  # FFT vs quad speed-up
python _bench_phaseB.py  # Prony pseudomode .solve() speed-up
```

All test files reference equation numbers from this document in their
docstrings.

---

## 10. References

1. **Nakajima, S.** (1958). *On Quantum Theory of Transport Phenomena.*
   Prog. Theor. Phys. 20:948.
2. **Zwanzig, R.** (1960). *Ensemble Method in the Theory of
   Irreversibility.* J. Chem. Phys. 33:1338.
3. **Jaynes, E. T.** (1957). *Information Theory and Statistical
   Mechanics.* Phys. Rev. 106:620.
4. **Hua, Y. & Sarkar, T. K.** (1990). *Matrix pencil method for
   estimating parameters of exponentially damped/undamped sinusoids
   in noise.* IEEE Trans. ASSP 38:814.
5. **Roy, R. & Kailath, T.** (1989). *ESPRIT - Estimation of signal
   parameters via rotational invariance techniques.* IEEE Trans. ASSP
   37:984.
6. **Garraway, B. M.** (1997). *Nonperturbative decay of an atomic
   system in a cavity.* Phys. Rev. A 55:2290.
7. **Tamascelli, D.** et al. (2018). *Nonperturbative treatment of
   non-Markovian dynamics of open quantum systems.* Phys. Rev. Lett.
   120:030402.
8. **Tanimura, Y.** (2020). *Numerically "exact" approach to open
   quantum dynamics: The hierarchical equations of motion (HEOM).*
   J. Chem. Phys. 153:020901.
9. **Greengard, L. & Lee, J.-Y.** (2004). *Accelerating the nonuniform
   fast Fourier transform.* SIAM Rev. 46:443.
10. **Akaike, H.** (1974). *A new look at the statistical model
    identification.* IEEE Trans. AC 19:716.
11. **Schwarz, G.** (1978). *Estimating the dimension of a model.*
    Ann. Statist. 6:461.
12. **Burg, J. P.** (1975). *Maximum Entropy Spectral Analysis.*
    PhD thesis, Stanford.
13. **DESVAUX, G. J. Y.** (2023). *Extension non-markovienne de la
    mécanique quantique.* Hope 'n Mind SASU - Research.
    DOI: 10.5281/zenodo.19517607.
14. **DESVAUX, G. J. Y.** (2026). *BoltZ-Kernel: Non-Markovian Quantum
    Dynamics Solver with Boltzmann Memory Kernel* (this software).
    DOI: 10.5281/zenodo.19648837.

---

*Document version 1.0 - 2026-04-19. Companion to BoltZ-Kernel v1.1.0.
Open to revision with each minor release of the software.*
