package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Predicate;

/** Persistent-data model; no inventory access, side effects, or reward authority. */
public final class ColonyTaskQueue {
    public enum State { QUEUED, RESERVED, ASSIGNED, DONE, HELD }
    public record Task(long id, String dimension, long source, long destination,
                       State state, UUID owner, UUID job, long assignedTick) {
        public Task {
            if (id <= 0 || dimension == null || dimension.isBlank() || source == destination
                    || state == null || assignedTick < -1)
                throw new IllegalArgumentException("Invalid colony task");
            if (state == State.QUEUED && (owner != null || job != null || assignedTick != -1))
                throw new IllegalArgumentException("Queued task cannot own a job");
            if (state != State.QUEUED && owner == null)
                throw new IllegalArgumentException("Nonqueued task requires an owner");
            if ((state == State.ASSIGNED || state == State.DONE) && (job == null || assignedTick < 0))
                throw new IllegalArgumentException("Assignment requires a physical job");
        }
    }

    /**
     * A completed motor receipt supplied by the authoritative world adapter.
     * This value does not inspect inventories or establish physical success by
     * itself; the caller must first validate the actual completed executor job.
     */
    public record Completion(UUID world, String dimension, UUID citizen, UUID job,
                             long source, long destination, long assignedTick,
                             long deliveredTick) {
        public Completion {
            Objects.requireNonNull(world);
            Objects.requireNonNull(citizen);
            Objects.requireNonNull(job);
            if (dimension == null || dimension.isBlank() || source == destination
                    || assignedTick < 0 || deliveredTick < assignedTick)
                throw new IllegalArgumentException("Invalid motor completion receipt");
        }
    }
    private final List<Task> tasks = new ArrayList<>();
    private long nextId = 1;
    public synchronized Task enqueue(String dimension, long source, long destination) {
        Task task = new Task(nextId++, dimension, source, destination, State.QUEUED, null, null, -1);
        tasks.add(task);
        return task;
    }
    /**
     * Idempotently propose a physically observed resource-transfer opportunity.
     * A held or assigned task blocks duplicates. Completed tasks permit new
     * opportunities after a later observation, but never replay the old job.
     */
    public synchronized Task propose(String dimension, long source, long destination) {
        for (Task task : tasks) {
            if (task.dimension().equals(dimension) && task.source() == source
                    && task.destination() == destination && task.state() != State.DONE)
                return task;
        }
        if (tasks.size() >= 256)
            return null; // Bounded persisted board; never evict uncertain evidence.
        return enqueue(dimension, source, destination);
    }

    public synchronized void restore(Task task) {
        Objects.requireNonNull(task);
        if (tasks.stream().anyMatch(t -> t.id() == task.id()))
            throw new IllegalArgumentException("Duplicate task id");
        tasks.add(task);
        nextId = Math.max(nextId, Math.addExact(task.id(), 1));
    }
    public synchronized Task reserve(UUID citizen, String dimension) {
        return reserve(citizen, dimension, ignored -> true);
    }
    public synchronized Task reserve(UUID citizen, String dimension, Predicate<Task> eligible) {
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(eligible);
        if (tasks.stream().anyMatch(t -> citizen.equals(t.owner()) && t.state() != State.DONE))
            return null;
        for (int i = 0; i < tasks.size(); i++) {
            Task task = tasks.get(i);
            if (task.state() != State.QUEUED || !task.dimension().equals(dimension) || !eligible.test(task))
                continue;
            Task reserved = new Task(task.id(), task.dimension(), task.source(), task.destination(),
                    State.RESERVED, citizen, null, -1);
            tasks.set(i, reserved);
            return reserved;
        }
        return null;
    }
    public synchronized Task assign(long id, UUID citizen, UUID physicalJob, long tick) {
        if (tick < 0 || physicalJob == null)
            throw new IllegalArgumentException("Invalid job assignment");
        Task current = owned(id, citizen, State.RESERVED);
        Task next = new Task(id, current.dimension(), current.source(), current.destination(),
                State.ASSIGNED, citizen, physicalJob, tick);
        replace(next);
        return next;
    }
    public synchronized Task finish(long id, UUID citizen, UUID physicalJob) {
        Task current = owned(id, citizen, State.ASSIGNED);
        if (!Objects.equals(current.job(), physicalJob))
            throw new IllegalArgumentException("Job mismatch");
        Task next = new Task(id, current.dimension(), current.source(), current.destination(),
                State.DONE, citizen, physicalJob, current.assignedTick());
        replace(next);
        return next;
    }

    /**
     * Idempotently reconcile assignment state at a physical completion boundary.
     * Valid replay of the same assignment returns the unchanged DONE task.
     * Tasks do not retain a delivery timestamp: this method checks its chronology,
     * while CitizenDecisionHistory separately retains the timestamp and rejects
     * conflicting completion-time replay. Unrelated jobs and uncertain
     * HELD/RESERVED work are never created, assigned, resumed or credited here.
     */
    public synchronized Task finishVerified(UUID world, String dimension, long now,
                                             Completion receipt) {
        Objects.requireNonNull(receipt);
        if (!receipt.world().equals(world) || !receipt.dimension().equals(dimension)
                || now < 0 || receipt.deliveredTick() > now)
            throw new IllegalArgumentException("Foreign or future motor completion");
        Task matched = null;
        for (Task task : tasks) {
            if (!receipt.job().equals(task.job())) continue;
            if (matched != null)
                throw new IllegalArgumentException("Ambiguous physical job binding");
            matched = task;
        }
        if (matched == null) return null;
        if (!matched.dimension().equals(dimension)
                || !receipt.citizen().equals(matched.owner())
                || receipt.source() != matched.source()
                || receipt.destination() != matched.destination()
                || receipt.assignedTick() != matched.assignedTick())
            throw new IllegalArgumentException("Completion differs from owned assignment");
        if (matched.state() == State.DONE) return matched;
        if (matched.state() != State.ASSIGNED) return null;
        return finish(matched.id(), receipt.citizen(), receipt.job());
    }
    public synchronized Task hold(long id, UUID citizen) {
        Task current = ownedAny(id, citizen);
        if (current.state() == State.DONE)
            throw new IllegalArgumentException("Cannot hold completed job");
        Task next = new Task(id, current.dimension(), current.source(), current.destination(),
                State.HELD, citizen, current.job(), current.assignedTick());
        replace(next);
        return next;
    }
    public synchronized List<Task> snapshot() { return List.copyOf(tasks); }
    private Task owned(long id, UUID citizen, State state) {
        Task result = ownedAny(id, citizen);
        if (result.state() != state)
            throw new IllegalStateException("Invalid task transition");
        return result;
    }
    private Task ownedAny(long id, UUID citizen) {
        return tasks.stream().filter(t -> t.id() == id && citizen.equals(t.owner()))
                .findFirst().orElseThrow(() -> new IllegalArgumentException("Unknown ownership"));
    }
    private void replace(Task next) {
        for (int i = 0; i < tasks.size(); i++) {
            if (tasks.get(i).id() == next.id()) {
                tasks.set(i, next);
                return;
            }
        }
        throw new IllegalArgumentException("Task missing");
    }
}
