# Milling recovery decision contract

MillstoneRecoveryGate classifies durable evidence after an interrupted operation. It is not connected to the live diagnostic hook and does not issue rewards.

| Recovered evidence | Decision |
| --- | --- |
| Missing input proof or completion | Quarantine |
| Operation identity, machine, world, dimension, recipe or source mismatch | Quarantine |
| Unknown credit lookup or conflicting credit record | Quarantine |
| Complete matching operation and matching existing credit | Already credited; no candidate |
| Complete matching operation and confirmed absent credit | Candidate for atomic credit commit |

A candidate is not permission to increment a balance directly. The eventual storage adapter must insert the receipt and apply the reward in one atomic transaction keyed by the stable pre-operation ID. Two concurrent recoveries may both see ABSENT; only one transaction may commit. MATCHING means the entire accepted receipt matches, not merely its ID. Lookup failure must map to UNKNOWN.

The current post-operation observation UUID is unsuitable as this stable ID. The live journal remains diagnostic and research rewards remain disabled. Remaining integration work includes durable pre-operation identity, full item-NBT-aware receipts, machine/journal reconciliation, an atomic credit store, and actual process-kill tests at persistence boundaries.

The standalone recovery tests enumerate all partial proof/completion checkpoint combinations against every credit state, conflicting operation IDs, a complete uncredited operation, repeated recovery of an already-credited operation, and uncertain/conflicting credit lookups. These are deterministic policy tests, not a claim of power-loss durability.
