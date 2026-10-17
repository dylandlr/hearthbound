# Hearthbound v0.7.0 — two-offer selection contract

## Implemented
WorkChoicePlanner builds a validated ColonyPolicy observation from independent
work offers. Offers expose IDs, task kinds, normalized priority 0..100, and
server-derived executability. The chosen proposal passes ActionGate. It does
not itself mutate Minecraft, acquire claims, or grant technology.

The regression experiment presents both HAUL and STUDY:
- Work priorities STUDY=1, HAUL=4 -> study wins.
- Work priorities HAUL=1, STUDY=4 -> haul wins.
- An unavailable study offer cannot win.
- Disabling both kinds returns no authorized work.
- A stale decision is rejected.
The CI policy-kernel workflow now runs WorkChoicePlannerTest.

## Required before enabling in-world two-job dispatch
1. Create a server-side candidate provider for *real*, player-authorized haul
   endpoints and validated marked book containers. Never guess source/destination.
2. Install one scoped dispatcher/arbiter for both executors; do not run parallel
   independent decision loops. Persist lease identities and restore them on load.
3. Ensure hauling's existing source claims, mill reservations, cargo quarantine
   and operator reconciliation are preserved. No automatic restart of quarantined
   cargo.
4. Handle lifecycle completion/interrupt explicitly and cap decision traces.
5. Confirm Forge compilation, dedicated server save/reload, and end-to-end
   two-candidate behavior in Minecraft.

This is policy-layer progress, not a claim of real Minecraft two-job autonomy.
