# `e` as natural scale step and boundary rule (working hypothesis)

## Status

Research card.
Does not change L0 canon and does not introduce physical constants into DETM core.

Note: first-pass translation of `docs/rus/40_hypotheses/e_scale_boundary_invariants.md`.

---

## 1. Context and terms

Here `e` means the mathematical constant (`e ~= 2.71828`), not elementary charge.

Working intuition:
- `e` may be a natural coarsening step;
- passing one unit boundary may follow exponential attenuation;
- logarithmic scale can linearize transitions between levels.

---

## 2. Scale hypothesis (`e`-step)

If levels obey:

```text
L_(n+1) = e * L_n
```

then level index is:

```text
n = ln(L / L0)
```

Consequences:
- one level step is `+1` in `ln L`;
- coarsening is uniform in log-scale;
- evolution equations are natural in `dX / d(ln L)` rather than `dX / dL`.

Equivalent inward step:

```text
L_(n+1) = L_n / e  =>  ln L_(n+1) = ln L_n - 1
```

---

## 3. Boundary hypothesis (exponential passage)

For energy flow through a boundary:

```text
dE/dx = -kE  =>  E(x) = E0 * exp(-k*x)
```

If `k = 1` and unit boundary thickness `x = 1`:

```text
E_out = E_in / e
```

DETM interpretation:
- boundary is a finite attenuation/transform layer;
- transitions between adjacent layers can be parameterized exponentially.

---

## 4. Link to invariants

If component `X` scales as `X ~ L^a`, then under `L_(n+1)=e*L_n`:

```text
X_(n+1) = exp(a) * X_n
```

For inward step (`L_(n+1)=L_n/e`):

```text
X_(n+1) = exp(-a) * X_n
```

In log variables:

```text
ln X_(n+1) = ln X_n + a
```

Practical meaning:
- non-invariant components drift systematically along `n`;
- stable invariants have low drift in log-scale;
- `e`-coarsening can be used as stability filter operator.

---

## 5. Why this suggests near-`O(1)` representation

Dimensionless variables (`n = ln(L/L0)` and normalized time/energy) can:
- reduce dependence on absolute scale;
- describe inter-level transitions with constant multipliers;
- move dynamics toward constant-complexity-per-level-step behavior within validity bounds.

Important: this is not a universal guarantee. Phase transitions and non-self-similar regimes may break this normalization.

---

## 6. How to test

1. Compare two coarsening scales: arbitrary factor `k` and `k = e`.
2. Compare invariant stability at equal log-step horizon.
3. Measure log-space drift of:
- spectral peaks;
- boundary flows;
- share of refinement events.
4. Check whether inter-level operator coefficient spread shrinks (indicator of near-`O(1)` description).

Falsification criterion:
- `k=e` provides no stability/transferability gain over nearby `k`,
- or log-scaling does not reduce inter-level drift.

---

## 7. Limits and compatibility with canon

- This is a scaling hypothesis, not a claim about physical constants.
- Canonical invariant `E in [0,1]` remains unchanged.
- Any implementation must stay within existing level/refinement/coarsening contracts.

Related docs:
- `docs/eng/20_mechanisms/coarsening.md`
- `docs/eng/20_mechanisms/scale_axis.md`
- `docs/eng/20_mechanisms/invariants.md`
- `docs/eng/20_mechanisms/boundary_throughput_and_period_scaling.md`
- `docs/rus/90_notes/globaltime_o1_dt.md`

