# Manual claim inspection and recovery

Admin/operator commands (dimension-local):
- `/hearthboundclaims count` — how many source reservations exist
- `/hearthboundclaims owner <x y z>` — show current owner UUID of that source
- `/hearthboundclaims release <x y z> <expectedOwner UUID>` — release only if current owner matches

**Manual release is dangerous.** Inspect whether the citizen is alive, whether its haul NBT contains wheat cargo, and whether source/output chests have consistent counts before releasing. A live citizen may still be carrying the wheat; releasing its source allows conflicting work. No automated cargo reconciliation exists yet.

Test plan:
1. Assign haul, inspect claim owner and count.
2. Run release with incorrect UUID: must fail without mutation.
3. Run release with matching UUID (only after independently verifying job abandonment and cargo): must succeed.
4. Stop/restart world; compare owner and count before/after a graceful save.
5. Repeat on another dimension to confirm independent claim storage.
6. Test real Minecraft commands and Forge build.

No claims are made about crash-atomicity or e2e success until tested.
