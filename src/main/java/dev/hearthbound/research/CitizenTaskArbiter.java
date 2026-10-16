package dev.hearthbound.research;

import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Minimal task ownership protocol for hierarchical jobs.
 * No Minecraft dependencies, enabling fast deterministic unit tests.
 * Ownership is exclusive and identified by a unique assignment ID.
 */
public final class CitizenTaskArbiter {
    public enum Kind { HAUL, STUDY, EXPERIMENT, SOCIAL, REST }
    public record Lease(UUID assignmentId, Kind kind, long acquiredTick) {
        public Lease {
            Objects.requireNonNull(assignmentId);
            Objects.requireNonNull(kind);
            if (acquiredTick < 0) throw new IllegalArgumentException("Negative tick");
        }
    }
    private final Map<UUID, Lease> leases = new HashMap<>();

    public synchronized Lease acquire(UUID citizen, Kind kind, long tick) {
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(kind);
        if (leases.containsKey(citizen)) throw new IllegalStateException("Task already active");
        Lease lease = new Lease(UUID.randomUUID(), kind, tick);
        leases.put(citizen, lease);
        return lease;
    }

    /** Only the exact owner may release a task, preventing stale callbacks
     * from releasing newer assignments. */
    public synchronized boolean release(UUID citizen, UUID assignmentId) {
        Lease lease = leases.get(Objects.requireNonNull(citizen));
        if (lease == null || !lease.assignmentId().equals(assignmentId)) return false;
        leases.remove(citizen);
        return true;
    }

    public synchronized Lease active(UUID citizen) { return leases.get(citizen); }

    /** Used on reload to reconstruct persisted task ownership without conflict. */
    public synchronized void restore(UUID citizen, Lease lease) {
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(lease);
        Lease previous = leases.putIfAbsent(citizen, lease);
        if (previous != null && !previous.equals(lease))
            throw new IllegalStateException("Conflicting persisted task");
    }
}
