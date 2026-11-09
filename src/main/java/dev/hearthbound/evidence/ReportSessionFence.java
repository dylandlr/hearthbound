package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/**
 * Conservative report-choice fence, not a durable extraction journal.
 * A new server lifetime requires a new direct observation even if unsaved
 * negative NBT was lost. A delivery timestamp alone cannot renew evidence.
 */
public record ReportSessionFence(UUID world, UUID session) {
    public ReportSessionFence {
        Objects.requireNonNull(world);
        Objects.requireNonNull(session);
    }

    public boolean accepts(UUID observedWorld, UUID observedSession,
                           long observedTick, long deliveredTick, long now) {
        return world.equals(observedWorld) && session.equals(observedSession)
            && observedTick >= 0 && deliveredTick >= observedTick && now >= deliveredTick;
    }
}
