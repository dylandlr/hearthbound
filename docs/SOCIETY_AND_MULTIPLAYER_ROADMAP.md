# Hearthbound: emergent societies and a joinable server

Planning baseline: 2026-11-09. This is a staged readiness plan, not a deployment
announcement. No address, host, paid resource, public port or player invitation
has been created. Public deployment requires the owner's explicit approval and
access to the selected host. Do not put credentials in Git, chat transcripts,
test artifacts or this document.

## What the evidence currently supports

The latest #190 head, `888bfef7bccc199e3770d98befa59b5f0cb4c391`, passed all
12 triggered workflows when checked on November 9. It proves a bounded,
operator-triggered failure/report/recovery experiment in real Forge. The earlier
matched pilot found no trained MLP advantage over the scripted baseline. A
running dedicated development server and genuine item receipts are useful
foundations; they do not establish self-sustaining colonies or emergent society.

v0.16.6 adds restart fencing and adversarial persistence acceptance; see
[its contract](RESTART_FENCED_BELIEFS_V0_16_6.md) and the exact-head CI on its PR.
NBT is still not a durable physical transaction system. A private developer
playtest can precede society readiness, but must be labeled as such and use a
disposable world. The desired society-observation invitation requires later gates.

## Engineering milestones, in order

| Gate | Implementation | Evidence needed before advancing |
| --- | --- | --- |
| A: truthful restart | Preserve clean-save negative/request identity; fence old reports; durable extraction intent/outcome reconciliation next | Clean boot, forced kill, torn writes, world swap, partial rollback and cargo quarantine; no invented success or duplicate items |
| B: autonomous recheck | Citizen chooses REQUEST_REOBSERVATION or WAIT_FOR_REPORT from owned evidence; nearby scout accepts or declines based on its priorities and task availability | No operator dispatch/observe/share after setup; real movement, local direct sensing, range-limited delivery; explicit requested/accepted/observed/delivered/expired states and no false acceptance |
| C: fair policy experiment | Baseline without negative feedback, scripted failure-aware policy, frozen simulator-trained MLP; identical executor and information masks | Pre-registered held-out seeds and scenarios; physical source/destination deltas, retry counts, abstentions, recovery ticks, communication cost, route failures, stale-report rejection; paired seed-level effects and uncertainty intervals |
| D: sustainable colony loop | Local needs, food replenishment, storage, hauling, Create production, task interruption and finite shared resources | Multi-hour runs without intervention after setup; consumed/produced item conservation, bounded hunger/death, contention recovery, chunk unload/reload and restart continuity |
| E: social coordination | Persistent citizen identity, local knowledge, specialization, exchange, commitments, resource claims and conflict resolution | Repeatable networks of interdependence under scarcity; partner switching, broken commitments and recovery; compare against scripted/no-communication/role-fixed controls |
| F: society evidence | Several colonies, travel/trade, changing relationships and durable institutions arising from agent decisions | Multi-day held-out worlds; measurable specialization, trade networks and conventions that persist after perturbation; no hidden role or faction script presented as emergence |

Budgets must bound sensing, planning and communication per tick. Never give a
policy global inventories or operator audit JSON. Publish both failures and
successes. A delivery counts only with a matching executor job and independent
physical deltas. Create processing needs actual machine callbacks, valid job
binding, witnesses and contribution causality. Do not grant rewards, research
credits or unlocks because a narrative, predicted outcome or task selection says
it happened. Keep LLMs deferred until the deep-learning scope and evaluation gates
are complete; no online weight updates in the frozen-policy experiments.

Gate C starts with at least 20 paired held-out seeds as a proposed pilot budget,
not a promise of statistical power. Report one aggregate per seed, bootstrap
paired seed differences, retain timeouts/abstentions in denominators, and increase
the predeclared sample if intervals cannot resolve the practical effect. Repeated
ticks from one world are not independent society samples. Select policies by
physical outcomes, safety and cost; do not assume neural superiority.

## Staged deployment and invitation gates

| Stage | Access and work | Exit criteria |
| --- | --- | --- |
| 0: release candidate | No external listener. Resolve stacked PRs in dependency order after review; pin one commit and build its reobfuscated JAR | All relevant exact-head CI green; pack manifest, model hash, configs and rollback package recorded |
| 1: local dedicated compatibility | Loopback only, a separate test save; production Forge launcher rather than Gradle `runServer` | Real client joins, reconnects and changes dimension; Create renders/operates; second client sees same citizens/items; clean restart preserves identity |
| 2: private operator staging | Owner-approved private network/VPN; owner only; throwaway valuables | 24-hour monitored soak, restore rehearsal, ordinary-player permission checks, stable performance and no unexplained item deltas |
| 3: society readiness | Continue closed testing through gates B–E | At least 72 hours of sustained colony operation, independently logged interventions, bounded resource use, multiplayer interference tests, restart recovery and no unresolved corruption; claim society emergence only after gate F |
| 4: invited alpha | Explicit approval of host, cost, access method and player list; initially 2–4 allowlisted testers | Exact client pack and known-limitations sheet; validated backups, successful owner join, non-admin permissions, rollback operator available; then send invitations only when authorized |
| 5: wider service | Separate approval; increase citizens/players gradually | Repeated load/abuse/restore tests, moderation capacity, storage/CPU headroom, incident procedure and stable release process |

CI's offline-mode RCON fixtures are disposable experiments. Never copy their
passwords, automatic EULA acceptance or authentication settings into a player
server. An owner must review/accept the Minecraft EULA before server operation.

## Modpack compatibility and deliverables

Use **Minecraft Java Edition 1.20.1, Forge 47.4.10 and Java 17** for the initial
candidate, matching this repository. Forge's 1.20.1 documentation specifies a
64-bit Java 17 JDK for development. Do not substitute Bedrock, Fabric, NeoForge,
Paper or a vanilla server for this Forge build.
[Forge documentation](https://docs.minecraftforge.net/en/1.20.1/gettingstarted/).

Create 6.0.8 has an official 1.20.1 release. The repository's development artifacts
are Create `6.0.8-289:slim`, Ponder `1.0.91`, Flywheel `1.0.5` and Registrate
`MC1.20-1.3.3`. These compile-time coordinates are **not a verified distributable
client/server modpack manifest**. Inspect the release JAR's bundled dependencies
and required companions before packaging; do not install duplicate nested
libraries. [Create's release notes](https://wiki.createmod.net/users/changelogs/6.0.8).

Produce separate client/server manifests recording each approved download URL,
filename, exact version, SHA-256, license and side (client/server/both). Include
Hearthbound commit/JAR hash, frozen weights/hash and configuration checksums.
Respect redistribution permissions; provide original-source download instructions
when bundling is not allowed. The repository declares All Rights Reserved, so
public pack distribution needs an explicit owner decision. Client-only shaders
and visual mods stay off the dedicated server. Add optimization or permission
mods only after a separate Forge/Create compatibility trial. A successful
development `runServer` test does not prove the packaged launch works.

## Hardware and performance budget

These are **starting allocations to measure**, not tested capacity or purchasing
recommendations. No hosting vendor or paid plan has been selected.

| Trial | Host budget | Initial limits |
| --- | --- | --- |
| Private 2–4 players, 8–16 active citizens | Modern high single-thread CPU, 4 dedicated cores, 16 GB host RAM, 6–8 GB Java heap, SSD/NVMe with at least 50 GB free plus separate backup capacity | View distance 6–8, simulation distance 4–6, limited loaded colony chunks |
| Expanded 4–8 players, 32–64 citizens | Measure first; consider 6–8 cores, 32 GB host RAM, 10–12 GB heap if memory data warrants it | Raise one population/chunk limit at a time; keep the prior stable cap as rollback |

No GPU is required for the current small frozen MLP inference. Training can run
outside the game host. Leave RAM for the OS and backups; avoid assuming more heap
fixes tick latency. Record p50/p95/p99 tick time, TPS, pauses, heap, active entities,
loaded chunks, pathfinding/observation cost and disk growth under simultaneous
players and Create machinery. Proposed acceptance: sustained near-20 TPS,
p95 tick time below 45 ms and no persistent tick backlog at the advertised cap;
measure worst-case contention and chunk generation too. Failed budgets mean
lower caps or optimized scheduling, not overstated capacity.

## Persistent world, backup and rollback

Run as a non-admin service account with a fixed persistent data directory. Keep
world UUID, all dimensions, entity/region files, player data, saved data, causal
journals, model artifacts and configs together as a versioned recovery unit.
Keep binaries separately by release; record which release last wrote the save.
Never start the same writable world in two server processes. For upgrades, stop,
take a coherent backup, clone into isolated staging, rehearse migration and join,
then switch release. Roll back the matching world plus binaries together.

Initial policy: consistent hourly snapshots, seven daily and four weekly copies,
encrypted off-host copy, and a retained pre-upgrade snapshot. Prefer graceful
stop-and-copy initially; alternatively pause saving, `save-all flush`, take a
filesystem-consistent snapshot including journals, and always resume saving.
A casual live copy of a subset of region/NBT files is not a coherent backup.
Set proposed recovery objectives of at most one hour of progress loss and a
30-minute restore, then time a rehearsal before promising them. Alert on failed
backups, low disk and repeated crashes. Test restoration into a private isolated
instance, verifying world/citizen/job identities and inventory conservation.
Keep production stopped while restoring; do not mix old entity data with newer
journals or reset the UUID to bypass validation. Crash ambiguity stays quarantined
for operator reconciliation; never auto-delete cargo or mint replacement items.

## Identity, permissions, privacy and security

Use authenticated Java accounts (`online-mode=true`) and an enforced allowlist
(`white-list=true`, `enforce-whitelist=true`). Track players by authenticated UUID,
citizens by persistent entity UUID plus world identity, not display name. Keep
ordinary testers unopped. Hearthbound's experiment commands require permission
level 2; only trusted operators may spawn actors, mutate fixtures or run probes.
Verify denied commands as an actual ordinary client, not only through RCON.

Start with loopback binding using [the example](../server/server.properties.example).
For approved remote staging, bind deliberately to the selected private interface
and firewall the game port to the private access network. Use a host firewall,
key-based admin access and a non-admin process. Disable RCON/query by default;
if operationally necessary, restrict RCON to an encrypted administrative path
and local/private firewall rules with a unique secret. Never expose RCON publicly.
Do not open router ports, publish DNS/IPs or pay for hosting without approval.

Restrict filesystem/backup access, patch the OS/JVM, and review mod provenance.
No public metrics dashboard or raw CI upload of real saves/logs. Minimize retained
player IPs/chat; proposed operational-log retention is seven days, with restricted
incident retention when needed. Keep scientific receipts separate and pseudonymize
player identifiers before sharing. Tell testers what is logged, who can access it,
and how to request removal; backup expiry governs removal from retained copies.
Player chat and behavior are not training data without separate informed consent.
Agent messages, signs, books and player chat are untrusted game input and must
never become filesystem, server-console or privileged tool instructions.

## The invitation handoff

Before invitations, provide the owner with the passing readiness record, approved
cost/capacity, exact client pack, backup/restore result, access method, player UUID
allowlist, known limitations and rollback contact. Confirm owner login first. A
tester then installs the matching Forge profile, verifies pack hashes, joins the
approved private address, and confirms reconnect/persistence as a non-admin.
Do not advertise autonomous societies while recovery still depends on operator
commands; distinguish a developer preview from the requested society-ready alpha.
