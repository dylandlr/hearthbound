# v0.8.10 — Reproducible two-arm Minecraft CI readiness

The scripted and trained policy trials are run in independent disposable Forge/Create worlds. They now use exactly the same level seed `hearthbound-policy-v0-8-10` so terrain generation is no longer an uncontrolled difference. This **does not** synchronize random mob decisions, scheduler timing, villagers' internal RNG or process scheduling.

To prevent a valid experiment from failing prematurely while Gradle resolves a cold Forge/Create runtime, the dedicated-server startup readiness budget increased from 8 to 12 minutes per boot, the CI job timeout increased from 20 to 35 minutes, and the first boot now prints last server/Gradle lines every 60 seconds. Startup remains fail-closed: the run requires a real Minecraft `Done` ready line and Hearthbound mod initialization before beginning the RCON experiment.

A successful run must still produce the strict independently verified wheat transfer, real Create flour, persistent Sable experience, game tick completion log, and three-state shadow policy comparisons. An infrastructure timeout must not be reported as neural gameplay failure or success.

## Pending research work

One scripted and one imitation-MLP trial per run can prove policy-dispatched Minecraft execution but **cannot** establish model superiority. Next add multiple independently seeded held-out worlds, paired outcomes with measured variance, policy version/hash, and eventually train a reward-driven RL controller rather than scripted-rule imitation. Maintain the exact seed in every trial's metadata and never silently change experimental fixtures.
