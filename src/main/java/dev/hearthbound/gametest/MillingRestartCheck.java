package dev.hearthbound.gametest;

import dev.hearthbound.integration.MillingObservationSavedData;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;

/** Opt-in CI assertion, run in a second JVM against the saved GameTest world. */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class MillingRestartCheck {
    private MillingRestartCheck() {}
    private static java.io.File pendingCitizenCheck;
    private static long restartTicks;

    @SubscribeEvent
    public static void onServerStarted(ServerStartedEvent event) {
        String expectedPath = System.getenv("HEARTHBOUND_RESTART_EXPECTED");
        if (expectedPath == null || expectedPath.isBlank()) return;
        try {
            CompoundTag expected = NbtIo.readCompressed(new java.io.File(expectedPath));
            MillingObservationSavedData journal = MillingObservationSavedData.get(event.getServer());
            // The saved world now contains three genuine Create operations. The
            // original checkpoint records only the first operation's journal;
            // require its exact immutable payload rather than rejecting newer
            // observations from the separate consecutive-milling GameTest.
            var original = expected.getList("Observations", net.minecraft.nbt.Tag.TAG_COMPOUND);
            if (original.isEmpty() || original.size() > 3 || journal.snapshot().size() != 3)
                throw new IllegalStateException("Unexpected milling journal count after restart");
            for (int i = 0; i < original.size(); i++) {
                CompoundTag saved = original.getCompound(i);
                if (!saved.equals(journal.find(saved.getUUID("Id"))))
                    throw new IllegalStateException("Original milling evidence changed after restart");
            }
            CompoundTag observation = original.getCompound(0);
            CompoundTag beforeConflict = journal.save(new CompoundTag());
            if (journal.append(observation))
                throw new IllegalStateException("Duplicate accepted after restart");
            CompoundTag conflict = observation.copy();
            conflict.putString("Recipe", "hearthbound:conflicting");
            boolean rejected = false;
            try { journal.append(conflict); } catch (IllegalArgumentException expectedConflict) { rejected = true; }
            if (!rejected || !beforeConflict.equals(journal.save(new CompoundTag())))
                throw new IllegalStateException("Conflict altered persisted journal");
            MillingCheckpointFixture.verify(event.getServer(),
                    new java.io.File(new java.io.File(expectedPath).getParentFile(), "milling-machine-expected.nbt"));
            pendingCitizenCheck = new java.io.File(
                    new java.io.File(expectedPath).getParentFile(),"citizen-supply-restart-expected.nbt");
            restartTicks=0;
            LogManager.getLogger().info("HEARTHBOUND_RESTART_PASS observation={} fullPayload=true duplicatesRejected=true",
                    observation.getUUID("Id"));
            // Explicit CI mode: finish cleanly once all restart assertions pass.
            // Allow Minecraft entity chunk loading to finish before inspecting villagers.
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot read restart expectation", failure);
        }
    }
    @SubscribeEvent
    public static void afterRestartTick(net.minecraftforge.event.TickEvent.ServerTickEvent event) {
        if(event.phase!=net.minecraftforge.event.TickEvent.Phase.END
                || pendingCitizenCheck==null || ++restartTicks<80) return;
        java.io.File expected=pendingCitizenCheck;
        pendingCitizenCheck=null;
        try {
            CitizenSupplyRestartFixture.verify(event.getServer(),expected);
            org.apache.logging.log4j.LogManager.getLogger().info(
                    "HEARTHBOUND_CITIZEN_RESTART_DELAYED_CHECK_PASS ticks={}",restartTicks);
            event.getServer().halt(false);
        } catch(java.io.IOException failure) {
            throw new IllegalStateException("Citizen supply world evidence missing after entity loading",failure);
        }
    }

}
