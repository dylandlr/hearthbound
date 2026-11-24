# Forge dependency setup and the next communication study

## Scope and preserved evidence

This revision continues the draft stack after PR #217. It changes build setup,
build evidence, prospective trial declarations, and an offline study design.
It does not change the production haul motor, the original four-citizen fixture,
the existing six-world communication pilot, or any physical success threshold.
The new source revision is a separate cohort. Earlier failures remain failures;
there are no behavioral retries or replacements.

The larger study is specified in
[communication preregistration v1](COMMUNICATION_EXPERIMENT_PREREGISTRATION_V1.md).
Its 144 planned worlds are **not scheduled by this revision**. New network and
unread-message runtime capabilities still need implementation, separate tests,
and an exact execution binding before that design can run. Learned collaboration,
LLM control, and societal emergence remain future experimental targets.

## The observed dependency failure

At source `31febdd08223b5575a09da14a51b3a036726ceb9`, the existing private
pilot's `pair-03-no-messages` job failed before starting Minecraft. The other
five planned worlds reached valid measurements; only two of the three pairs
were complete. This is an unavailable performance measurement, not a zero-output
world. Preserve the
[original run](https://github.com/dylandlr/hearthbound/actions/runs/45256833501),
[failed job](https://github.com/dylandlr/hearthbound/actions/runs/45256833501/job/137980753121),
and [artifact](https://github.com/dylandlr/hearthbound/actions/runs/45256833501/artifacts/14860016111).
The artifact ZIP's SHA-256 is
`eb3efdac40b394f98ef548d8f017d1d7b067fe59bfe8a2d96029e4217452340f`.

The earliest useful exception says that
`net.minecraftforge:installertools:1.4.4:fatjar` cannot resolve because no
repositories are defined. Subsequent mapped Forge, Create, Flywheel, Ponder,
and Registrate errors follow that failure. Both this job and a successful
sibling began with an empty Gradle user-home cache, so these records do not
establish that a warm cache masked the problem. The logs do not identify the
exact resolved ForgeGradle artifact, and they do not explain the preceding
manual Maven lookup/download miss. A network outage is not established.

The pinned upstream
[MavenArtifactDownloader source](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/common/java/net/minecraftforge/gradle/common/util/MavenArtifactDownloader.java)
matches the reported stack behavior. It separates Maven repositories, Forge's
generated repositories, and other repositories. After a manual Maven miss, its
Gradle fallback receives only the third group. With the prior project repository
set, that group is empty. The fallback temporarily clears the project repository
list and restores it only after successful resolution; a failure can therefore
also explain the subsequent mapped-dependency cascade. Matching source behavior
is not proof of the old job's exact plugin release.

## Narrow build correction and a falsifiable check

`build.gradle` adds an artifact-only Ivy view of the existing official Forge
Maven endpoint, filtered to the installer-tools module. Maven-compatible layout
preserves the existing `1.4.4:fatjar` coordinate. ForgeGradle can now retain an
eligible repository in its non-Maven fallback. Minecraft and mod dependency
versions are unchanged. ForgeGradle is pinned to the directly observed 6.0.54
release so the tested helper behavior cannot float under a version range. This
fixes the empty-fallback configuration; it does not promise that a remote
repository can never fail.

The fallback also removes and re-adds already-used repository objects. The
supported `net.minecraftforge.gradle.filter.repos=false` setting disables
ForgeGradle's repeated filter callback; `build.gradle` applies the identical
`.*_mapped_.*` exclusion once per external repository object instead. Generated
repositories retain their exemption, and IDE `DownloadSources` tasks retain
the upstream existing-only behavior. This preserves the filter rather than
removing it. The upstream
[filter implementation](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/common/java/net/minecraftforge/gradle/common/util/Utils.java)
and [supported setting](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/common/java/net/minecraftforge/gradle/common/util/EnvironmentChecks.java)
define the policy being preserved.

The `Forge cold dependency setup` workflow runs two independent, cache-disabled
build jobs, each with one preflight invocation:

1. Normal cold resolution followed by actual Forge and test compilation.
2. A diagnostic cold build that excludes only installer-tools from every project
   Maven repository. The actual ForgeGradle helper must resolve that tool through
   the Gradle fallback, produce an artifact under the Gradle modules cache, and
   leave the original repository objects and order intact. The public upstream
   content-filter inspector checks the actual filters before and after that
   helper call: mapped installer versions must remain excluded, and the ordinary
   installer must remain eligible in the Ivy fallback. Forge and test compilation
   then provide a compatibility check in that same build process.

The exclusion init script is used only by the diagnostic job. It does not apply
to the normal pilot or reliability jobs. There is no repeated attempt to obtain
a green result. Raw logs, the subprocess result, exact resolved plugin artifact
hashes when available, and fallback evidence are retained, including failures.
Configuration failure can prevent a Gradle evidence task from running; the
Python wrapper's invocation/result record still distinguishes that missing
evidence from successful resolution.

The build pins ForgeGradle 6.0.54 but still requests a MixinGradle snapshot.
Recording resolved artifact hashes makes a run inspectable; it does **not** turn
all dependencies into an immutable lock. The expanded study's future execution
binding must freeze actual build inputs and resolved dependencies.

```bash
python3 scripts/run_forge_build_preflight.py \
  --output build-evidence --log forge-preflight.log
```

Use a new output directory for each declared build. The ordinary private,
controlled-diagnostics, and reliability workflows use this wrapper and archive
its records. Their protocol fingerprints now include the build configuration
and helpers, so build changes cannot silently share an old protocol identity.
The active Minecraft compatibility workflows also trigger on the relevant
build inputs.

## Retained first build-script failure and correction

The first v0.15 source, `71b3770b1f3dcb40c3cfdf28ba63c5406bd73ca2`, passed
the 165 focused Python checks but failed actual Gradle configuration. The new
applied evidence script could not resolve its static imports of ForgeGradle's
`MavenArtifactDownloader` and `Utils`. This is a new build-script defect,
separate from the archived installer-tools dependency failure.

Both [first cold jobs](https://github.com/dylandlr/hearthbound/actions/runs/45312803215)
remain failures. Their [ordinary artifact](https://github.com/dylandlr/hearthbound/actions/runs/45312803215/artifacts/14883559244)
and [forced-fallback artifact](https://github.com/dylandlr/hearthbound/actions/runs/45312803215/artifacts/14883069793)
retain one cold attempt each, exact input/log hashes, and no successful plugin
capture or fallback verification. The [controlled trial](https://github.com/dylandlr/hearthbound/actions/runs/45312803237)
also stopped before Minecraft, with its plan and
[failed build evidence](https://github.com/dylandlr/hearthbound/actions/runs/45312803237/artifacts/14883479406)
retained. No unrun world is relabelled as a zero-output result.

The correction resolves the public helper classes lazily through the already
applied Forge plugin's classloader. It does not introduce a second copy of the
plugin. Both cold logs independently identify ForgeGradle 6.0.54 and the
MixinGradle artifact `0.7-20230803.124500-15`; the corrected revision pins that
observed ForgeGradle release. Artifact SHA-256 capture remains unavailable in
the failed revision. Corrected code receives a separate first-outcome cohort;
the earlier jobs are not rerun or overwritten.

## Retained second-source outcomes and repository-filter correction

At source `8df440c36598ecc7e5a256defae7a1e791f00ddc`, the
[ordinary cold job](https://github.com/dylandlr/hearthbound/actions/runs/45313501271/job/138174656959)
passed both `compileJava` and `compileTestJava`. Its
[artifact](https://github.com/dylandlr/hearthbound/actions/runs/45313501271/artifacts/14885086706)
has ZIP SHA-256
`5f430244fd51a60e67486c01305de15977188a4608e2fec8d5a8483c938ea417`.
The [forced-fallback job](https://github.com/dylandlr/hearthbound/actions/runs/45313501271/job/138174656589)
reached the actual helper but failed while re-adding the Ivy repository: the
upstream callback tried to mutate a content descriptor after use. Its
[failed artifact](https://github.com/dylandlr/hearthbound/actions/runs/45313501271/artifacts/14885320720)
has ZIP SHA-256
`9a301c0a4b62b7ee4c859be659943cc7d038711180bfc9034bda2310af14854c`.
Both jobs retained their single cold attempts and captured matching actual
ForgeGradle and MixinGradle artifact hashes. The idempotent filter correction
above receives a new source revision and separate first-outcome cohort.

A separate [completion-boundary job](https://github.com/dylandlr/hearthbound/actions/runs/45313501292/job/138174656487)
failed before Minecraft with `Invalid patcher dependency, could not resolve
sources: null`. Its [artifact](https://github.com/dylandlr/hearthbound/actions/runs/45313501292/artifacts/14884776162)
retains the sparse compile log (ZIP SHA-256
`1f1ff17ab81266ab426631813890d3d71532661c8dc7e47c5163020017595d7f`).
The upstream
[Patcher source lookup](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/userdev/java/net/minecraftforge/gradle/userdev/MinecraftUserRepo.java)
uses the manual-only downloader and prints the returned `File`. A null result
does not establish a missing coordinate. This path does not use the new Ivy
fallback, and the retained log does not establish its HTTP failure cause.
Neither the filter correction nor a later passing build resolves that separate
uncertainty by itself.

## Continuing the original accounting and active-haul investigation

The original five trials remain `world-01` through `world-05`, with seeds
43101–43105. The force-loaded rectangle, actor setup, 150-second fixture
observation bound, physical witnesses, accounting event definitions, and scoring
rules remain unchanged. Each job now writes an exclusive prospective plan
**before** Java/Gradle setup or compilation. The runner consumes that exact plan,
and the trusted summary requires its trial, seed, source, and protocol binding.

A valid plan with no runner result is `NOT_RUN`, with unknown accounting and
physical outcomes. It remains in the five-world denominator. A missing or
mismatched plan prevents that world's outcome from entering the assessed
frequency and prevents a passing cohort. Duplicate, unreadable, or mixed-run
declarations invalidate pooled estimation. No native world UUID, cargo witness,
or terminal score is fabricated for a build failure.

The original fixture score is frozen before the existing v2 motor observations.
The collector retains the four original decision-trace identities and records
three read-only rounds of exact-UUID motor/chunk snapshots and native field
probes. Full coverage still requires all four subjects in every round; unavailable
or removed entities are not treated as empty cargo. These diagnostics cannot
repair tasks, force actors, extend the scored window, or rescore a failed run.

The separate controlled blocked-haul/chunk-suspension fixture continues to check
that the observer distinguishes a loaded, non-ticking probe from a ticking one
and that ordinary cargo recovery and conservation still work. Demonstrating
that mechanism in a controlled probe does not establish the cause of the
archived active-haul stall. Passing worlds also do not erase the original
three-of-four or later two-of-four accounting discrepancies.

Follow the existing
[reliability protocol](COLONY_RELIABILITY_TRIALS_V0_1.md) and
[motor diagnostic protocol](HAUL_MOTOR_DIAGNOSTICS_V0_14.md) for the frozen
definitions. Report new source revisions separately, retaining all failed,
incomplete, and unrun worlds in their planned denominators.

### Observed active-carrying stall on the original fixture

The second source's original `world-04`, seed 43104, produced a physical failure
with complete motor observations. Its
[retained artifact](https://github.com/dylandlr/hearthbound/actions/runs/45313501320/artifacts/14884149409)
identifies native world `367defee-7504-4c09-be67-6b01954f9d1b`.
After the original full fixture window, the destination held three wheat, all
four sources were empty, and one worker retained one wheat and its claim.
Accounting was DONE=3 / ASSIGNED=1. The frozen result remains
`FIXTURE_ASSERTION_FAILURE`; this is distinct from the original accounting-only
event where all four items physically arrived.

Worker `737c925d-ae6d-48d7-9ca8-40f92f4ede07` was active in `TO_DEST`, loaded
in unforced chunk `(1,-1)`, with `no_ai=false` and `can_update=true`, but
`position_entity_ticking=false`. Across world ticks 3047, 3068, and 3088, its
entity tick counter stayed at 97 and its position stayed unchanged. The loaded
destination was already within the motor's reach threshold. Native probes
corroborated the same job, phase, and one-wheat cargo. All four original subjects
were observed in every diagnostic round.

The full failed-fixture transcript contains no decision-trace command because
the fixture stopped at its timeout first; all four identities were recovered
through the declared current-roster fallback. No actor was moved, frozen,
force-loaded, repaired, or rescored by the post-window diagnostic. This directly
records an active-carrying stall with absent entity ticking in this new world.
It does not retrospectively establish the cause of the older archived stall,
and the accounting-only reliability question remains open.

## Research foundation and validation boundary

[Project Sid, MultiAgentBench, MARBLE, and the PA4 readings](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md)
remain the primary foundation. This phase translates their architectural and
evaluation lessons into attributable information flow, explicit permission
graphs, inspectable failures, and world-level experimental units. Their reported
results are not Hearthbound results, and they do not select a winning topology.

Offline schema and denominator tests are separate from actual Forge compilation
and live physical acceptance. The new workflow results and artifact links must
be reviewed before claiming that this source revision passed either cold build
gate or any new world trial. The 144-world design remains a preregistration even
if all current compatibility checks pass.
