# Hearthbound v0.15.1 — Observed event attribution and detection latency

## Why

The new out-of-distribution stress benchmark in PR #171 passed: greedy forecast was −2.27778 direct discoveries per 64-decision episode compared to scripted rotation. The frozen age-blended predictor averaged +0.00463; the coverage guard again made zero deviations. The age-blend made around 22–24 different choices per episode but saw largely the same number of changes. This suggests that raw count alone may conceal differences in *when* a real latent event is detected.

We are **not** changing any agent policy or model weights in this milestone.

## Direct observation and hidden evaluator contract

`benchmark_attention_event_latency.py` replays the same frozen forecaster against scripted, greedy, age-blended and coverage-guard selectors. It records only the selected-source direct observation at every time step, with source ID, prior personally observed state, new state, first-visit flag and confirmed disagreement.

A separate offline evaluator then reads the pre-generated latent timeline. For a source's transition at time T, count it as witnessed only if the agent had inspected that source **before T**, reinspects it **at or after T but before its next same-source transition**, and confirms that the new directly observed value **differs from its own previous observed value**. If a transition reverses before observation, or there was no earlier baseline, do **not** invent a detection. A witnessed event's delay is the selected reinspection time minus T.

The evaluator additionally reports: all latent transitions, baseline-eligible transitions, events witnessed before their next same-source transition, events not witnessed, total/average detection delay for witnessed events, total direct reinspection disagreements, nonproductive reinspections and first inspections. Strict regression fixtures cover immediate detection, unseen reversal and missing pre-transition baselines. The metric is a synthetic world-observer audit, *not* a reward or observation provided to an agent.

## Experimental design

Reuse exactly the three previously precommitted novel stress schedules from PR #171: permanent depletion, unannounced bursts and long gaps, each 64 decisions. Freeze the existing GRU forecaster once per seed (11,17,23), with 180 original training episodes; compare all four unchanged policies on 24 independently generated timelines per seed/schedule. Report signed latent timeline manifests, frozen model parameter hashes and per-episode paired event-detection differences relative to scripted selection. No parameters are tuned on outcomes.

This evaluation avoids conflating first-time resource discovery (which may reward any source on its first visit) with actual detection of **changes since a known observation**. However, detection latency is conditional on detected events: it must be reported alongside missed-event counts, not alone, because a policy could obtain a small average delay by missing slower events.

## Boundaries

All data are simulated. The real Forge four-source attention challenge remains a separate experiment in which scripted attention witnessed 8/16 operator mutations and the deployed frozen MLP 5/16. None of those results train this forecaster or adjust decision thresholds. No Minecraft weights, mods, live tasks, LLMs, or RCON authority are modified or deployed. The project still requires independently held-out real Forge evaluations before claiming runtime generalization.

## Verified initial run, and follow-up metric refinement

The initial event-journal benchmark passed in GitHub Actions [run 42108926580](https://github.com/dylandlr/hearthbound/actions/runs/42108926580). Mean directly detected latent transitions per 64-decision episode (scripted, age-blend, greedy): permanent depletion **4.000, 4.000, 1.333**; bursty mutations **8.958, 8.972, 7.389**; long gaps **4.000, 4.000, 1.403**. The coverage guard exactly matched scripted rotation.

For events that were witnessed, mean **total** detection delays per episode (scripted, age-blend) were: depletion **5.556, 6.611**, bursts **9.250, 9.597**, long gaps **5.833, 6.056**. Those conditional totals can misleadingly reward greedy forecasting for ignoring events.

The additional **horizon-censored event delay** metric now counts the actual delay for a detected event and the remaining evaluation horizon from the event time for each undetected event. This allows paired comparison without discarding misses. We retain event detection counts separately; a small score does not authorize a model swap. An independently signed `report_attention_event_admission.py` checks per-episode paired differences and refuses to admit the age-aware rule unless it maintains event coverage AND no worse censored total delay across all stress regimes. Even if these synthetic conditions are met, `model_promotion_authorized=false` remains mandatory.

The separate full Forge CI workflow in PR #172 initially failed on the **scripted seeded-C wheat-hauling smoke test**, which timed out waiting 150 seconds for delivery. The dedicated simulator event attribution workflow passed; this failure is a real, separate regression/test failure requiring investigation or a reproducible rerun—not proof that event-latency code affected live hauling. No runtime Forge mod source was changed in this PR.

## Forge hauling smoke: repeated-run evidence and instrumentation

The scripted seeded-C wheat-hauling test failed once on GitHub run **42108926499**: source chest initially held eight wheat, the job was assigned, and the direct destination inventory check remained false for 150 seconds. The passing rerun on **42116833645** completed every server matrix case, including seeded-C, and all five policy comparison jobs. All seven workflows at that SHA passed. Thus a one-off failure has been observed, but the underlying pathfinding/job/inventory failure mode is **not established**. Do not label it resolved simply because a rerun was green.

The failed job's archived artifacts contained `server-smoke.log`, `smoke-rcon.log`, preflight checks and latest server log; it did **not** contain a series of villager positions and job snapshots during the 150-second interval. The passing job continued to later real Create production probes. These support a test-timing/behavior investigation but do not identify an exact root cause.

The latest follow-up adds a separately unit-tested `haul_smoke_diagnostics.py` command contract, with strictly read-only RCON probes at **30, 60, 90 and 120 nominal seconds**, capturing Sable's haul-audit, position, source chest items and destination chest items. The fixed **75 × 2-second polls**, physical transfer requirement, source/destination inventory assertions and real proximity assertion are unchanged. The 150-second failure path still prints final read-only diagnostics and raises `AssertionError`.

CI now validates the allowed diagnostic commands, fixed acceptance threshold, request-ID uniqueness, parseability and refusal of invalid poll positions. Further real server failure would produce a position/job/inventory timeline useful for distinguishing pathfinding stall from inventory mutation or a lost claim, without any reconciliation or automatic rescue that could hide the failure.

**Important:** new periodic RCON probes incur small additional real-time processing overhead. Their timestamps are nominal based on the sleep/poll budget, not an assertion about exact wall-clock server ticks; the existing 150 seconds is also a nominal polling threshold rather than a hard wall-clock deadline.
