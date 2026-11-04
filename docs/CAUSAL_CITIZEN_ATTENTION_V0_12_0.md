# Hearthbound v0.12.0 — Causal attention from personal observations

This research milestone sits on top of PR #140. It removes a privileged feature from the simulator-trained attention policy and requires predictions to use only direct historical observations of registered sources. The new policy is **not deployed into the Minecraft agent or task executor**.

## Feature contract

Each of four abstract sources contributes:
1. Never-inspected flag.
2. Last directly observed availability flag.
3. Capped normalized age since direct inspection.
4. **Empirical change frequency** = observed differing readings / pairs of consecutive direct inspections.

Before two direct inspections, the change-frequency estimate defaults to 0.5 (uncertain prior). It never accesses actual simulator flip probability, current hidden availability, intermediate state changes, or other citizens' private observations. The estimate is *not* an unbiased estimate of per-tick volatility because unobserved changes between samples are aliased.

## Training and test separation

The environment uses the same synthetic resource process, initial MLP architecture and one-inspection-per-step budget as the earlier reference. Train separately for seeds 11, 17, and 23, 500 episodes each. Evaluate 100 held-out episodes per trained model across original, high-volatility, low-volatility, and heterogeneous-volatility scenarios; preserve the original scripted least-recently-inspected baseline unchanged. Resample **paired episode differences** 300 times for each training-seed/regime cell.

This benchmark is not a controlled feature ablation with identical learned weights: model weights must be retrained after removing privileged input. Its comparator to v0.11.9 is exploratory, using the same synthetic process and seed families but a changed feature representation.

## CI acceptance

- Invalidate knowledge-free accesses: changing unseen source truth or latent volatility must not change the policy feature vector.
- A direct inspection updates only the selected source's observed statistics.
- Repeatable seeds must produce identical full reports and SHA-256 hashes.
- Output marks `SIMULATED_ONLY`, `privileged_volatility_feature=false`, `minecraft_policy_deployed=false`, `citizen_actions_authorized=false`.
- Independently generated benchmark JSON is retained as a GitHub Actions artifact; no superiority claim until successful CI and inspection of results.

## Next real Minecraft bridge

Develop a chronological offline replay contract for `CITIZEN_WATCH_RECEIPT` and `PERCEPTION_RECEIPT` events:
- Record each citizen's actual candidate subscriptions and what could have been observed **at decision time**.
- Include only events with server timestamps no later than the replay decision tick. Do not reconstruct features using future observations.
- Avoid counterfactual reward claims unless the server actually observed the alternative outcome; use abstention or clearly marked simulator-only counterfactual evaluation.
- Replay without issuing watch commands, changing world state, or granting new Minecraft execution authority.

## Initial measured simulator results (CI run 41753054446)

The new causal-history benchmark completed and `CAUSAL_ATTENTION_HISTORY_TESTS_PASS` was observed. Each cell is the **mean trained-minus-scripted discovered changes per 32-observation synthetic episode** across 100 held-out worlds; three independently trained models are shown separately.

| Training seed | Normal | High volatility | Low volatility | Unequal volatility |
|---|---:|---:|---:|---:|
| 11 | -2.15 | -0.26 | -0.64 | +3.95 |
| 17 | -0.40 | +1.16 | -0.71 | +2.41 |
| 23 | -2.12 | +1.56 | -1.42 | -4.51 |

Training-seed sensitivity is severe for the unequal-volatility regime: the third MLP loses 4.51 discoveries per episode despite the first two gaining. The original v0.11.9 privileged-volatility model had positive gains for all three seeds in this regime. Thus the previous advantage **does not survive removal of hidden volatility consistently**. Also note the causal model was retrained and cannot be directly interpreted as a strict fixed-weights feature ablation. The benchmark is not a claim of improved Minecraft behavior.

Research priority: improve the observation-history representation (account for elapsed time between readings, uncertainty/inspection count, and partial observability) and compare against stronger simple causal baselines before trying larger networks. Preserve seed 11/17/23 as previously measured reference results; make new model-selection decisions using separate validation seeds.
