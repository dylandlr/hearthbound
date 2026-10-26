package dev.hearthbound.integration;

import java.util.UUID;
import org.apache.logging.log4j.LogManager;

/**
 * Explicit opt-in crash hook for a future isolated fault-injection CI job.
 * Never enabled by the ordinary Minecraft GameTest/production server.
 */
public final class CitizenSupplyCrashProbe {
    private CitizenSupplyCrashProbe() {}
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
