# v4.4 — Minecraft-aware inventory tests belong in Minecraft

CI failure evidence:
- Run 39882857602: uninitialized Minecraft registry
- Run 39885575452: game version not initialized
- Run 39886191027: Forge networking EventBus initialization error (`NetworkEvent.<init>()`) after calling Minecraft bootstrap

These failures demonstrate that a normal JavaExec task is not an initialized Forge runtime. The JavaExec task is removed, while `testClasses` continues to compile the original Minecraft-specific test fixture.

The shipping mod now includes an operator-only `/hearthbound verify_inventory_delta` command. It runs eight actual Minecraft ItemStack assertions on a live server: empty slot, item insertion, stack increase/decrease, removal, item replacement, NBT mutation, and tagged-item count increase. A failed assertion is reported as command failure. It is *not yet executed in Minecraft*; it is a runtime verification tool, not an automatic passing CI test.

Do not count `compile-and-contract` as proving Minecraft-specific tests passed. A future Forge GameTest should invoke the same checks automatically; the dedicated-server smoke test remains EULA-gated.

No research credit or autonomous citizen learning was added.
