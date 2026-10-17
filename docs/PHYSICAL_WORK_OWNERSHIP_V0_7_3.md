# Hearthbound v0.7.3 — Physical work ownership

CitizenWorkOwnership stores a per-citizen work kind and lease UUID under
`hearthbound.workOwnerV1`. It reconciles with the *actual persisted Minecraft
executor states* each server villager tick and before assignments. The two
physical assignment entry points (SableHauling.assign and
AutonomousLibraryStudy.assign) must be free before starting and register their
accepted assignment after physical initiation.

The record is not a replacement for haul job UUID, source claims, mill
reservations, cargo audit/quarantine or study dispatcher lease. These remain
authoritative and distinct. The record prevents two physical job kinds from
silently claiming one citizen, and recovers legacy tasks after reload.

A conflict is fail-closed: the owner is marked CONFLICT rather than throwing
repeated exceptions every tick. No automatic cargo/item reconciliation is ever
performed. Inspect Sable with `/sable work-owner`.

## Acceptance protocol (still unverified in Minecraft)
1. Fresh Sable -> FREE.
2. Assign haul -> HAUL. While active, try library travel -> denied.
3. Complete haul -> FREE. Retry library travel -> STUDY.
4. While traveling/studying, try haul -> denied before source claims are taken.
5. Complete or interrupt study -> FREE, but the separate study dispatcher must
   also release its persisted lease.
6. Restart with pre-pickup haul and mid-study; both ownership records should
   recover without creating duplicate work.
7. Restart with cargo, trigger quarantine, verify ownership remains HAUL until
   explicit safe operator reconciliation.
8. Verify conflict diagnostics and prevent re-assignment if saved state disagrees.

## Known limitations
Ownership is currently per-villager NBT rather than a world-wide registry.
No complete real-world job-board candidate discovery, personality/needs
observation, priority UI, or Forge compile verification yet. This change does
not prove that the running Minecraft mod compiles or behaves correctly.
