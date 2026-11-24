# Roadmap and Development Gates

## Current development route: need-driven services

The v0.20 service controller completed its scoped live storage acceptance on
`4c0d6d058d5b38ec3e791f7f115e92063d0dd559`: locally observed shortage → physically
carried request → persistent commitment → native physical transfer → target
closure. The v0.21 work extends the same executor and private knowledge
boundary through actual Create processing, output custody, final flour delivery,
and per-citizen learning. See [the production contract](PRODUCTION_SERVICE_LEARNING_V0_21.md)
and [playtest](PRODUCTION_SERVICE_PLAYTEST_V0_21.md) for its validation status.
At `17c3c353`, four real Create batches delivered four flour and two seeds;
both citizens produced output and updated their private models. Completed
restart and held unfinished-input restart passed. The broader legacy colony
reliability gate remains unresolved because citizens can fall from its elevated
fixture after completing delivery. This is still a bounded engineering pilot;
no policy-performance or emergent-occupation claim is promoted.
The small recipient-only PPO diagnostic is paused; frozen simulator baselines
remain reference evidence.

The next bounded increment, [shared neural services v0.22](SHARED_NEURAL_SERVICES_V0_22.md),
now passes its six-slot real Forge integration/restart cohort on `495938dc`.
Three offline training seeds improved the fixed simulator comparison, but the
preselected neural checkpoint averaged 7.5 live deadline flour versus 8.0
untrained and 8.5 authored. Both neural worlds responded to later demand at both
sites, with only two productive citizens and lower recorded travel/message costs.
This is a verified neural integration milestone, not a throughput promotion or
learned division-of-labor result. Private RLS remains the default.

Next calibrate native timing, yield, refusals and information gathering, then
train/evaluate improved allocation on fresh worlds with a private-RLS control.
Use complete native option transitions before claiming learning from Minecraft
experience. Do not turn
each internal implementation change into a new full benchmark campaign. The
three milestone deliverables and their evidence boundaries are defined in
[Need-driven service architecture v0.20](NEED_DRIVEN_SERVICE_ARCHITECTURE_V0_20.md).

The historical gates below still apply to claims about the corresponding feature.

## D0 — Design foundation
Define first-slice behavior, AI policy interface, experiment protocol, Minecraft/Create compatibility strategy and acceptance criteria.

## M1 — Minecraft dev environment
Pin Java/Gradle/Forge/Create; verify a real Minecraft client/server boots with the integration mod. CI compile + dedicated-server smoke test when feasible.

## M2 — Citizen embodiment
Persistent named Sable entity, navigation, registered jobs, inventory claims and recovery.

## M3 — Real Create mill
Working Create blocks, workshop registration, demonstration, autonomous hauling/milling/delivery, fault handling and persistence.

## M4 — Benchmark backends
Common policy API, deterministic baseline, tree and random forest offline training, held-out evaluation, optional neural/RL/LLM policies.

## M5 — First Mill gameplay video
Record genuine Minecraft client session, show version/commit and behaviors, share original file and reproducible playtest instructions.

## M6 — Colony life and multiplayer
Mara/Iven roles, schedules, relationships, projects, expedition loop, two-player validation.

Every milestone requires measurable acceptance evidence. Prefer small PRs and protect main after initial scaffolding.
