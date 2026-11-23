package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * The common scripted policy for an opt-in four-worker communication pilot.
 *
 * Each worker owns a separate KnowledgeBook. The Forge adapter must establish
 * observation ownership and validate world/session/recipient provenance before
 * admission; this class has no world, global task-board, inventory or UUID
 * access. A choice is a source hint requiring a fresh direct recheck, never
 * authority to move an item or credit a physical outcome.
 */
public final class PrivateCommunicationPolicy {
    public static final int WORKERS = 4;
    public static final int CADENCE_TICKS = 20;
    public static final int MAX_HORIZON_TICKS = 1200;
    public static final int MAX_AGE_TICKS = 200;
    public static final int MAX_SOURCES = 16;
    public static final int RADIUS = 16;
    public static final int NEAR_POSITION_BUDGET = 75;
    public static final int NEAR_INSPECTION_BUDGET = 4;
    public static final int OUTER_POSITION_BUDGET = 75;
    public static final int OUTER_INSPECTION_BUDGET = 4;
    public static final int RECHECK_BUDGET = 1;
    public static final int ASSIGNMENT_BUDGET = 1;
    public static final int SEND_BUDGET = 1;

    private PrivateCommunicationPolicy() {}

    public enum State { EMPTY, AVAILABLE }
    public enum Origin { DIRECT, REPORT }

    public record Point(int x, int y, int z) {}

    public record Position(double x, double y, double z) {
        public Position {
            if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z))
                throw new IllegalArgumentException("Nonfinite observer position");
        }
        public double distanceSquared(Point source) {
            Objects.requireNonNull(source);
            double dx = source.x() + 0.5 - x;
            double dy = source.y() + 0.5 - y;
            double dz = source.z() + 0.5 - z;
            return dx * dx + dy * dy + dz * dz;
        }
    }

    /** Report IDs identify actual private deliveries, not invented peer claims. */
    public record Knowledge(Point source, State state, int wheat, long observedTick,
                            Origin origin, String reportId) {
        public Knowledge {
            Objects.requireNonNull(source);
            Objects.requireNonNull(state);
            Objects.requireNonNull(origin);
            if (observedTick < 0 || wheat < 0
                    || (state == State.AVAILABLE ? wheat == 0 : wheat != 0)
                    || (origin == Origin.DIRECT && reportId != null)
                    || (origin == Origin.REPORT
                        && (reportId == null || reportId.isBlank() || reportId.length() > 2048)))
                throw new IllegalArgumentException("Invalid private source evidence");
        }
    }

    public record Choice(Knowledge evidence, double distanceSquared) {
        public Choice {
            Objects.requireNonNull(evidence);
            if (evidence.state() != State.AVAILABLE
                    || !Double.isFinite(distanceSquared) || distanceSquared < 0
                    || distanceSquared > RADIUS * RADIUS)
                throw new IllegalArgumentException("Ineligible source choice");
        }
        public Point source() { return evidence.source(); }
        public boolean reportCued() { return evidence.origin() == Origin.REPORT; }
        public String kind() {
            return reportCued() ? "REPORT_CUED_DIRECT_RECHECK" : "DIRECT_MEMORY_RECHECK";
        }
    }

    private static boolean eligibleAge(Knowledge knowledge, long now) {
        return now >= 0 && knowledge.observedTick() <= now
            && now - knowledge.observedTick() <= MAX_AGE_TICKS;
    }

    private static final class SourceMemory {
        Knowledge direct;
        Knowledge report;

        Knowledge latest(long now) {
            Knowledge own = direct != null && eligibleAge(direct, now) ? direct : null;
            Knowledge peer = report != null && eligibleAge(report, now) ? report : null;
            if (own == null) return peer;
            if (peer == null || own.observedTick() >= peer.observedTick()) return own;
            return peer;
        }
    }

    /**
     * Bounded private memory, with one retained direct and reported observation
     * per source. Accepted updates move that source to the FIFO tail; reads,
     * duplicate deliveries and rejected stale/future updates do not refresh it.
     * Latest observation wins across origins, including EMPTY vetoes; a direct
     * observation wins an equal-tick tie. Same-origin equal-tick updates follow
     * their actual admission order.
     */
    public static final class KnowledgeBook {
        private final LinkedHashMap<Point, SourceMemory> sources = new LinkedHashMap<>();

        public int size() { return sources.size(); }

        /** False means the evidence was not admitted or was an exact duplicate. */
        public boolean remember(Knowledge knowledge, long now) {
            Objects.requireNonNull(knowledge);
            if (now < 0) throw new IllegalArgumentException("Negative policy tick");
            if (!eligibleAge(knowledge, now)) return false;
            SourceMemory memory = sources.get(knowledge.source());
            if (memory == null) memory = new SourceMemory();
            Knowledge previous = knowledge.origin() == Origin.DIRECT ? memory.direct : memory.report;
            if (previous != null && (previous.equals(knowledge)
                    || previous.observedTick() > knowledge.observedTick())) return false;
            if (knowledge.origin() == Origin.DIRECT) memory.direct = knowledge;
            else memory.report = knowledge;
            sources.remove(knowledge.source());
            if (sources.size() >= MAX_SOURCES)
                sources.remove(sources.keySet().iterator().next());
            sources.put(knowledge.source(), memory);
            return true;
        }

        /** Current private source views; EMPTY is intentionally retained. */
        public List<Knowledge> knowledge(long now) {
            if (now < 0) throw new IllegalArgumentException("Negative policy tick");
            var result = new ArrayList<Knowledge>();
            for (SourceMemory memory : sources.values()) {
                Knowledge latest = memory.latest(now);
                if (latest != null) result.add(latest);
            }
            return List.copyOf(result);
        }

        /**
         * Only this worker's genuine direct observations, never received reports.
         * The transport additionally applies its own sender-freshness/range gates.
         */
        public List<Knowledge> ownDirect(long now) {
            if (now < 0) throw new IllegalArgumentException("Negative policy tick");
            var result = new ArrayList<Knowledge>();
            for (SourceMemory memory : sources.values())
                if (memory.direct != null && eligibleAge(memory.direct, now))
                    result.add(memory.direct);
            return List.copyOf(result);
        }

        /**
         * Choose only from admitted private evidence. Claims can exclude known
         * candidates but cannot add new source coordinates to the menu.
         */
        public Choice choose(Position observer, long now, Set<Point> claimed, Point destination) {
            Objects.requireNonNull(observer);
            Objects.requireNonNull(claimed);
            Objects.requireNonNull(destination);
            Choice best = null;
            for (Knowledge knowledge : knowledge(now)) {
                if (knowledge.state() != State.AVAILABLE
                        || knowledge.source().equals(destination)
                        || claimed.contains(knowledge.source())) continue;
                double distance = observer.distanceSquared(knowledge.source());
                if (distance > RADIUS * RADIUS) continue;
                Choice choice = new Choice(knowledge, distance);
                if (best == null || CHOICE_ORDER.compare(choice, best) < 0) best = choice;
            }
            return best;
        }
    }

    private static final Comparator<Choice> CHOICE_ORDER =
        Comparator.comparingDouble(Choice::distanceSquared)
            .thenComparingInt(c -> c.source().x())
            .thenComparingInt(c -> c.source().y())
            .thenComparingInt(c -> c.source().z());

    /** A selected hint alone can never satisfy the physical assignment gate. */
    public static boolean isCurrentPositiveRecheck(Choice choice, Knowledge observation, long now) {
        return choice != null && observation != null && now >= 0
            && choice.source().equals(observation.source())
            && observation.origin() == Origin.DIRECT
            && observation.state() == State.AVAILABLE
            && observation.wheat() > 0 && observation.observedTick() == now;
    }

    public static void validateHorizon(int horizonTicks) {
        if (horizonTicks < CADENCE_TICKS || horizonTicks > MAX_HORIZON_TICKS
                || horizonTicks % CADENCE_TICKS != 0)
            throw new IllegalArgumentException("Horizon must be 20..1200 ticks in 20-tick rounds");
    }

    /**
     * Stable slot order independent of citizen/world UUIDs. Rotation balances
     * first opportunity across each four consecutive rounds, including at long
     * seed/round boundaries without overflowing their sum.
     */
    public static List<Integer> roundOrder(long policySeed, long round) {
        if (round < 0) throw new IllegalArgumentException("Negative policy round");
        int first = (int) ((Math.floorMod(policySeed, (long) WORKERS) + round % WORKERS) % WORKERS);
        return List.of(first, (first + 1) % WORKERS, (first + 2) % WORKERS, (first + 3) % WORKERS);
    }

    public record Costs(int nearPositions, int nearInspections, int outerPositions,
                        int outerInspections, int rechecks, int assignments, int sends) {}

    /**
     * Allocate once per idle worker round. Consume before the corresponding
     * operation; refusal must not invoke a sensor, send or assignment. The
     * adapter also enforces cadence/horizon and checks the recheck result.
     */
    public static final class RoundBudget {
        private int nearPositions, nearInspections, outerPositions, outerInspections;
        private int rechecks, assignments, sends;

        public boolean tryNearPosition() {
            if (nearPositions >= NEAR_POSITION_BUDGET) return false;
            nearPositions++;
            return true;
        }
        public boolean tryNearInspection() {
            if (nearInspections >= NEAR_INSPECTION_BUDGET || nearInspections >= nearPositions)
                return false;
            nearInspections++;
            return true;
        }
        public boolean tryOuterPosition() {
            if (outerPositions >= OUTER_POSITION_BUDGET) return false;
            outerPositions++;
            return true;
        }
        public boolean tryOuterInspection() {
            if (outerInspections >= OUTER_INSPECTION_BUDGET || outerInspections >= outerPositions)
                return false;
            outerInspections++;
            return true;
        }
        public boolean tryRecheck() {
            if (rechecks >= RECHECK_BUDGET) return false;
            rechecks++;
            return true;
        }
        public boolean tryAssignment() {
            if (assignments >= ASSIGNMENT_BUDGET || assignments >= rechecks) return false;
            assignments++;
            return true;
        }
        public boolean trySend() {
            if (sends >= SEND_BUDGET) return false;
            sends++;
            return true;
        }
        public Costs snapshot() {
            return new Costs(nearPositions, nearInspections, outerPositions,
                outerInspections, rechecks, assignments, sends);
        }
    }
}
