# v3.4 Create Millstone Mutation Hook

Pinned source: [Create 6.0.8 MillstoneBlockEntity](https://github.com/Creators-of-Create/Create/blob/mc1.20.1-6.0.8/src/main/java/com/simibubi/create/content/kinetics/millstone/MillstoneBlockEntity.java).

Hearthbound now defines `MillstoneProcessMixin`, with HEAD and RETURN injections around the private `process()` method. It calls `MillstoneMutationAudit.before/after` and logs `HEARTHBOUND_MILLSTONE_MUTATION` when the input count fell by exactly one. We read the actual millstone's input and output inventories immediately around the synchronous function call, without rolling recipe RNG again or changing Create's behavior.

### Important limits
- **Diagnostic only**: no validated recipe identity, world UUID, operation UUID, crash-durable journal, or research award.
- `outputs` lists only positive net per-slot increases. If a slot replaces an existing different item, the audit does not treat it as proven production.
- If Create modifies its method signature in future versions, the required mixin may fail on startup.
- The snapshot is not a durable receipt and must not be fed to `MillstoneReceiptGate` as trustworthy `InputProof`.
- Compile/package checks are distinct from runtime injection success. Verify the hook in an actual Create-powered Minecraft server.

### Acceptance test
1. Confirm Forge build and JAR archive verification are green.
2. On an EULA-accepted Forge server load the mod and Create; require `HEARTHBOUND_SERVER_READY createLoaded=true`.
3. Verify mixin startup logs have no injection failure.
4. Build and power a Create millstone. Add one wheat item.
5. Require precisely one `HEARTHBOUND_MILLSTONE_MUTATION` message associated with that physical processing event. Check observed output stacks and monitor recipes with stochastic results.
6. Retry with an invalid input; no mutation message should appear.
7. Cross-check against tick trace, then restart server and confirm no spurious credit or replay.
8. Next implementation: bind this mutation hook to a verified recipe identity, stable operation ID, world/dimension/position, server tick and atomic persist-before-reward journal.

### Current state
Implemented in draft PR #76; not yet validated via successful Forge CI for this exact commit, nor through live Minecraft gameplay.
