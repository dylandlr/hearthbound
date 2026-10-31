package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/**
 * Fail-closed evidence export readiness. This is a policy gate, not proof of disk durability.
 * Caller must supply facts from an independent, durable startup verification procedure.
 */
public final class WorldIdentityExportFence {
    public record StartupEvidence(UUID inMemoryWorld, UUID diskWorld,
            boolean identityFileVerified, boolean initializedBeforeThisStartup,
            boolean journalWorldMatches, boolean rollbackCheckPassed) {}
    public enum Status { READY, UNINITIALIZED, FILE_NOT_VERIFIED, ID_MISMATCH, JOURNAL_MISMATCH, ROLLBACK_UNVERIFIED }
    private WorldIdentityExportFence() {}

    public static Status evaluate(StartupEvidence e) {
        Objects.requireNonNull(e);
        if (e.inMemoryWorld() == null || !e.initializedBeforeThisStartup()) return Status.UNINITIALIZED;
        if (!e.identityFileVerified() || e.diskWorld() == null) return Status.FILE_NOT_VERIFIED;
        if (!e.inMemoryWorld().equals(e.diskWorld())) return Status.ID_MISMATCH;
        if (!e.journalWorldMatches()) return Status.JOURNAL_MISMATCH;
        if (!e.rollbackCheckPassed()) return Status.ROLLBACK_UNVERIFIED;
        return Status.READY;
    }

    public static void requireReady(StartupEvidence e) {
        Status status = evaluate(e);
        if (status != Status.READY) throw new IllegalStateException("Evidence export disabled: " + status);
    }
}
