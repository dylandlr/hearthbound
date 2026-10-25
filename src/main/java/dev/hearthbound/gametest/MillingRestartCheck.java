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
            CitizenSupplyRestartFixture.verify(event.getServer(),
                    new java.io.File(new java.io.File(expectedPath).getParentFile(),
                            "citizen-supply-restart-expected.nbt"));
            LogManager.getLogger().info("HEARTHBOUND_RESTART_PASS observation={} fullPayload=true duplicatesRejected=true",
                    observation.getUUID("Id"));
            // Explicit CI mode: finish cleanly once all restart assertions pass.
            event.getServer().halt(false);
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot read restart expectation", failure);
        }
    }
}
