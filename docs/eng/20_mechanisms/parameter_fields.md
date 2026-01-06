# Environment parameters as fields

Note: first-pass translation of `docs/rus/20_mechanisms/parameter_fields.md`.

In DETM, dynamics parameters (e.g. `kappa/alpha/beta/gamma/lambda_t`) are treated as **environment parameters**, not fixed “universal constants”.

They can be:
- global constants for a run;
- **spatio-temporal fields** (different values in different regions and/or over time).

This enables regime control **without injecting energy**:
- a “channel” = a region with lower latency/suppression and/or higher conductivity;
- “embedding” a neuron/object (future) = locally substituting an environment parameter set in a small patch;
- parameter gradients = a weak condition field that invariants respond to.

Related docs:
- channels: `docs/eng/20_mechanisms/channels.md`
- parameter gradients experiment: `docs/eng/40_experiments/exp_gradient.md`
- influence port (integration contract): `docs/eng/integration_contract.md`

