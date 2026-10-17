# Hearthbound v0.7.1 — operator-specified two-job experiment

The /sable choose-work command allows a real citizen to choose between two
physical activities through the existing WorkChoicePlanner:
- HAUL: operator supplies loaded source and destination positions.
- STUDY: operator supplies a loaded book container with the explicitly marked
  Hearthbound milling primer.

## Commands

```
/sable haul-priority 1
/hearthbound library priority 4
/sable choose-work <source-x y z> <destination-x y z> <library-x y z>
/sable work-choice-inspect
```

Reverse priorities (haul 4, study 1) to test the other selection.
The citizen must be Sable, spawned via /sable spawn, within command range.
Use /hearthbound library primer to generate the known lesson book.

The selected executor is physically authoritative. A haul offer only verifies
that endpoints are loaded and distinct; actual source claims, mill reservations,
and item transfer eligibility remain guarded by SableHauling.assign and tick.
The study executor validates the marked book before accepting travel.
If an executor declines, the recorded result explains the refusal; there is
no automatic fallback to the second offer in this prototype.

## Safety notes
- Never assume every loaded haul endpoint has wheat or available inventory.
- /sable choose-work is a manually triggered development experiment.
- Automatic LibraryAutonomyTick is a separate loop; disable it during tests
  (/hearthbound library auto off) to avoid competing decision cycles.
- The HAUL path still does not use the same CitizenWorkDispatcher lease
  instance as STUDY; existing runtime interlocks prevent dual assignment.
- Do not restart a quarantined cargo delivery without operator reconciliation.
- Unknown hunger, danger and fatigue are currently zeros, *not* observations.

## Acceptance tests (not yet executed)
1. With valid wheat endpoints and primer, set HAUL=1/STUDY=4; expect HAUL_ASSIGNED.
2. Fresh citizen, reverse priorities, expect STUDY_ASSIGNED.
3. Remove book: STUDY offer is unavailable, HAUL may be selected.
4. Issue command while either job runs: expect busy rejection.
5. Break source claim or mill reservation and confirm no unauthorized delivery.
6. Inspect /sable work-choice-inspect for recorded decision/outcome.
7. Compile Forge and perform dedicated-server save/reload test.
