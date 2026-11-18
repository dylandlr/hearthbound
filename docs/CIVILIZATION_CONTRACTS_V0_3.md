# Scoped civilization decisions v0.3

This change integrates the v0.3 design's observation/decision boundary into the
existing Forge civilization dispatcher. It does not replace SableHauling,
PickupJournalBridge, source claims, or the existing recovery gates.

## Behavior

- Evidence, observations, and decisions include an episode UUID and a snapshot
  revision. Existing constructors remain available in an explicitly legacy scope.
- The live episode derives from persistent world identity, current report-session
  identity, and dimension. Restarting the server changes the episode even if game
  time or saved citizen data repeats.
- Snapshot revisions are per citizen and session-local. One citizen's counter
  does not expose another citizen's observation activity.
- Evidence IDs include the episode, citizen, target, origin tick, and revision.
  Reusing that evidence must retain its ID; forwarding/report transport is not
  implemented by this change.
- Validation binds the decision to the observation's episode/revision/tick and
  its evidence to its target. GATHER requires fresh, positive, personal DIRECT
  evidence. A later direct zero-stock observation supersedes an older positive
  observation, regardless of list order.
- Dispatch validates against the actual server tick immediately before reserving
  work. The provisional age ceiling is 20 game ticks, inclusive. This is a
  declared initial contract, not a calibrated sensing optimum.
- GATHER here means selecting the existing one-wheat haul task. Assignment does
  not extract an item. SableHauling remains responsible for navigation, local
  pickup admission, mutation, and verified completion. Travel may last longer
  than the original dispatch observation's freshness window; pickup uses the
  executor's separate physical checks rather than treating dispatch as stock
  authority.
- OBSERVE may investigate an old report or inference. It does not authorize
  inventory movement. DELIVER/COMMUNICATE decisions fail closed until complete
  operation-specific contracts exist. Current live dispatch exposes neither.
- The pure policy can choose EXPLORE when that capability is supplied; the Forge
  dispatcher still exposes GATHER/WAIT. This does not implement free-roaming
  exploration or establish communication benefit.

The source sensor retains its existing 16-block distance-based inventory access.
It is not a line-of-sight camera or a visual learning model. Operator-defined
tasks and a registered shared destination remain supplied knowledge. No new
claim of fully emergent work discovery or occupation learning is made.

## Audit evidence

Latest citizen decision metadata remains under the existing persistent key
`hearthbound.civilization.v1`, with inner schema `hearthbound.civilization.v3`.
It records episode, snapshot revision, decision and evidence IDs, evidence
origin tick and target, selected action, task, and actual haul job.

The permission-2 command `/hearthbound-colony decision-audit` counts distinct
citizens whose latest scoped decision matches a completed task in the current
server session. It checks task/job/target identities and timestamp order. It is
a read-only admin audit of current loaded citizen metadata, not a historical
receipt journal, global replay registry, reward gate, or cryptographic proof.
After restart, old decision memory is intentionally outside the new episode.

`/hearthbound-colony audit` retains the existing COLONY_V1 prefix and adds
`decision_contract=V0_3`. The four-citizen acceptance requires the existing exact
four physical wheat deliveries, released source claims, four distinct completers,
and `latest_scoped_completed_citizens=4` from the new audit.

## Validation and limits

Run the dependency-free suites with a JDK 17+ on PATH:

```powershell
python scripts/test-civilization-contracts.py
```

Local Java 17 compilation and all three civilization suites passed. The decision
contract suite reports 44 checks, including invalid target reuse, cross-episode
and same-tick revision replay, future evidence, execution-time expiration,
superseded stock, reported-versus-direct authority, fallback behavior, and old
constructor compatibility. All 24 existing standalone research-journal suites also passed, including
forced-kill storage checks. These remain storage/contract results, not live Forge
crash evidence.

Full `gradle --no-daemon compileJava compileTestJava` was attempted using verified
Gradle 8.8 and Temurin JDK 17. Dependency resolution failed before compilation:
Gradle's native connection to the configured network proxy reported
`java.net.SocketException: Network is unreachable` for plugin repositories.
The resulting top-level error was unresolved ForgeGradle `[6.0,6.2)`.
An IPv4 retry had the same result. No dependency versions or TLS checks were
changed to conceal this failure. This is distinct from the older documented
Create Maven certificate incident.

Consequently, the modified Forge adapter has not been fully compiled locally and
the new live audit/acceptance has not been run locally. GitHub CI did execute
those checks on source commit `f7d6929f35ce7d64219a1a1c0d78bc9e47274b11`:

| Check | Result | Evidence |
| --- | --- | --- |
| Actual Forge compilation | Passed | [Run 44230182062](https://github.com/dylandlr/hearthbound/actions/runs/44230182062) |
| Playtest JAR build | Passed | [Run 44230181948](https://github.com/dylandlr/hearthbound/actions/runs/44230181948) |
| Four-citizen physical colony | Passed | [Run 44230182127](https://github.com/dylandlr/hearthbound/actions/runs/44230182127) |
| Causal-outcome restart | Passed | [Run 44230182193](https://github.com/dylandlr/hearthbound/actions/runs/44230182193) |
| Dedicated-server smoke | Passed | [Run 44230181904](https://github.com/dylandlr/hearthbound/actions/runs/44230181904) |
| Pickup-belief restart | Crash mode passed; clean mode exposed a harness mismatch | [Run 44230182166](https://github.com/dylandlr/hearthbound/actions/runs/44230182166) |

The four-citizen execution log reports four observed proposals, four physical
deliveries, destination wheat exactly four, zero outstanding claims, and four
scoped citizen decisions. This is one small scripted colony fixture, not a
learned-policy result, independent-seed generalization, or complete crash-safety
proof.

The clean pickup-restart mismatch was confined to the haul's outer diagnostic
string. After restart, the existing motor intentionally replaces `No wheat
available` with its `PAUSE_EMPTY_OUTCOME` recovery-fence explanation. Original
failure/request evidence, job, phase, endpoints, and assignment remained intact.
The harness now waits for that exact same-job recovery receipt, permits only
that exact outer-string update, and compares all other haul bytes unchanged.
Nine adversarial harness tests reject changed job/phase/cargo/decision data,
wrong or duplicated errors, and nested or quoted lookalikes. The original failed
CI snapshots also satisfy this narrow comparison. A fresh live restart run is
required to validate the corrected harness end to end.

These validators compare an authoritative snapshot with a proposed decision.
They do not authenticate arbitrary external payloads, bind an old supplied
snapshot to a global current-state registry, guarantee durable operation
idempotence, or prove present stock. Any future asynchronous/networked policy
must select its snapshot from server-owned storage, reject superseded intentions,
and revalidate the current session and world preconditions before execution.

## Next gate

Complete a fresh clean/crash pickup-restart workflow with the corrected harness,
preserving the original failed run. Then expand independent-world and contention
coverage before claiming robust coordination. Add communication/exploration
controls as separate experiments; the old report-withheld-to-WAIT adapter remains
a wiring check.
