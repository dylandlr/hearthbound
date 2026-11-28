# C14-01 event scheduler contract (version 2)

Status: implementation in progress; this document does not assert native integration or acceptance.

## Scope and boundary

The scheduler delivers experiment intents. It never mutates Minecraft, supplies actor observations,
assigns occupations, grants rewards, or chooses a recovery policy. The native adapter must independently
verify effects. Scheduler correctness, physical injection, and learned adaptation are separate gates.

The initial Python v1 cursor snapshot is deliberately not migrated: it cannot establish whether a
physical effect happened. A v1 artifact requires an explicit experiment restart or external reconciliation.

## Immutable schedule

- Event IDs, world IDs, run IDs, and evidence IDs are ASCII tokens matching `[A-Za-z0-9][A-Za-z0-9._-]{0,63}`.
- Kinds: `crop_failure`, `mill_failure`, `specialist_loss`, `resource_depletion`,
  `communication_failure`, `demand_change`. New kinds require an explicit contract update.
- At most 4096 events. IDs unique. Ticks are integers 0..9223372036854775807. Duration is positive;
  onset + duration cannot overflow that range. Booleans are not integers in the Python input contract.
- Severity is a finite IEEE binary64 number in [0,1]. Normalize negative zero to positive zero.
- Intervals are half-open. Transitions sort by (tick, end before start, ASCII event ID).
- Canonical schedule bytes: ASCII `hearthbound:event-schedule:v2\n`, followed by events sorted by ID,
  each `id\tkind\tonset\tduration\tseverity_bits\n`. `severity_bits` is the 16-digit lowercase
  hexadecimal binary64 representation. Digest is SHA-256 of those bytes. Empty schedules are valid controls.
- Schedule-neutral transition key: `<schedule_sha256>:<event_id>:<start|end>`.
  Delivered intent and receipt identity: `<world_id>:<run_id>:<schedule_sha256>:<event_id>:<start|end>`.
  Binding the runtime identity prevents cross-run receipts from settling an otherwise identical schedule.

## Delivery state machine

There is one outstanding intent, and a settled prefix of the ordered transition list.

1. `poll(tick)` rejects backward clocks or an outstanding intent. If the next transition is due, it
   durably records PREPARE **before** returning the intent. Otherwise it durably advances CLOCK if needed.
2. Each returned intent records its scheduled tick and observed tick. It is executable only when these
   are equal. Every transition strictly earlier than the observed tick is missed; it must receive a
   MISSED receipt, without retroactive effects. Skipped ticks remain visible in the history.
3. `acknowledge(transition_id, outcome, evidence_id, effect_tick)` records the result before advancing the
   settled prefix. Normal outcomes: APPLIED, FAILED, MISSED. APPLIED requires an on-time intent and an
   effect tick exactly equal to its scheduled tick. FAILED requires an on-time intent and no effect tick.
   MISSED requires a late intent and no effect tick. Evidence is always required; it is an adapter claim,
   not independent proof. A FAILED receipt must not be interpreted as a guarantee of zero partial mutation.
4. After every reopen, an outstanding PREPARE is held as `recovery_required`, never reissued for execution.
   Only explicit `reconcile(...)` can settle it. Reconciliation accepts the normal outcomes plus
   NOT_APPLIED (no effect tick, external witness that the intent was not applied). It never retries a
   mutation. Unresolved physical evidence leaves the intent held and blocks later delivery.
5. Exact repeated receipts are idempotent. A different outcome, evidence, effect tick, or settlement mode
   for the same transition is a conflict. Foreign/unknown IDs and impossible histories fail closed.
6. Receipt completion permits another poll at the same tick, preserving simultaneous transition order.
   Once resumed at a later world tick, newly encountered historical transitions are MISSED.

This deliberately favors inspectable failure over silent retries. It does not implement exactly-once
Minecraft effects, automatic rollback, or a complete native crash-recovery protocol.

## Durable journal protocol

Python and Java use the same ASCII append-only journal. Create and reopen are distinct operations:
create uses exclusive creation, while reopening an empty/truncated file is an error. Take an exclusive
POSIX record lock for the file lifetime (Python `lockf`, Java `FileChannel.tryLock`). A second writer,
including another handle in the same process, must fail. Supported persistence environment: local Linux
filesystem; other filesystem/power-loss guarantees require separate validation.

Use exactly one journal descriptor per process while a scheduler is open. Even closing a separate
read-only descriptor can release POSIX process locks. Inspection uses the scheduler's immutable views;
raw-file export waits until the owner closes. The same-process inode guard covers cooperating scheduler
handles (including hard-link aliases), not unrelated file opens. Do not rename, replace, truncate, or
externally edit an active journal. These are cooperative locking guarantees, not a security boundary.
See the Java 17 [FileLock platform dependencies](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/channels/FileLock.html)
and [FileChannel force contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/channels/FileChannel.html#force(boolean)).

Each line is `sequence\tprevious_hash\top\targuments...\tchecksum\n`. Checksum is SHA-256 of all
preceding fields joined by tabs, **excluding** the final checksum and newline. Sequence starts at zero
and is contiguous. Previous hash on sequence zero is 64 zeroes; later records use the preceding checksum.

| Operation | Arguments |
| --- | --- |
| BIND (sequence zero only) | world ID, run ID, schedule SHA-256 |
| CLOCK | observed tick |
| PREPARE | next transition index, observed tick |
| ACK | transition index, outcome, effect tick or `-`, evidence ID |
| RECONCILE | transition index, outcome, effect tick or `-`, evidence ID |

All decimal encodings are canonical (no sign or leading zeroes except zero itself). Replaying RECONCILE
validates its lifecycle as a settlement of a pending intent; the recorded operation is its provenance.
Replay does not require that the historical process lifetime be reproducible from the journal.

Append and force/fsync each record before modifying in-memory state or returning an executable intent.
On initial creation, also force the parent directory before returning. Any uncertain write/force failure
poisons the open handle; it cannot continue. Reopen validates the entire sequence, hash chain, binding,
and semantic lifecycle before admitting new writes. Corrupt/torn records are rejected without truncation
or automatic repair. A checksum detects accidental damage, not malicious rewriting or rollback.

Limits: maximum 1024 bytes per line, 100000 records including BIND, 16 MiB file. Exhaustion fails closed.
Before PREPARE, reserve one additional record and 1024 bytes for its eventual ACK or RECONCILE;
capacity exhaustion must not produce an executable intent that can never be settled. This is a
conservative reservation for the maximum permitted frame, not a throughput or storage-efficiency claim.
Clock-only records are persisted only on a changed tick. Delivery uses the next transition index, not a
full timeline scan each tick. Mutation of receipts and schedule data through returned views is forbidden.

Python journal handles and their process locks must not be inherited for use after `fork`. The API
rejects inherited handles before taking their copied mutexes and rejects journal creation/reopen in a
forked copy of the imported module. Such a child must exec before using the scheduler. A subprocess
that execs a fresh Python or Java runtime is supported and covered by cross-process tests.

## Required validation

Boundary/order/input tests; empty controls; overlap and compound events; skipped-tick non-execution;
restart before/after intent and receipt; exact and conflicting duplicate receipts; foreign bindings;
torn/corrupt/semantically impossible logs; injected append/force failure; process termination at the
intent/effect/receipt boundaries; writer exclusion; shared Java/Python digest, delivery, and journal replay.

Native Forge compilation is a separate compatibility check. Physical injection and actor information
isolation need a future native adapter and live-world evidence before C14-01 can close.
