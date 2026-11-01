# v0.7.15 — Actual Create block smoke probe

The existing dedicated-server smoke test already proves that Sable physically transfers wheat from one real Minecraft chest to another: source 8→7 and destination 0→1, followed by an entity proximity assertion.

This change extends that SAME Forge dedicated-server test by placing `create:millstone` at (9,100,3) and running `sable mill-inspect` against it. This confirms Create block registration and the Hearthbound machine-inspection path, rather than mistaking a vanilla chest for a millstone.

**Not yet proof of production:** no shaft, kinetic power, input/output recipe operation, flour ItemStack, production receipt, or policy learning are asserted here. A fully powered, instrumented Create experiment remains the next step. The CI job must pass before the new machine probe can be called verified.

For the first genuine production trial, check both `HEARTHBOUND_PROCESS_CALLBACK` and `HEARTHBOUND_PROCESS_RECEIPT`, inspect a real flour stack, run `scripts/verify-real-mill-production.py` on the server log, and capture a real client recording. Do not label a synthetic test or headless rendering as Minecraft gameplay.
