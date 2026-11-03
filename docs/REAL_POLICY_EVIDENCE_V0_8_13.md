# v0.8.13 — Real two-arm outcome evidence

On PR #108 (the earlier branch), both real Forge/Create trials executed the authorized one-shot policy-selected haul:
- SCRIPTED: \`REAL_POLICY_TRIAL_RESULT\` recorded completion=1, elapsed_ticks=201, verified_experience=1, flour_observed=1.
- TRAINED_MLP: same independently observed results, elapsed_ticks=201.
- Both jobs failed *after* the task because an overlong \`LIVE_SHADOW_PAIR\` console line was split/truncated by the CI log transport, causing the evidence parser to reject all three expected stages. Thus neither whole job completed its restart-persistence check or produced a final artifact.

This revision preserves the full server RCON responses and compares observation fields in the smoke client, but emits a compact, bounded record per stage. A strict parser checks all three stages, citizen identity, powered fixture, observed output, experience and read-only status. Fast Python evidence-contract CI validates the parser independently of a time-consuming Forge boot.

A second CI job named \`compare-policy-arms\` runs **only if both** real server matrix arms pass. It downloads the two independently verified trial artifacts and emits \`policy-comparison.json\` with elapsed ticks and their difference. One episode per arm is descriptive, not a basis for statistical inference.

## Scientific scope

The scripted controller and the MLP currently select the **same one-shot hauling task** on this fixture. Both feed the same SableHauling executor and use a deterministic scripted-imitating MLP. Equal recorded 201-tick outcomes are entirely plausible and neither demonstrate generalization nor experience-driven RL. More difficult held-out environments, randomized layouts, multiple replicates and a trainable policy are required before comparing behavioral intelligence.

Do not represent the prior failed jobs as fully passed CI; they verified physical gameplay but terminated during report parsing before the post-restart persistence step.
