package dev.hearthbound.gametest;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;

/**
 * Read-only second-JVM probe for the isolated hard-crash experiment.
 * The ordinary dev server does not run these assertions.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class CitizenCrashRestartCheck {
    private CitizenCrashRestartCheck() {}
    @SubscribeEvent
    public static void onStarted(ServerStartedEvent event) {
        if (!"isolated-citizen-crash-test".equals(
                System.getenv("HEARTHBOUND_FAULT_TEST_ACK"))
                || !"inspect_after_crash".equals(
                System.getenv("HEARTHBOUND_CITIZEN_RECOVERY_STAGE"))) return;
        var server = event.getServer();
        Path world = server.getWorldPath(LevelResource.ROOT);
        Path attempts = world.resolve("hearthbound-citizen-supply-attempts");
        Path orders = world.resolve("hearthbound-citizen-milling-workorders");
        try {
            long attemptCount = countIntents(attempts);
            long orderCount = countIntents(orders);
            if (attemptCount < 1 || orderCount < 1)
                throw new IOException("Crash world must retain both operation and attempt journals");
            // No task mutation or inventory supply is permitted by this probe.
            LogManager.getLogger().info(
                    "HEARTHBOUND_CRASH_RESTART_JOURNALS_PASS attempts={} orders={} replayed=false",
                    attemptCount, orderCount);
            server.halt(false);
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot inspect actual persisted crash world", failure);
        }
    }
    private static long countIntents(Path dir) throws IOException {
        if (!Files.isDirectory(dir)) throw new IOException("Missing journal directory: " + dir);
        try (Stream<Path> paths = Files.list(dir)) {
            return paths.filter(p -> p.getFileName().toString().endsWith(".intent"))
                    .count();
        }
    }
}
