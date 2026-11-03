# Hearthbound v0.9.0 — Verified Minecraft experience / reward ledger

## Established live result

PR #109's dedicated Forge/Create experiment passed all checks, including both real Minecraft policy arms, the post-restart Sable experience test, and the independent policy comparison. Each policy selected an authorized wheat-hauling task and completed it in **201 Minecraft game ticks** on the matched test fixture. Both observed Create flour and a verified increment in Sable's persisted mill-experiment memory.

This establishes model-selected Minecraft task execution, **not reinforcement learning** or learned-policy superiority.

## Reward contract v1

The offline evidence builder now requires:

1. The strictly verified real-game task-result JSON (\`hearthbound.real-minecraft-policy-trial.v1\`).
2. Three server-observed paired shadow-policy states (\`hearthbound.live-shadow-evidence.v2\`), including an empty powered mill and Sable's subsequent verified experience.
3. The independent **post-restart** Sable memory receipt, \`SABLE_VERIFIED_EXPERIENCE_SURVIVED_REAL_SERVER_RESTART\`, in that arm's authenticated RCON transcript.

It records the model/scripted selected high-level action, **an actually observed starting state**, terminal outcome, elapsed Minecraft ticks, input SHA-256 evidence digests and test-world seed. No invented intermediate transitions or hidden counterfactual observations.

The two rewards are explicitly separate:

| Reward | Signal | Value |
|---|---|---:|
| Colony | Verified production success | +1.0 |
| Colony | Time cost | -0.001 per actual Minecraft game tick |
| Personal | Verified task completion | +0.5 |
| Personal | Verified increment in citizen experience | +0.5 |

For the previous successful 201-tick examples, the *proposed offline contract* would yield colony reward **0.799** and personal reward **1.0** for each arm. These rewards are engineered labels, not values Minecraft itself paid to the agent. Rewards cannot be credited on incomplete tasks or missing restart evidence. No learned weight update occurs.

## GitHub Actions artifacts

Only after a real server job passes gameplay **and** persisted-memory verification do we build its \`minecraft-experience.json\` record. After both matrix jobs pass, the comparison job aggregates two validated records as \`minecraft-experience-dataset.json\`. The fast evidence-contract workflow runs synthetic unit tests for the parser, invalid reward receipts, and two-arm aggregation without Minecraft.

## Research limitations and next step

Two successes of the same one-shot action provide almost no meaningful state-action coverage for RL. This ledger is a provenance foundation, not a training dataset of useful size. The next milestone must add **varied held-out Minecraft tasks**, safe alternative actions (including waiting/recovery), explicit action masks and failure outcomes, and measured state transitions across time. Only then train a reward-driven policy in a fast simulator or from sufficiently diverse genuine game rollouts, and evaluate it on unseen worlds without leakage. Keep scripted and neural baselines frozen for comparison.
