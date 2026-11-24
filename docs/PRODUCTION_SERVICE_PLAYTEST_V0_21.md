# Real Create production service playtest v0.21

## Revision and current evidence

This work is based on the newest remote branch verified on 24 November 2026:
`feat/need-driven-service-runtime-v0-20`, commit
`4c0d6d058d5b38ec3e791f7f115e92063d0dd559` (draft PR #223). All 217 remote
branch heads were checked. The unfinished local
`feat/production-service-learning-v0-21` changes were preserved and continued
in `feat/production-services-verified-v0-21`.

At initial publication, 13 standalone Java civilization suites passed locally
with Java 21 and Java 17 source/target settings, and 18 Python evidence checks
passed. This local Java installation does not support `--release 17`; the real
Java 17 API gate, Forge compilation, and live acceptance run in the dedicated
GitHub workflow. No live production result is claimed until that workflow and
its retained inventories have been inspected. Update this section with the
exact checked revision and run after validation.

The first live run at `99b68fd` is retained as a failure:
https://github.com/dylandlr/hearthbound/actions/runs/45479379392.
Its recipient selected the reported production request, then died from
suffocation before delivering wheat. The server also logged oversized NBT
strings while saving the growing history. Follow-up changes install a stable
roof before excavating the disposable fixture, retain spawn clearance/health
witnesses, detect missing actors immediately, and encode JSON histories as UTF-8
byte arrays. Actual Minecraft NBT tests cover payloads beyond 65,535 bytes,
Unicode, existing string saves, and malformed data. These changes do not turn
the failed world into a success or resolve the broader reliability gate.

## What the player can watch

Two citizens have identical capabilities. One starts near a flour buffer and
observes its shortage. It can carry that private request toward a public wheat
source and exchange it with a nearby citizen. A recipient can select the whole
production service: collect wheat, take it to the reserved mill, wait for actual
Create processing, collect the resulting flour and wheat seeds, and deliver
the complete batch to the buffer. Its own value model then updates from that
finished service. Repeated batches reuse the same physical machine.

This remains a bounded service pilot: at most 16 enrolled citizens and eight
source/buffer sites. Initial priorities, allowed options, encounter distance,
expiry, and execution safety gates are authored. The online estimator is
recursive least squares, not deep Q-learning or MAPPO. Repeated successful
work is not by itself an emergent occupation.

## Manual commands in a disposable Minecraft world

Use the existing Forge 1.20.1/Create development setup and a playtest JAR built
from this branch. Build a reachable wheat chest, a powered Create millstone,
and a separate destination chest. The example positions below match the CI
fixture; replace them with the actual positions of your infrastructure.

```text
/hearthbound-services configure-source 36 101 3
/hearthbound-services configure-mill 11 101 3 4 101 3 4
/hearthbound-services enroll <first-citizen-UUID>
/hearthbound-services enroll <second-citizen-UUID>
/hearthbound-services start
/hearthbound-services status
/hearthbound-services records 0
```

Use citizens created with `/sable spawn` that do not belong to another
controller. The commands register geometry and a four-flour target; they do
not give either citizen the remote inventory contents. The first observation
requires a citizen near the output chest. Record pages contain four events;
use offsets 4, 8, 12, and so on to inspect later records.

```text
/hearthbound-services set-target 4 101 3 6
/hearthbound-services stop
```

A higher target introduces another shortage. `stop` cancels proven empty jobs
and retains unresolved physical custody. After a clean stopped restart, use
`start` explicitly. An unresolved machine or output job stays held for review;
repeated `start` does not resolve it or resume a material mutation.

## Automated live acceptance

The `Production services and private learning` workflow checks the exact PR
head, compiles Forge, and runs three server sessions against one disposable
world:

1. Complete multiple powered production cycles, preserve every output item,
   link a received packet to recipient production, observe private parameter
   updates and a subsequent scored choice, then observe target closure.
2. Reboot and compare stopped histories, private model digests, and native
   inventories. Remove the external motor power before starting a new shortage,
   wait for a real input delivery, then stop with that input still in the mill.
3. Reboot again. Require the input and reservation to remain held, reject an
   unsafe start, and verify that neither output nor learning credit appeared.

The runner is `scripts/rcon_production_services_acceptance.py`; its
`--phase` values are `live`, `restart-and-hold`, and `held-restart`.
`run/production-service-acceptance.json` retains the full event sequence,
independent native inventory responses, callback witnesses, model digests,
and explicit failure state. The workflow uploads it even when a phase fails.
Use this fixture only in a disposable test world: setup creates a test corridor
and replaces blocks in that corridor.

The known broader colony reliability failures remain a separate gate.
Neither a passing fixed fixture nor nonzero learned parameters establish
causal communication benefit, superiority over an authored controller,
generalization, a learned courier occupation, or a 100-agent society.
