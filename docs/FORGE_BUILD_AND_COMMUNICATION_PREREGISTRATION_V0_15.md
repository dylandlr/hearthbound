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
2. A diagnostic cold build that excludes only installer-tools version 1.4.4 from
   every project Maven repository. The separate MCP tool version 1.3.2 remains
   eligible. The actual ForgeGradle helper must resolve the targeted tool through
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

## Retained third-source diagnostic scope failure

At source `d64e1ff27cf26e3d8ba030296e96ea55c3b4ce3e`, the
[forced cold job](https://github.com/dylandlr/hearthbound/actions/runs/45316093557/job/138183179292)
verified the actual fallback successfully before later compilation failed.
The separate [ordinary cold job](https://github.com/dylandlr/hearthbound/actions/runs/45316093557/job/138183179577)
passed production and test compilation; its
[artifact](https://github.com/dylandlr/hearthbound/actions/runs/45316093557/artifacts/14885194953)
retains that first outcome.
The [artifact](https://github.com/dylandlr/hearthbound/actions/runs/45316093557/artifacts/14885581847)
has ZIP SHA-256
`9e7e28257c8a2bfb3f11a2d7b79d9af4ecf9900ce276f5d9bb00ce4d955f8022`.
The installer-tools 1.4.4 artifact resolved through Gradle's non-Maven fallback;
its SHA-256 is
`3de0f0899c060b6f5aa79d4d9d79063ca9029cfefa19e792cb222782f754184d`.
All ten repository object identities and their order were restored, and all
eight external mapped-version filter tables were preserved.

The diagnostic's module-wide Maven exclusion also blocked
`net.minecraftforge:installertools:1.3.2:fatjar`. This is a separate dependency
of [MCPRuntime](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/mcp/java/net/minecraftforge/gradle/mcp/util/MCPRuntime.java),
which deliberately calls the manual-only downloader. Its missing-tool exception
preceded generated `Start.java` and mapped Forge compilation errors. Preserve
the emitted `SOURCE_COMPILATION_FAILURE` result and this independently inspected
earlier cause; the full forced build did not pass.

The fourth source narrowed the exclusion to the exact targeted 1.4.4 version,
but its added 1.3.2 eligibility assertion was too broad, as recorded below.
It also corrected future classification to require an actual project source
path to label a project compilation error; downstream generated source errors
cannot hide an explicit dependency failure. The preceding emitted classification
and failed build remain unchanged.

## Retained fourth-source positive-control assertion failure

At source `bac9cb402ae5eb7edb45dfc313ff8072c42c4ed3`, the
[forced job](https://github.com/dylandlr/hearthbound/actions/runs/45317676006/job/138188344167)
failed its new positive-control assertion before calling the actual fallback.
Its [artifact](https://github.com/dylandlr/hearthbound/actions/runs/45317676006/artifacts/14886007080)
has ZIP SHA-256
`ff601afad853074dd6fb4a423d276987496de9fce0e98cf4790d4112c8d96233`.
The actual inspector found 1.4.4 excluded from all seven Maven repositories,
and 1.3.2 eligible in five but excluded in `maven5` and `MavenRepo2`. This
artifact does not establish helper execution or full forced compilation.
The separate [ordinary cold job](https://github.com/dylandlr/hearthbound/actions/runs/45317676006/job/138188344668)
passed production and test compilation, with its
[first artifact](https://github.com/dylandlr/hearthbound/actions/runs/45317676006/artifacts/14886331361)
retained independently of the failed diagnostic.

Those two non-target exclusions are intentional upstream policy. The pinned
[UserDevPlugin](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/userdev/java/net/minecraftforge/gradle/userdev/UserDevPlugin.java)
attaches Mojang Maven and an additional Maven Central with
[Utils.filterForge](https://github.com/MinecraftForge/ForgeGradle/blob/14206fa010c92f79ccf61e3bd9bd0d1aedce9a9c/src/common/java/net/minecraftforge/gradle/common/util/Utils.java),
which excludes the whole `net.minecraftforge` group there. Requiring those
repositories to serve a Forge tool would remove a legitimate restriction.
Mapping the fourth artifact's dynamic repository names to those policies is
an inference from pinned repository creation order; that artifact recorded
names and filter results, but not public repository types and URLs.

The corrected check records public repository types and URLs. Every affected
Maven repository must exclude the targeted 1.4.4 version; the actual official
Forge **Maven** repository must permit the separate manual-only 1.3.2 lookup.
The Ivy fallback alone cannot satisfy that positive control. Every repository's
full filter table, including intentional non-target exclusions, must match
before and after the actual helper. This assertion correction has its own
source and first-outcome cohort. No earlier failure is rerun or relabelled.
The complete table must cover the mapped-policy repository list exactly, and
the forced-exclusion list must cover every actual Maven row exactly. Duplicate,
omitted, or unprobed repositories cannot satisfy the gate.

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

The completed second-source cohort retained three passing worlds, this physical
failure, and one `NOT_RUN` slot. `world-03` timed out during its single 1,200-second
dependency setup attempt; its
[archived snapshot](https://github.com/dylandlr/hearthbound/actions/runs/45313501320/artifacts/14885880107)
contains repeated Maven Central HTTP 429 responses. Minecraft never started.
Its wrapper explicitly records `log_finalized=false` and a null internal log
digest because complete Gradle daemon shutdown was not independently verified.
The ZIP checksum protects the archived bytes; it does not prove log finality.

The [retained summary](https://github.com/dylandlr/hearthbound/actions/runs/45313501320/artifacts/14886190173)
replays exactly from the frozen source. Both accounting event estimators are
0 observed / 4 assessable / 1 unknown / 5 planned. The descriptive Wilson 95%
interval among assessable worlds is 0–48.99%; all-planned missingness bounds are
0–20%. This is not a 0-of-5 observation. All four executed worlds have complete
four-citizen, three-round diagnostics; the unrun world's diagnostics stay missing.
The event definition, full fixture window, and frozen scores are unchanged.

### Preserved unavailable actor after original completion

The third source's `world-02` retains an original passing score: four physical
deliveries, DONE=4, and no claims. Its
[artifact](https://github.com/dylandlr/hearthbound/actions/runs/45316093591/artifacts/14885527504)
identifies native world `c08ad349-20bc-45c6-a96d-091a6c4507c9`. The strict
post-window motor capture is nevertheless `CAPTURE_INCOMPLETE`.

Retained citizen `b9411ab4-5b00-464c-a2d6-9e962490a4dd` was observed at world
tick 149 with `alive=true`, then at tick 170 with `alive=false`. Both observed
snapshots report a completed, inactive job and no cargo tag. At tick 190 the
exact UUID returns `NOT_LOADED_IN_DIMENSION`; all three native haul-field probes
return `No entity was found`. The archive retains 11 observed snapshots, one
unavailable snapshot, 21 valid native probes, and three unavailable probes.
The cause of death or subsequent disappearance is not established. Unavailable
observations are not empty-cargo measurements, and they do not replace the
earlier observations. The original score remains frozen while the complete
diagnostic gate correctly fails.

All five original third-source fixture scores passed. Both accounting event
estimators are 0 observed / 5 assessable / 0 unknown, with descriptive Wilson
95% interval 0–43.45%. The strict summary nevertheless fails because only four
of the five diagnostic captures are complete. Across the five worlds, the
archives contain 59 observed snapshots plus one unavailable snapshot, and 117
valid native probes plus three unavailable probes. These repeated citizen
observations are diagnostics, not independent world replicates.

A separate [third-source direct-witness job](https://github.com/dylandlr/hearthbound/actions/runs/45316093612/job/138183178850)
reached its 360-by-2-second readiness deadline while still in MCP setup, before
server readiness or RCON. Its
[sparse artifact](https://github.com/dylandlr/hearthbound/actions/runs/45316093612/artifacts/14886895407)
establishes a pre-runtime timeout; it does not establish the underlying reason
for slow or stalled setup. Later successes cannot resolve that cause by themselves.

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
