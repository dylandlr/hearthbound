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
versions are unchanged. This fixes the empty-fallback configuration; it does not
promise that a remote repository can never fail.

The `Forge cold dependency setup` workflow runs two independent, cache-disabled
build jobs, each with one preflight invocation:

1. Normal cold resolution followed by actual Forge and test compilation.
2. A diagnostic cold build that excludes only installer-tools from every project
   Maven repository. The actual ForgeGradle helper must resolve that tool through
   the Gradle fallback, produce an artifact under the Gradle modules cache, and
   leave the original repository objects and order intact. Forge and test
   compilation then provide a compatibility check in that same build process.

The exclusion init script is used only by the diagnostic job. It does not apply
to the normal pilot or reliability jobs. There is no repeated attempt to obtain
a green result. Raw logs, the subprocess result, exact resolved plugin artifact
hashes when available, and fallback evidence are retained, including failures.
Configuration failure can prevent a Gradle evidence task from running; the
Python wrapper's invocation/result record still distinguishes that missing
evidence from successful resolution.

The build still requests a ForgeGradle version range and a MixinGradle snapshot.
Recording resolved artifact hashes makes a run inspectable; it does **not** turn
those declarations into an immutable dependency lock. The expanded study's future
execution binding must freeze actual build inputs and resolved dependencies.

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
