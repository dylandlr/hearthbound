package dev.hearthbound.integration;

import java.util.UUID;
import org.apache.logging.log4j.LogManager;

/**
 * Explicit opt-in crash hook for a future isolated fault-injection CI job.
 * Never enabled by the ordinary Minecraft GameTest/production server.
 */
public final class CitizenSupplyCrashProbe {
    private CitizenSupplyCrashProbe() {}
    /**
     * Flush the actual citizen, registry and Create block entity immediately
     * before the durable attempt is created. The first JVM is then halted
     * after journal creation, with no intervening Minecraft world save.
     */
    public static void checkpointBeforeAttempt(net.minecraft.server.MinecraftServer server,
                                               UUID operation) {
        if (!"isolated-citizen-crash-test".equals(
                System.getenv("HEARTHBOUND_FAULT_TEST_ACK"))
                || !"after_attempt_before_mutation".equals(
                System.getenv("HEARTHBOUND_CITIZEN_CRASH_STAGE"))) return;
        if (!server.saveEverything(false,true,true))
            throw new IllegalStateException("Cannot save pre-attempt Minecraft world baseline");
        LogManager.getLogger().info(
                "HEARTHBOUND_FAULT_PRE_ATTEMPT_WORLD_SAVED operation={}",operation);
    }
    public static void afterDurableAttempt(UUID operation) {
        if (!"isolated-citizen-crash-test".equals(
                System.getenv("HEARTHBOUND_FAULT_TEST_ACK"))) return;
        if (!"after_attempt_before_mutation".equals(
                System.getenv("HEARTHBOUND_CITIZEN_CRASH_STAGE"))) return;
        LogManager.getLogger().error(
                "HEARTHBOUND_FAULT_INJECTION_AFTER_ATTEMPT operation={} exit=86",operation);
        // Halt deliberately bypasses shutdown hooks. Only activate in a disposable world.
        Runtime.getRuntime().halt(86);
    }
}
