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
            if (!expected.equals(journal.save(new CompoundTag())) || journal.snapshot().size() != 1)
                throw new IllegalStateException("Persisted milling journal differs after restart");
            CompoundTag observation = journal.snapshot().getCompound(0);
            if (journal.append(observation))
                throw new IllegalStateException("Duplicate accepted after restart");
            CompoundTag conflict = observation.copy();
            conflict.putString("Recipe", "hearthbound:conflicting");
            boolean rejected = false;
            try { journal.append(conflict); } catch (IllegalArgumentException expectedConflict) { rejected = true; }
            if (!rejected || !expected.equals(journal.save(new CompoundTag())))
                throw new IllegalStateException("Conflict altered persisted journal");
            LogManager.getLogger().info("HEARTHBOUND_RESTART_PASS observation={} fullPayload=true duplicatesRejected=true",
                    observation.getUUID("Id"));
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot read restart expectation", failure);
        }
    }
}
