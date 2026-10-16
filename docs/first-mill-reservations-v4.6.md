# First Mill v4.6 — Hearthbound-only exclusive reservations

## Baseline
At commit `1429193e`, all four Create integration workflows passed: Forge startup, powered processing, Sable's real item delivery, and SaveData restart of candidate and direct Create processing receipts.

## New code
`MillReservations` holds one saved-world millstone reservation per dimension/BlockPos, bound to a **job UUID and citizen UUID**. Assignment into a loaded Create millstone acquires the reservation before committing the job. A competing Hearthbound assignment fails closed and releases its attempted source claim. For non-mill destinations the hauling behavior is unchanged.

Direct Create `process()` receipts now require the reservation to match the linked job and citizen. Commands: `/sable mill-reservation <pos>` for read-only audit.

## Acceptance coverage added
- Existing First Mill script requires reservation identity equals the physical hauling job identity.
- A second Sable tries to haul wheat to the same millstone, and the command must reject the attempt while preserving the first job's reservation.
- After Minecraft save/stop/restart, the original reservation must still be present and matched to the same UUID.
- Existing direct process receipt and candidate records must remain present after restart.

## Explicit limitations
The current reservation prevents **Hearthbound-controlled** conflicting haul jobs. It does *not* prevent a player, hopper, Create belt, other mod, or an unrelated mechanism from inserting material. It does not lock the physical Create inventory. Consequently a direct callback plus reservation is still insufficient to prove one-citizen item provenance in a shared open world. **No technological unlock, individual learning reward, colony reward, or Outcome Ledger credit** is emitted.

Reservations intentionally do not expire automatically, even after hauling completion or restart. Operator-reviewed release, tamper detection, resource-lifecycle rules, and full physical access control must precede autonomous experiments and rewards. Crash consistency across a machine inventory and SavedData remains a separate problem. New CI runs must pass before claiming v4.6 verified.
