# v0.6.2 Priority policy integration

## Reconciliation with work in parallel tabs
The repository already includes ColonyPolicy, PriorityPolicy, ActionGate and
PolicyKernelTest on feat/colony-policy-kernel (also present in this branch).
These remain the authoritative decision interface. The research package
CitizenPriorityPolicy is an experimental prototype, not a separate runtime
scheduler. The new StochasticPriorityPolicy implements ColonyPolicy directly,
preserving observation versions and server-side ActionGate validation.

## Safety / sampling
FLEE if danger >= 60, then EAT if hunger >= 70, then REST if fatigue >= 80
if the corresponding action is executable. Work settings do not suppress
emergencies. Non-emergency work is filtered by executable and priority 0
(disabled), then assigned priority, traits, and temperature-based stochastic
sampling. Fixed seeds reproduce action sequences.

## Design limitations
This is a policy kernel, not yet a per-citizen persisted preference panel.
Sampling occurs only at scheduler decision boundaries, not every movement tick.
Study/social/build action kinds and their server executors need to be added
through explicit versioned migrations. The current policy cannot discover an
action not present in its partial observation. Actual Minecraft E2E tests and
CI execution remain required. The score coefficients are experimental.

## Next
Integrate one authoritative task owner for hauling and studying; add STUDY
to the versioned ColonyPolicy Kind contract; construct server-side observation
from citizen skill/personality/needs; then rerun kernel, Forge compilation and
headless Minecraft regression tests before any merge.
