package dev.hearthbound.civilization;

import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.ColonyTaskQueue.Completion;
import dev.hearthbound.civilization.ColonyTaskQueue.State;
import dev.hearthbound.civilization.ColonyTaskQueue.Task;

/** Completion bookkeeping contracts; physical insertion is tested in Forge. */
public final class ColonyTaskCompletionTest {
    private static final UUID WORLD = new UUID(1, 1);
    private static final UUID CITIZEN = new UUID(2, 2);
    private static final UUID JOB = new UUID(3, 3);
    private static final String DIMENSION = "minecraft:overworld";
    private static int checks;

    private static void check(boolean condition) {
        checks++;
        if (!condition) throw new AssertionError("completion check " + checks);
    }

    private static void rejected(Runnable action) {
        checks++;
        try { action.run(); }
        catch (IllegalArgumentException | NullPointerException expected) { return; }
        throw new AssertionError("expected rejected completion " + checks);
    }

    private static ColonyTaskQueue assigned() {
        ColonyTaskQueue queue = new ColonyTaskQueue();
        Task task = queue.enqueue(DIMENSION, 10, 20);
        queue.reserve(CITIZEN, DIMENSION);
        queue.assign(task.id(), CITIZEN, JOB, 100);
        return queue;
    }

    private static Completion receipt() {
        return new Completion(WORLD, DIMENSION, CITIZEN, JOB, 10, 20, 100, 110);
    }

    private static void rejectedWithoutMutation(ColonyTaskQueue queue, Completion receipt) {
        List<Task> before = queue.snapshot();
        rejected(() -> queue.finishVerified(WORLD, DIMENSION, 110, receipt));
        check(queue.snapshot().equals(before));
    }

    public static void main(String[] args) {
        ColonyTaskQueue queue = assigned();
        // No subsequent citizen tick or new-dispatch permission is needed to
        // record the already completed motor job.
        Task completed = queue.finishVerified(WORLD, DIMENSION, 110, receipt());
        check(completed.state() == State.DONE);
        check(completed.id() == 1 && completed.job().equals(JOB));
        check(queue.snapshot().size() == 1);
        List<Task> once = queue.snapshot();
        check(queue.finishVerified(WORLD, DIMENSION, 500, receipt()) == completed);
        check(queue.snapshot().equals(once));

        // The queue owns assignment state, not immutable delivery timestamps.
        // A different in-range delivery time cannot add or mutate a DONE task;
        // the separate history must reject that conflicting receipt replay.
        check(queue.finishVerified(WORLD, DIMENSION, 111,
            new Completion(WORLD, DIMENSION, CITIZEN, JOB,
                10, 20, 100, 111)) == completed);
        check(queue.snapshot().equals(once));
        CitizenDecisionHistory history = new CitizenDecisionHistory(2);
        UUID episode = new UUID(4, 4);
        check(history.register(new CitizenDecisionHistory.Entry(1, CITIZEN, JOB,
            episode, new UUID(5, 5), new UUID(6, 6), 1, 90, 95, 100,
            -1, 10, 20, CitizenDecisionHistory.Status.ASSIGNED)));
        check(history.complete(JOB, CITIZEN, episode, 110, 10, 20));
        var historicalReceipt = history.snapshot();
        rejected(() -> history.complete(JOB, CITIZEN, episode, 111, 10, 20));
        check(history.snapshot().equals(historicalReceipt));

        // Completion imposes no lifetime job cap: the same citizen can accept
        // a new observation and finish a distinct second job.
        Task next = queue.propose(DIMENSION, 10, 20);
        check(next.id() != completed.id());
        check(queue.reserve(CITIZEN, DIMENSION).id() == next.id());
        UUID secondJob = new UUID(3, 4);
        queue.assign(next.id(), CITIZEN, secondJob, 200);
        check(queue.finishVerified(WORLD, DIMENSION, 210,
            new Completion(WORLD, DIMENSION, CITIZEN, secondJob,
                10, 20, 200, 210)).state() == State.DONE);
        check(queue.snapshot().stream().filter(t -> t.state() == State.DONE).count() == 2);
        check(queue.finishVerified(WORLD, DIMENSION, 220, receipt()).id() == completed.id());
        check(queue.snapshot().size() == 2);

        ColonyTaskQueue fresh = assigned();
        rejectedWithoutMutation(fresh, new Completion(new UUID(1, 2), DIMENSION,
            CITIZEN, JOB, 10, 20, 100, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, "minecraft:the_nether",
            CITIZEN, JOB, 10, 20, 100, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, DIMENSION,
            new UUID(2, 3), JOB, 10, 20, 100, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, DIMENSION,
            CITIZEN, JOB, 11, 20, 100, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, DIMENSION,
            CITIZEN, JOB, 10, 21, 100, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, DIMENSION,
            CITIZEN, JOB, 10, 20, 101, 110));
        rejectedWithoutMutation(fresh, new Completion(WORLD, DIMENSION,
            CITIZEN, JOB, 10, 20, 100, 111));
        rejected(() -> fresh.finishVerified(WORLD, DIMENSION, -1, receipt()));
        rejected(() -> new Completion(WORLD, DIMENSION, CITIZEN, JOB,
            10, 20, 100, 99));
        rejected(() -> new Completion(WORLD, DIMENSION, CITIZEN, JOB,
            10, 10, 100, 110));
        rejected(() -> new Completion(WORLD, DIMENSION, CITIZEN, JOB,
            10, 20, -1, 110));
        rejected(() -> new Completion(null, DIMENSION, CITIZEN, JOB,
            10, 20, 100, 110));
        rejected(() -> new Completion(WORLD, DIMENSION, CITIZEN, null,
            10, 20, 100, 110));
        check(fresh.snapshot().get(0).state() == State.ASSIGNED);

        // A real direct/operator haul cannot invent a colony assignment.
        List<Task> beforeUnknown = fresh.snapshot();
        check(fresh.finishVerified(WORLD, DIMENSION, 110,
            new Completion(WORLD, DIMENSION, CITIZEN, new UUID(9, 9),
                10, 20, 100, 110)) == null);
        check(fresh.snapshot().equals(beforeUnknown));
        ColonyTaskQueue empty = new ColonyTaskQueue();
        check(empty.finishVerified(WORLD, DIMENSION, 110, receipt()) == null);
        check(empty.snapshot().isEmpty());

        // Persisted uncertain work is never resumed or converted to DONE by
        // this observer. It retains the existing manual recovery boundary.
        fresh.hold(1, CITIZEN);
        List<Task> held = fresh.snapshot();
        check(fresh.finishVerified(WORLD, DIMENSION, 110, receipt()) == null);
        check(fresh.snapshot().equals(held));
        ColonyTaskQueue restoredHeld = new ColonyTaskQueue();
        for (Task task : held) restoredHeld.restore(task);
        check(restoredHeld.finishVerified(WORLD, DIMENSION, 110, receipt()) == null);
        check(restoredHeld.snapshot().equals(held));

        ColonyTaskQueue restoredDone = new ColonyTaskQueue();
        restoredDone.restore(completed);
        check(restoredDone.finishVerified(WORLD, DIMENSION, 110, receipt()).equals(completed));
        check(restoredDone.snapshot().size() == 1);
        rejectedWithoutMutation(restoredDone, new Completion(WORLD, DIMENSION,
            CITIZEN, JOB, 10, 20, 99, 110));

        // Malformed saved duplicate job identities fail closed before either
        // assignment is changed; list order must not select a lucky winner.
        ColonyTaskQueue ambiguous = assigned();
        ambiguous.restore(new Task(2, DIMENSION, 30, 20, State.ASSIGNED,
            new UUID(2, 4), JOB, 100));
        rejectedWithoutMutation(ambiguous, receipt());
        System.out.println("PASS " + checks + " colony completion boundary checks");
    }
}
