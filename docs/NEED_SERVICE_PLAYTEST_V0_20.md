# Need service playtest v0.20

This is the first Minecraft integration of private needs and persistent service
options. It uses real wheat and chest inventories. The selected services are
authored; this playtest does not establish learned cooperation, processed Create
output, or an emergent courier occupation.

## What should be visible

Two identically capable citizens begin near separate sites, 32 blocks apart. One
site is a wheat buffer with a target of two; the other contains eight wheat. Site
coordinates and the buffer target are public configuration. Current inventories
and observations are private to the citizen that witnesses them. The citizen
near the empty buffer can carry its request toward the source rendezvous. A
recipient can then commit to a physical supply job using its own local source
knowledge. All transfers use the existing native hauling executor.

The expected completed cycle leaves six wheat at the source and two at the
buffer, with no active source claims. A subsequent quiet window must not start
another material job. Setting the target to zero is an explicit operator change;
stopping the controller is an explicit operator stop. Neither is a demonstration
that a learned policy independently inferred that a profession was unnecessary.

## Commands

| Command | Meaning |
| --- | --- |
| `/hearthbound-services configure-buffer <x> <y> <z> <target>` | Register the public buffer position and desired wheat stock |
| `/hearthbound-services configure-source <x> <y> <z>` | Register a public source rendezvous; this does not inspect its stock |
| `/hearthbound-services enroll <entity>` | Give a marked Sable the same service capabilities as other enrolled citizens |
| `/hearthbound-services start` | Start the explicit service controller after ownership checks |
| `/hearthbound-services set-target <x> <y> <z> <target>` | Change or withdraw an operator-defined goal; zero withdraws it |
| `/hearthbound-services stop` | Stop new service selection and use the safe cancellation/hold boundaries |
| `/hearthbound-services status` | Inspect bounded counters and current control status |
| `/hearthbound-services records <offset>` | Read a page of observed service events |

The service controller owns its enrolled citizens before the legacy colony or
follow-player path can act. A server restart does not silently re-enable it.
Unresolved native jobs remain fenced for explicit recovery rather than being
reassigned.

## Automated live acceptance

The `Need-driven Minecraft services` workflow first runs pure Java lifecycle and
evidence-admission contracts, then compiles the actual Forge mod. It boots a
fresh dedicated server and runs:

```powershell
python scripts/rcon_need_services_acceptance.py --phase live
```

That client builds its fixture in a disposable world, enrolls both real citizens,
and starts the service runtime. From that point until the completed target and
quiet window, its commands are observations only. It never teleports a worker,
forces a request handoff, assigns a haul, inserts a completion receipt, or retries
a failed behavioral attempt. The declared wall-clock guard is 240 seconds.

The client requires native inventory witnesses as well as a trace linking a
received request to the recipient's own native job and verified transfer. It
rejects duplicate jobs or completion credit, wrong ownership, missing receipts,
reversed timestamps, oversupply, held jobs, and exhausted evidence capacity.

After the completed cycle, it explicitly withdraws the target, stops services,
saves the world, and stops the server. The workflow reboots that same world and
runs:

```powershell
python scripts/rcon_need_services_acceptance.py --phase restart
```

This checks retained membership/completion counts, unchanged real inventories,
zero outstanding source claims, and no automatic dispatch while stopped. This
is a **clean stopped restart** check. It does not test a forced crash during
extraction, an unresolved cargo job across restart, pre-pickup withdrawal in a
live world, or post-pickup live cancellation. Those boundaries need separate
live evidence before broader recovery claims.

The RCON client uses the existing multipart-safe connection and requires
`HEARTHBOUND_RCON_PASSWORD`. A normal player can instead exercise the listed
in-game commands in a prepared test area. The automated setup modifies its
fixture area and is intended for the workflow's disposable world.

## Evidence and interpretation

The workflow retains build logs, both server logs, RCON transcripts, and
`run/need-service-acceptance.json`, including a failure record if the live cycle
does not finish. The test passes only when the independently observed source
decrement equals the independently observed buffer increment and the exact native
job receipts account for both units.

The service event history distinguishes a need observation, starting an option,
sending and receiving a request, claiming a unit, assigning a native job, and
verifying a transfer. Status explicitly distinguishes production credit from
these events. An information pathway is visible in this acceptance; its causal
benefit over a matched alternative is a later experiment.

The next integrated milestone is changing demand at several actual work sites,
with output attribution to real Create processing and outcome-trained service
selection. That develops the same runtime rather than returning to a new
unrelated miniature economy. See
[Need-driven service architecture](NEED_DRIVEN_SERVICE_ARCHITECTURE_V0_20.md).
