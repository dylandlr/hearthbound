# v0.8.2 — Real Minecraft live policy observation / scripted reference

The v0.8.1 sequential surrogate passed on GitHub Actions. On 300 paired held-out synthetic episodes of 60 steps, the scripted oracle averaged 15.9767 flour / 0 wasted actions, the untrained MLP averaged 0 flour, and the imitation MLP averaged 15.9167 flour / 9.05 wasted actions. These are synthetic surrogate outcomes, NOT live Minecraft policy measurements.

## Read-only live bridge

Use `/hearthbound policy_probe <millstone block position>`.

The dedicated Minecraft server reads:
- actual registered Create millstone, input and output ItemStacks
- millstone kinetic speed (powered/unpowered)
- exactly one nearby named Sable villager
- Sable's verified mill experience from persistent Forge entity NBT

The *scripted reference policy* returns one of:
`ABSTAIN`, `INSPECT_UNPOWERED`, `REQUEST_WHEAT_HAUL`,
`WAIT_FOR_PROCESSING`, `COLLECT_OUTPUT`.

The bridge **cannot issue actions**, initiate a haul, mutate inventories or grant rewards. Output includes `EXECUTION_DISABLED NO_ML_INFERENCE`. Source wheat availability and citizen needs are not observed yet. The live probe is a deliberately tiny, bounded domain; it must not be mistaken for the six-feature synthetic observation schema.

## New dedicated-server assertions

While using the existing, genuine powered Create machine and Sable:
1. A powered, empty mill with one nearby Sable must recommend `REQUEST_WHEAT_HAUL`.
2. When real flour has been produced, it must recommend `COLLECT_OUTPUT`.
3. After Sable's separately authorized physical milling experiment and receipt, the probe must report `experience=1`.

If this CI run passes, we have confirmed that decision suggestions are based on actual Minecraft world observations, **not** that a neural policy is controlling the citizen.

## Remaining for real trained-vs-scripted gameplay

- Version a Java-compatible inference model artifact (weights/hash/features/actions) from the trained PyTorch policy.
- Build a full agent observation schema that can be populated without scripted oracle / privileged state.
- Add action masks, server-side safety gate and high-level action executor only after live-action tests.
- Execute matched, held-out Minecraft trials for three policies and compare flour, elapsed ticks, wasted actions and violations.
- Train an experience-driven RL policy if claiming reinforcement learning rather than imitation learning.
