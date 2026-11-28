# C14-01 seeded scenario contract, version 1

Parent: [C14-01 / #233](https://github.com/dylandlr/hearthbound/issues/233).
This implements the recovered seeded-generation requirement as a separate layer over
[delivery protocol v2](C14_EVENT_SCHEDULER_CONTRACT.md). It does not change v2 journal bytes or
reinterpret old journals. Native scope enforcement, physical sham preservation, actor isolation,
and final ticket acceptance remain open.

## Scope and immutable inputs

A configuration consists of named block-target scopes and named event rules. It is copied into
immutable sorted values before generation. Constructing with a different input ordering produces
the same canonical configuration. Duplicate identifiers or target positions are rejected rather
than silently deduplicated. Canonical file parsing is strict: reordered or otherwise noncanonical
bytes must be canonicalized through validated objects before use.

| Input | Version 1 rule |
| --- | --- |
| Seed | Integer 0 through 9223372036854775807, inclusive: a nonnegative 63-bit domain. Python booleans and floats are rejected. |
| Mode | Exactly `treatment`, `sham`, or `no_event` |
| Trial ID | Original caller identity retained in the manifest; ASCII `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` |
| Scope / rule ID | Same ASCII token contract; unique within each namespace |
| Dimension | Lowercase namespaced identifier matching `[a-z0-9_.-]+:[a-z0-9_./-]+`, at most 128 ASCII characters |
| Permitted box | Inclusive minimum and maximum positions; each axis has 1–256 logical positions |
| Position | Three signed 32-bit integer coordinates; each configured target must be inside its scope's box |
| Rule kind | `crop_failure`, `mill_failure`, or `resource_depletion` |
| Count | 1–4096 slots per rule, subject to the total cap |
| Onset | Inclusive nonnegative signed-long minimum and maximum |
| Duration | Inclusive positive signed-long minimum and maximum |
| End bound | Reject if maximum onset + maximum duration exceeds 9223372036854775807, before any draws |
| Severity | Inclusive integer range in parts per million, 0–1000000. This quantization is scenario-v1 policy. |
| Scope choices | Nonempty, unique list of existing scopes, sorted by ASCII scope ID |
| Targets per event | 1–256, no greater than the number of eligible targets in every referenced scope |

Caps are **64 scopes, 64 rules, 256 targets per scope, 4096 total planned slots, and 65536 total
selected targets across all slots**. Configuration bytes are capped at 1 MiB; manifest bytes at
16 MiB. Empty configurations are valid and still bound to mode, seed, and trial identity.

These positions are bounded **logical addresses**, not proof that Minecraft accepts their height,
world-border location, dimension, loaded state, or block type. The digests below bind configured
positions and parameters; they do not bind independently observed block state or prove harvest loss.
Native adapters must validate those conditions separately on the server thread.

Entity- and channel-scoped kinds already recognized by the generic scheduler are deliberately
unsupported by this first generator version. `specialist_loss`, `communication_failure`, and
`demand_change` require explicit typed scope contracts; they are not reinterpreted as block mutations.
Other C14 event features remain on the backlog.

## Canonical configuration bytes

Use ASCII, TAB-separated fields, LF line endings, and a final LF. Decimal encodings have no leading
zeroes, plus signs, or negative zero. Signed decimals appear only in coordinates. Identifiers are
case-sensitive. Sort scopes/rules by ASCII ID, targets numerically by `(x,y,z)`, and scope choices
by ASCII scope ID. The complete ordered grammar is:

```text
hearthbound:scenario-config:v1
SCOPES<TAB>scope_count
SCOPE<TAB>scope_id<TAB>dimension<TAB>min_x<TAB>min_y<TAB>min_z<TAB>max_x<TAB>max_y<TAB>max_z<TAB>target_count
BLOCK<TAB>x<TAB>y<TAB>z
... target_count BLOCK records for that scope; repeat for every scope ...
RULES<TAB>rule_count
RULE<TAB>rule_id<TAB>kind<TAB>count<TAB>onset_min<TAB>onset_max<TAB>duration_min<TAB>duration_max<TAB>severity_min_ppm<TAB>severity_max_ppm<TAB>targets_per_event<TAB>scope_choice_count
USE_SCOPE<TAB>scope_id
... scope_choice_count USE_SCOPE records for that rule; repeat for every rule ...
```

`<TAB>` denotes an actual tab, not those five characters. There are no ellipsis records or comments
in a canonical file. The fixture [basic.config](../tests/fixtures/event_scenarios/basic.config) is
an executable example. Counts are checked before reading their repeated records. Unknown versions,
extra fields, CR, non-ASCII bytes, trailing records, truncation, and noncanonical order fail closed.

`config_sha256` hashes these complete bytes. A scope hash is SHA-256 of
`hearthbound:scenario-scope:v1` plus LF, followed by that scope's canonical SCOPE and BLOCK records.
This includes the scope ID, dimension, full permitted box, and all eligible target positions.

## Specified deterministic draws

No host-language random generator is used. Let `H(domain, fields...)` mean SHA-256 of the ASCII
domain followed by LF, each field followed by LF, and no other bytes. Digests used as fields are
64 lowercase hex characters. Integer fields use canonical decimal notation.

1. `sampling_key = H("hearthbound:scenario-sampling:v1", config_sha256, seed)`.
2. Traverse rules in canonical ID order, then each rule's ordinal from zero through count−1.
3. For each draw, hash `H("hearthbound:scenario-draw:v1", sampling_key, rule_id, ordinal, field, attempt)`.
   Interpret the 32 digest bytes as one unsigned big-endian 256-bit integer `u`.
4. For a positive integer range width `b`, calculate `limit = 2^256 − (2^256 mod b)`. Accept `u` only
   when `u < limit`, returning `u mod b`. Otherwise increment attempt from zero. Fail after 1024
   rejected attempts; never fall back to biased modulo or another RNG. Arithmetic does not narrow
   tick or seed values to 32 bits. The draw helper supports widths through 2^63.
5. Inclusive ranges use `minimum + draw(maximum − minimum + 1)`.

The field names and operations are fixed:

| Field | Selection |
| --- | --- |
| `scope` | Uniform index into the rule's sorted scope choices |
| `onset` | Rule's inclusive onset range |
| `duration` | Rule's inclusive duration range |
| `severity` | Rule's inclusive intended severity ppm range |
| `target-0`, `target-1`, … | Partial Fisher–Yates sampling without replacement from the chosen scope's canonical targets |

For target step `i`, swap position `i` with `i + draw(target_count − i)`. Take the first requested
number of positions, then sort that selected set numerically for stable downstream inspection.
The target hash is SHA-256 of `hearthbound:scenario-targets:v1` plus LF, the scope hash plus LF,
and each selected `x<TAB>y<TAB>z<LF>` record. No weighting, target discovery, or physics sampling is implied.

## Paired modes and identities

The sampling key excludes mode and trial ID. Therefore the same config and seed produce the same
scope choices, target sets, onsets, durations, and intended severities across paired arms. Each
slot's `pair_id = H("hearthbound:scenario-pair:v1", sampling_key, rule_id, ordinal)` identifies those
shared planned choices. Changing the config changes that pairing identity.

| Mode | Planned choices | Emitted scheduler events | Meaning |
| --- | --- | --- | --- |
| `treatment` | Retained in full | Same timing, intended severity converted as `ppm / 1000000.0` to binary64 | Intended disruption parameters only |
| `sham` | Same intended choices as treatment | Same timing, effective severity zero; explicit sham mode remains in manifest | A plan for a native sham control; physical state preservation must still be verified |
| `no_event` | Same latent choices retained | Empty schedule | Explicit absence of event delivery, distinct from sham activity |

Paired plan choices do not imply identical world states, UUIDs, execution timing, or physical outcomes.
A zero-severity event alone is not a verified sham. Future adapters must check the manifest mode and
independently witness that the native sham preserves the specified state.

`context = H("hearthbound:scenario-context:v1", config_sha256, seed, mode, trial_id)`.
For each emitted event:

```text
event_id = H("hearthbound:scenario-event:v1",
             context, rule_id, ordinal, scope_sha256, target_sha256,
             onset, duration, intended_severity_ppm)
```

The 64-character hex event ID fits the unchanged scheduler-v2 token contract and cryptographically
binds the entire config, seed, mode, original trial identity, and selected scope/target values. It is
not an authentication mechanism against a writer who can replace all evidence.

## Complete manifest and enforced journal wrapper

The manifest begins with these lines, then the exact `CONFIG_BYTES` bytes of canonical configuration:

```text
hearthbound:scenario-manifest:v1
GENERATOR<TAB>sha256-counter-rejection-v1
SEED<TAB>seed
MODE<TAB>mode
TRIAL<TAB>original_trial_id
CONFIG_BYTES<TAB>configuration_byte_count
```

It continues with `CONFIG_SHA256<TAB>hash`, `CHOICES<TAB>count`, and each choice in rule/ordinal order:

```text
CHOICE<TAB>rule_id<TAB>ordinal<TAB>pair_id<TAB>kind<TAB>scope_id<TAB>scope_sha256<TAB>target_sha256<TAB>onset<TAB>duration<TAB>intended_ppm<TAB>effective_ppm_or_dash<TAB>event_id_or_dash<TAB>target_count
TARGET<TAB>x<TAB>y<TAB>z
... selected target records ...
SCHEDULE_SHA256<TAB>scheduler_v2_hash
EVENT_COUNT<TAB>emitted_event_count
```

For no-event slots, effective severity and event ID use `-`. The last two records occur once after
all choices. The full manifest's SHA-256 is exposed separately, avoiding a self-referential digest.
Parsing regenerates the complete scenario from the embedded canonical config, seed, mode, and trial,
then requires every supplied byte to equal the regenerated manifest. Output fields cannot be trusted
merely because a supplied checksum looks valid.

The enforced wrapper derives:

```text
journal_run_id = H("hearthbound:scenario-run:v1", manifest_sha256, original_trial_id)
```

Python `Scenario.create_scheduler/open_scheduler` and Java `Scenario.createScheduler/openScheduler`
pass the generated schedule and this run ID to the existing scheduler-v2 create/open methods. The
world ID remains separately bound by v2. Reopening under changed config, scope, seed, mode, or trial
fails the existing BIND check—even when both schedules are empty. The original trial ID is retained
in the manifest, rather than being lost behind the derived hash.

Scenario callers must use these wrappers and retain their exact manifest with experiment evidence.
The low-level generic scheduler API remains available for older explicit schedules; it is not a
security sandbox. `event_choice/eventChoice` maps only an emitted event ID from this scenario back to
its immutable scope and parameters; unknown/foreign IDs are rejected. There is no automatic journal
migration, physical operation, policy observation, reward, role assignment, or recovery behavior.

## Validation and research applicability

The [acceptance record](C14_SEEDED_SCENARIO_ACCEPTANCE.md) distinguishes local functional results,
strict Java 17 CI, independent review, and remaining native gates. The shared fixtures pin exact
manifest bytes and identities for seeds 0, 7, and Long.MAX_VALUE across all three modes. Tests also
cover forced rejection sampling, wide tick ranges, malformed documents, reordered inputs, bounds,
paired choices, changed scopes and empty-control journal rejection, and pending-intent recovery.

The existing [reference record](C14_EVENT_SCHEDULER_REFERENCES.md) supplies relevant identity,
intent-versus-observed-effect, and evaluation-separation principles. The SHA draw algorithm,
canonical bytes, ppm quantization, caps, and wrapper encoding are engineering choices, not results
borrowed from those papers. No new paper review or adaptation result is claimed.
