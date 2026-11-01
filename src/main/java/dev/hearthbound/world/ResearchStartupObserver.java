package dev.hearthbound.world;

import dev.hearthbound.evidence.WorldStartupCheckpoint;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Real Forge server lifecycle entry point; strictly diagnostics-only.
 * Until journal ownership and rollback proofs exist, export remains disabled.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ResearchStartupObserver {
    private static final Logger LOG = LogManager.getLogger("HearthboundResearchStartup");
    private static volatile String status = "SERVER_NOT_STARTED";
    private ResearchStartupObserver() {}
    public static String status() { return status; }

    @SubscribeEvent
    public static void started(ServerStartedEvent event) {
        MinecraftServer server = event.getServer();
        try {
            var overworld = server.getLevel(Level.OVERWORLD);
            if (overworld == null) throw new IllegalStateException("overworld unavailable");
            UUID world = HearthboundWorldIdentity.get(overworld);
            Path data = server.getWorldPath(LevelResource.ROOT).resolve("data");
            Path checkpoint = data.resolve("hearthbound-world.identity");
            // Future journal files are checked only to prevent silently creating a
            // fresh identity when old research data may exist. Never claim READY.
            boolean journalsExist = Files.exists(data.resolve("hearthbound-research-inbox.bin"))
                || Files.exists(data.resolve("hearthbound-research-rewards.bin"));
            WorldStartupCheckpoint.Status marker =
                WorldStartupCheckpoint.verify(checkpoint, world, journalsExist, false);
            status = "EXPORT_DISABLED checkpoint=" + marker.name()
                + " journalReconciliation=NOT_IMPLEMENTED";
            LOG.warn("HEARTHBOUND_RESEARCH_STARTUP {} world={}", status, world);
        } catch (Exception failure) {
            status = "EXPORT_DISABLED startupFailure=" + failure.getClass().getSimpleName();
            LOG.error("HEARTHBOUND_RESEARCH_STARTUP_DENIED", failure);
        }
    }

    @SubscribeEvent
    public static void stopping(ServerStoppingEvent event) {
        status = "SERVER_STOPPING_EXPORT_DISABLED";
    }
}
