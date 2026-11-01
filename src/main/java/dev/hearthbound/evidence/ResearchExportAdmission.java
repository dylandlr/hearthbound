package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;
import java.util.UUID;

/**
 * Combines physical receipt identity, verified world readiness, and startup marker
 * checks. Cannot authorize research merely because a boolean was passed as 'true'.
 * IMPORTANT: journal ownership and rollback reconciliation remain external facts.
 */
public final class ResearchExportAdmission {
    private ResearchExportAdmission() {}

    public static VerifiedMillAttribution.Claim authorize(
            Path identityMarker,
            UUID worldId,
            WorldIdentityExportFence.StartupEvidence startup,
            VerifiedMillAttribution.Proof proof) throws IOException {
        Objects.requireNonNull(identityMarker);
        Objects.requireNonNull(worldId);
        Objects.requireNonNull(startup);
        Objects.requireNonNull(proof);
        // Calling after restart is mandatory. The first successful initialization
        // returns RESTART_REQUIRED rather than enabling credits in the same process.
        WorldStartupCheckpoint.Status checkpoint =
            WorldStartupCheckpoint.verify(identityMarker, worldId, true, startup.rollbackCheckPassed());
        if (checkpoint != WorldStartupCheckpoint.Status.READY)
            throw new IllegalStateException("Identity checkpoint not ready: " + checkpoint);
        WorldIdentityExportFence.requireReady(startup);
        if (!worldId.equals(startup.inMemoryWorld()) || !worldId.equals(proof.world()))
            throw new IllegalStateException("World identity mismatch in research claim");
        return VerifiedMillAttribution.validate(proof);
    }
}
