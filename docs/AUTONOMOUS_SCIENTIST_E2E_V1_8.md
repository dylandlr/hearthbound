# Hearthbound v1.8 — Autonomous Scientist End-to-End Acceptance

Adds an independent real Minecraft / Forge + Create acceptance scenario. The test spawns Sable beside a stocked chest and powered Create millstone and issues only `sable auto-research-on`.

The citizen's own server tick must: discover wheat and a millstone; select the physical experiment; assign the existing HAUL work through its reservation authority; persist a PROPOSED hypothesis; actually deliver wheat; obtain a Create process callback receipt; receive evidence-gated research credit and DIRECT_EXPERIMENT knowledge; and transition the hypothesis to CONFIRMED.

The fixture never calls `sable haul`, `sable experiment-discover`, or `sable hypothesis-mill-propose`. It uses admin RCON only to construct and inspect the controlled test world.

The new `.github/workflows/autonomous-scientist-e2e.yml` launches an isolated Forge dedicated server with Create and executes `scripts/rcon_autonomous_scientist.py`. It is separate from the generic `dedicated-server-smoke.yml` and the manually driven milling diagnostic.

## What this does not prove

The actor can select one explicitly templated wheat→flour research hypothesis, not invent arbitrary new recipes. Experimental trial is still grounded in an existing hauling path and a powered millstone, with no agent-designed machinery, general-purpose planning, autonomous communication research, or neural policy. A passing test proves the specified full-chain integration in the CI fixture, not broad scientific emergence. The branch remains draft until its own workflow succeeds.
