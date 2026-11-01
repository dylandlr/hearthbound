# v0.7.16 — Real powered Create milling acceptance

The dedicated-server smoke test now extends beyond Sable's verified chest haul:
- Place an actual `create:creative_motor` pointing upward at (9,98,3)
- Connect `create:shaft[axis=y]` at (9,99,3)
- Place the real `create:millstone` at (9,100,3)
- Summon one real `minecraft:wheat` item above the millstone
- Poll the actual Hearthbound `sable mill-inspect` command every 2 seconds, up to 180 seconds
- Fail the job if no real flour item is observed in the millstone inventory

This first production probe is **machine-only**; a creative motor is permissible as the experiment's controlled power source, not as a survival gameplay claim.

## Acceptance and limitations

A passing job would establish real machine production in a dedicated Minecraft/Forge/Create server, with server-side output inventory observations. It would **not** establish that Sable autonomously delivered the input, that a verified Hearthbound citizen-processing receipt was produced, or that an ML policy learned.

The current job uses the Create output inventory as the primary physical acceptance condition; the separate `verify-real-mill-production.py` script remains required to establish a citizen-attributed `HEARTHBOUND_PROCESS_RECEIPT`. The mixin may reject unreserved processing and must be investigated if the probe fails.

For the first **citizen learning** demonstration, compare a trained and an untrained policy on matched held-out seeds, explicitly recording decisions, inventory transitions and persistence. Do not claim learning from a single successful scripted haul.

The CI status of this newly committed production test must be inspected before reporting success.
