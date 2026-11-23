package dev.hearthbound.civilization;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Session-local scheduling and diagnostics for incremental idle discovery.
 * The adapter supplies actual loaded-world observations; this class cannot
 * inspect inventories, move actors, authorize jobs, or award completion.
 */
public final class BoundedSourceDiscovery {
    public static final int RADIUS = 16;
    public static final int POSITION_BUDGET = 75;
    public static final int INSPECTION_BUDGET = 4;
    public static final int CADENCE_TICKS = 20;
    public static final int MAX_CITIZENS = 256;
    public static final int MAX_OBSERVATIONS = 128;
    public static final int PAGE_SIZE = 2;

    public record Point(int x, int y, int z) {}
    public record Position(double x, double y, double z) {
        public Position {
            if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z)
                    || x < Integer.MIN_VALUE + RADIUS || x > Integer.MAX_VALUE - RADIUS
                    || y < Integer.MIN_VALUE + 1 || y > Integer.MAX_VALUE - 1
                    || z < Integer.MIN_VALUE + RADIUS || z > Integer.MAX_VALUE - RADIUS)
                throw new IllegalArgumentException("Invalid observer position");
        }
        public Point block() {
            return new Point((int) Math.floor(x), (int) Math.floor(y), (int) Math.floor(z));
        }
        public double distanceSquared(Point source) {
            double dx = source.x() + 0.5 - x;
            double dy = source.y() + 0.5 - y;
            double dz = source.z() + 0.5 - z;
            return dx * dx + dy * dy + dz * dz;
        }
    }
    public record Scope(UUID world, UUID episode, String dimension, Point destination) {
        public Scope {
            Objects.requireNonNull(world);
            Objects.requireNonNull(episode);
            Objects.requireNonNull(destination);
            if (dimension == null || dimension.isBlank())
                throw new IllegalArgumentException("Missing dimension");
        }
    }
    public enum State { UNKNOWN, EMPTY, AVAILABLE }
    public enum Proposal { NONE, CREATED, EXISTING, CAPACITY_DENIED }
    public record Observation(State state, int wheat, long tick, String reason,
                              Long taskId, Proposal proposal) {
        public Observation {
            Objects.requireNonNull(state);
            Objects.requireNonNull(proposal);
            if (wheat < 0 || tick < 0 || reason == null || reason.isBlank()
                    || (state == State.AVAILABLE ? wheat == 0 : wheat != 0)
                    || (taskId != null && taskId <= 0)
                    || ((proposal == Proposal.CREATED || proposal == Proposal.EXISTING)
                        != (taskId != null))
                    || (state != State.AVAILABLE && proposal != Proposal.NONE))
                throw new IllegalArgumentException("Invalid discovery observation");
        }
    }

    /** Called only in order: current geometry, loaded, block entity, inspect. */
    public interface WorldView {
        boolean loaded(Point source);
        boolean blockEntity(Point source);
        Observation inspect(Point source);
    }
    public record Entry(long sequence, Scope scope, UUID citizen, Position observer,
                        Point source, Observation observation) {}
    public record Citizen(UUID citizen, Point anchor, Point destination, int cursor,
                          long opportunities, long probes, long inspections, long proposals,
                          int maxCycleProbes, int maxCycleInspections, long lastTick,
                          long cycles, long reanchors, int lastCycleProbes,
                          int lastCycleInspections) {}
    public record Summary(int citizens, int observations, long citizenEvictions,
                          long observationEvictions, int candidatePositions) {}

    private static final List<Point> OFFSETS = offsets();
    private static final class Cursor {
        final UUID citizen;
        Point anchor, destination;
        int cursor;
        long opportunities, probes, inspections, proposals, lastTick = -1, cycles, reanchors;
        int maxCycleProbes, maxCycleInspections, lastCycleProbes, lastCycleInspections;
        Cursor(UUID citizen) { this.citizen = citizen; }
        Citizen snapshot() {
            return new Citizen(citizen, anchor, destination, cursor, opportunities,
                probes, inspections, proposals, maxCycleProbes, maxCycleInspections,
                lastTick, cycles, reanchors, lastCycleProbes, lastCycleInspections);
        }
    }

    // Access-order is updated only during an actual opportunity, never by audit.
    private final LinkedHashMap<UUID, Cursor> citizens = new LinkedHashMap<>();
    private final ArrayDeque<Entry> observations = new ArrayDeque<>();
    private Scope context;
    private long citizenEvictions, observationEvictions, sequence;

    private static List<Point> offsets() {
        var result = new ArrayList<Point>();
        for (int x = -RADIUS; x <= RADIUS; x++)
            for (int y = -1; y <= 1; y++)
                for (int z = -RADIUS; z <= RADIUS; z++) result.add(new Point(x, y, z));
        // Visit closer horizontal positions first, deterministically. Include
        // the full box: a fixed hole around an old anchor could hide sources
        // after the citizen moves. The current near cube is excluded below.
        result.sort(Comparator.comparingInt((Point p) -> p.x() * p.x() + p.z() * p.z())
            .thenComparingInt(p -> Math.abs(p.y())).thenComparingInt(Point::y)
            .thenComparingInt(Point::x).thenComparingInt(Point::z));
        return List.copyOf(result);
    }

    private static boolean sameContext(Scope left, Scope right) {
        return left != null && left.world().equals(right.world())
            && left.episode().equals(right.episode()) && left.dimension().equals(right.dimension());
    }
    public static boolean inNearCube(Point current, Point source) {
        return Math.abs((long) source.x() - current.x()) <= 2
            && Math.abs((long) source.y() - current.y()) <= 1
            && Math.abs((long) source.z() - current.z()) <= 2;
    }
    private static boolean moved(Point current, Point anchor) {
        return Math.abs((long) current.x() - anchor.x()) > 4
            || Math.abs((long) current.z() - anchor.z()) > 4
            || Math.abs((long) current.y() - anchor.y()) > 1;
    }

    /**
     * Advance at most one incremental opportunity. Skips convey no inventory
     * knowledge. Reaching the inspection cap leaves the next position pending.
     * Returns false for duplicate/too-early calls without invoking the adapter.
     */
    public boolean advance(Scope scope, UUID citizen, Position observer, long tick,
                           WorldView view) {
        Objects.requireNonNull(scope);
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(observer);
        Objects.requireNonNull(view);
        if (tick < 0) throw new IllegalArgumentException("Negative discovery tick");
        if (!sameContext(context, scope)) {
            context = scope;
            citizens.clear();
            observations.clear();
            citizenEvictions = observationEvictions = sequence = 0;
        }
        Cursor state = citizens.get(citizen);
        if (state != null && (tick <= state.lastTick || tick - state.lastTick < CADENCE_TICKS))
            return false;
        if (state == null) {
            if (citizens.size() >= MAX_CITIZENS) {
                citizens.remove(citizens.keySet().iterator().next());
                citizenEvictions++;
            }
            state = new Cursor(citizen);
        } else citizens.remove(citizen);
        citizens.put(citizen, state);
        Point current = observer.block();
        if (state.anchor == null || !scope.destination().equals(state.destination)
                || state.cursor == OFFSETS.size() || moved(current, state.anchor)) {
            state.anchor = current;
            state.destination = scope.destination();
            state.cursor = 0;
            state.reanchors++;
        }
        state.lastTick = tick;
        state.opportunities++;
        int probes = 0, inspections = 0;
        while (probes < POSITION_BUDGET && inspections < INSPECTION_BUDGET
                && state.cursor < OFFSETS.size()) {
            Point delta = OFFSETS.get(state.cursor++);
            Point source = new Point(state.anchor.x() + delta.x(), state.anchor.y() + delta.y(),
                state.anchor.z() + delta.z());
            probes++;
            if (source.equals(scope.destination()) || inNearCube(current, source)
                    || Math.abs((long) source.y() - current.y()) > 1
                    || observer.distanceSquared(source) > (double) RADIUS * RADIUS
                    || !view.loaded(source) || !view.blockEntity(source)) continue;
            inspections++;
            Observation sensed = Objects.requireNonNull(view.inspect(source));
            if (sensed.tick() != tick)
                throw new IllegalArgumentException("Discovery must record the current observation tick");
            if (sensed.proposal() == Proposal.CREATED) state.proposals++;
            if (observations.size() >= MAX_OBSERVATIONS) {
                observations.removeFirst();
                observationEvictions++;
            }
            observations.addLast(new Entry(++sequence, scope, citizen, observer, source, sensed));
        }
        if (state.cursor == OFFSETS.size()) state.cycles++;
        state.probes += probes;
        state.inspections += inspections;
        state.lastCycleProbes = probes;
        state.lastCycleInspections = inspections;
        state.maxCycleProbes = Math.max(state.maxCycleProbes, probes);
        state.maxCycleInspections = Math.max(state.maxCycleInspections, inspections);
        return true;
    }

    public Citizen citizen(Scope scope, UUID citizen) {
        if (!sameContext(context, scope)) return null;
        Cursor cursor = citizens.get(citizen);
        return cursor == null ? null : cursor.snapshot();
    }
    public List<Entry> observations(Scope scope, UUID citizen) {
        if (!sameContext(context, scope)) return List.of();
        return observations.stream().filter(e -> e.citizen().equals(citizen)).toList();
    }
    public Summary summary(Scope scope) {
        if (!sameContext(context, scope)) return new Summary(0, 0, 0, 0, OFFSETS.size());
        return new Summary(citizens.size(), observations.size(), citizenEvictions,
            observationEvictions, OFFSETS.size());
    }
}
