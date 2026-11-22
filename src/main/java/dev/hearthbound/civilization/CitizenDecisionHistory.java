package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Bounded, world-scope-only research observation journal.
 * This is NOT a physical inventory transaction log, reward authority,
 * or crash-durable append-only fsynced journal.
 */
public final class CitizenDecisionHistory {
    public enum Status { ASSIGNED, PHYSICALLY_COMPLETED }

    public record Entry(long taskId, UUID citizen, UUID job, UUID episode,
                        UUID decision, UUID evidence, long revision,
                        long observedTick, long decisionTick, long assignedTick,
                        long deliveredTick, long source, long destination,
                        Status status) {
        public Entry {
            Objects.requireNonNull(citizen);
            Objects.requireNonNull(job);
            Objects.requireNonNull(episode);
            Objects.requireNonNull(decision);
            Objects.requireNonNull(evidence);
            Objects.requireNonNull(status);
            if (taskId < 1 || revision < 1 || observedTick < 0 ||
                    decisionTick < observedTick || assignedTick < decisionTick ||
                    assignedTick - observedTick > CivilizationContracts.MAX_GATHER_EVIDENCE_AGE_TICKS ||
                    source == destination) {
                throw new IllegalArgumentException("Invalid scoped decision assignment");
            }
            if (status == Status.ASSIGNED && deliveredTick != -1L)
                throw new IllegalArgumentException("Unverified job cannot have delivery tick");
            if (status == Status.PHYSICALLY_COMPLETED && deliveredTick < assignedTick)
                throw new IllegalArgumentException("Completion precedes physical assignment");
        }
    }

    private final int capacity;
    private final List<Entry> entries = new ArrayList<>();
    private final Map<UUID, Integer> jobs = new HashMap<>();
    private long deniedCapacity;

    public CitizenDecisionHistory(int capacity) {
        if (capacity < 1 || capacity > 65536)
            throw new IllegalArgumentException("Invalid history bound");
        this.capacity = capacity;
    }

    public synchronized boolean register(Entry entry) {
        if (entry.status() != Status.ASSIGNED)
            throw new IllegalArgumentException("Registration must be an assignment");
        Integer priorIndex = jobs.get(entry.job());
        if (priorIndex != null) {
            if (!entries.get(priorIndex).equals(entry))
                throw new IllegalArgumentException("Conflicting job registration");
            return true;
        }
        if (entries.stream().anyMatch(e -> e.taskId() == entry.taskId()
                && e.episode().equals(entry.episode())))
            throw new IllegalArgumentException("Task already recorded with another job");
        if (entries.size() >= capacity) {
            deniedCapacity++;
            return false;
        }
        jobs.put(entry.job(), entries.size());
        entries.add(entry);
        return true;
    }

    public synchronized boolean complete(UUID job, UUID citizen, UUID episode,
                                          long deliveredTick, long source, long destination) {
        Integer index = jobs.get(job);
        if (index == null) return false;  // Do not reconstruct missing assignments.
        Entry old = entries.get(index);
        if (!old.citizen().equals(citizen) || !old.episode().equals(episode) ||
                old.source() != source || old.destination() != destination ||
                deliveredTick < old.assignedTick())
            throw new IllegalArgumentException("Completion does not match original assignment");
        if (old.status() == Status.PHYSICALLY_COMPLETED) {
            if (old.deliveredTick() != deliveredTick)
                throw new IllegalArgumentException("Conflicting physical completion");
            return true;
        }
        entries.set(index, new Entry(old.taskId(), old.citizen(), old.job(), old.episode(),
                old.decision(), old.evidence(), old.revision(), old.observedTick(),
                old.decisionTick(), old.assignedTick(), deliveredTick,
                old.source(), old.destination(), Status.PHYSICALLY_COMPLETED));
        return true;
    }

    /** Restore a previously serialized sequence; reject contradictory history. */
    public synchronized void restore(Entry entry) {
        Objects.requireNonNull(entry);
        if (jobs.containsKey(entry.job()) ||
                entries.stream().anyMatch(e -> e.taskId() == entry.taskId()
                    && e.episode().equals(entry.episode())) ||
                entries.size() >= capacity)
            throw new IllegalArgumentException("Duplicate or over-capacity restored history");
        jobs.put(entry.job(), entries.size());
        entries.add(entry);
    }

    public synchronized List<Entry> snapshot() { return List.copyOf(entries); }
    public synchronized long deniedCapacity() { return deniedCapacity; }
    public synchronized int capacity() { return capacity; }
    public synchronized void restoreDeniedCapacity(long count) {
        if (count < 0) throw new IllegalArgumentException("Invalid dropped count");
        deniedCapacity = count;
    }
}
