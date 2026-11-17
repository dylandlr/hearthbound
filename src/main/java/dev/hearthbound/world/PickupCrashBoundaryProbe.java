package dev.hearthbound.world;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

/**
 * External-kill synchronization for disposable Forge CI worlds ONLY.
 * No command, player, citizen, packet or policy can arm this probe.
 * The CI harness kills the RCON-owning JVM after observing a forced marker.
 *
 * Never call Runtime.halt here: even a test hook must not kill an ordinary
 * server. A missed kill times out and fails the task instead of proceeding.
 */
final class PickupCrashBoundaryProbe {
    enum Boundary {
        AFTER_INTENT, AFTER_EXTRACTION, AFTER_OUTCOME,
        AFTER_DELIVERY_INTENT, AFTER_INSERTION, AFTER_DELIVERY_RETURN
    }
    private static final String WORLD_NAME = "pickup-crash-boundary-world";
    private static final String PROPERTY = "hearthbound.ci.pickupCrashBoundary";
    private static final String ENABLED = "hearthbound.ci.disposablePickupWorld";
    private static boolean used;

    private PickupCrashBoundaryProbe() {}

    static void awaitExternalKill(ServerLevel level, UUID job, Boundary at) {
        if (!Boolean.parseBoolean(System.getProperty(ENABLED, "false"))) return;
        String requested = System.getProperty(PROPERTY, "");
        if (!at.name().equals(requested)) return;
        Path world = level.getServer().getWorldPath(LevelResource.ROOT).toAbsolutePath().normalize();
        if (world.getFileName() == null || !WORLD_NAME.equals(world.getFileName().toString()))
            throw new IllegalStateException("Refusing crash probe outside disposable CI world");
        if (used) throw new IllegalStateException("Crash probe already triggered");
        used = true;
        // Separate, fixed test-only sidecar; never used for AI observations.
        Path marker = world.getParent().resolve("pickup-crash-boundary.marker");
        byte[] payload = ("HEARTHBOUND_PICKUP_BOUNDARY " + at.name() + " job=" + job
            + " world=" + HearthboundWorldIdentity.get(level) + "\n")
            .getBytes(StandardCharsets.US_ASCII);
        try (FileChannel output = FileChannel.open(marker,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            ByteBuffer bytes = ByteBuffer.wrap(payload);
            while (bytes.hasRemaining()) output.write(bytes);
            output.force(true);
        } catch (IOException failure) {
            throw new IllegalStateException("Crash marker cannot be forced", failure);
        }
        // Keep the server thread at the exact boundary while CI kills the
        // actual JVM. A timeout aborts rather than continuing an uncertain motor.
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(90);
        while (System.nanoTime() < deadline) {
            java.util.concurrent.locks.LockSupport.parkNanos(
                java.util.concurrent.TimeUnit.MILLISECONDS.toNanos(50));
        }
        throw new IllegalStateException("Crash boundary reached but external kill was not observed");
    }
}
