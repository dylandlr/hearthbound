package dev.hearthbound.jobs;

import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/** Server-thread ledger: both endpoints or neither. Waiting requests never own items. */
public final class StationReservations {
    public record Lease(UUID worker, String job, long from, long to) {
        public boolean touches(long station) { return from == station || to == station; }
    }
    private record Request(long from, long to, long seen) {
        boolean overlaps(long a, long b) { return from == a || from == b || to == a || to == b; }
    }
    private final Map<UUID, Lease> leases = new LinkedHashMap<>();
    private final Map<UUID, Request> waiting = new LinkedHashMap<>();

    public Lease holder(long station) {
        return leases.values().stream().filter(l -> l.touches(station)).findFirst().orElse(null);
    }
    public Lease lease(UUID worker) { return leases.get(worker); }
    public int waitingAt(long station, long now) {
        return (int) Math.min(999, waiting.values().stream()
                .filter(r -> now - r.seen() <= 120 && r.overlaps(station, station)).count());
    }
    public boolean isWaiting(UUID worker, long station, long now) {
        var request = waiting.get(worker);
        return request != null && now - request.seen() <= 120 && request.overlaps(station, station);
    }
    public Collection<Lease> leases() { return List.copyOf(leases.values()); }

    public boolean acquire(UUID worker, String job, long from, long to, long now) {
        if (from == to || job.isEmpty()) return false;
        var owned = leases.get(worker);
        if (owned != null) return owned.equals(new Lease(worker, job, from, to));
        // Only an ungranted request expires. An in-flight lease has no timer.
        waiting.entrySet().removeIf(e -> now - e.getValue().seen() > 120);
        var previous = waiting.get(worker);
        if (previous != null && (previous.from() != from || previous.to() != to)) waiting.remove(worker);
        waiting.put(worker, new Request(from, to, now)); // replacing preserves queue order
        for (var entry : waiting.entrySet()) {
            if (entry.getKey().equals(worker)) break;
            if (entry.getValue().overlaps(from, to)) return false;
        }
        if (holder(from) != null || holder(to) != null) return false;
        leases.put(worker, new Lease(worker, job, from, to));
        waiting.remove(worker);
        return true;
    }

    /** Saved leases are restored before any entity can request new work. */
    public void restore(Lease lease) {
        Objects.requireNonNull(lease.worker());
        if (lease.from() == lease.to() || lease.job().isEmpty() || leases.containsKey(lease.worker())
                || holder(lease.from()) != null || holder(lease.to()) != null)
            throw new IllegalArgumentException("Conflicting saved station reservation");
        leases.put(lease.worker(), lease);
    }
    public void cancelWaiting(UUID worker) { waiting.remove(worker); }
    public boolean release(UUID worker, String job) {
        var lease = leases.get(worker);
        return lease != null && lease.job().equals(job) && leases.remove(worker, lease);
    }
}
