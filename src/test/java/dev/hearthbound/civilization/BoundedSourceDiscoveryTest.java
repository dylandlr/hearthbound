package dev.hearthbound.civilization;

import dev.hearthbound.civilization.BoundedSourceDiscovery.Entry;
import dev.hearthbound.civilization.BoundedSourceDiscovery.Observation;
import dev.hearthbound.civilization.BoundedSourceDiscovery.Point;
import dev.hearthbound.civilization.BoundedSourceDiscovery.Position;
import dev.hearthbound.civilization.BoundedSourceDiscovery.Proposal;
import dev.hearthbound.civilization.BoundedSourceDiscovery.Scope;
import dev.hearthbound.civilization.BoundedSourceDiscovery.State;
import dev.hearthbound.civilization.BoundedSourceDiscovery.WorldView;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/** Scheduling/observation boundaries only; live Forge tests verify real movement. */
public final class BoundedSourceDiscoveryTest {
    private static final UUID WORLD = new UUID(1, 1), EPISODE = new UUID(2, 2);
    private static final UUID CITIZEN = new UUID(3, 3);
    private static final Scope SCOPE = new Scope(WORLD, EPISODE, "minecraft:overworld",
        new Point(12, 0, 0));
    private static final Position ORIGIN = new Position(0.5, 0.5, 0.5);
    private static int checks;

    private static void check(boolean value, String reason) {
        checks++;
        if (!value) throw new AssertionError(reason);
    }
    private static void rejected(Runnable action) {
        checks++;
        try { action.run(); }
        catch (IllegalArgumentException | NullPointerException expected) { return; }
        throw new AssertionError("Expected rejected discovery input");
    }

    private static final class View implements WorldView {
        final Set<Point> loadedQueries = new HashSet<>(), entityQueries = new HashSet<>();
        final List<Point> inspected = new ArrayList<>();
        Position observer = ORIGIN;
        long tick;
        boolean allLoaded = true, allEntities;
        Point entity;
        State state = State.EMPTY;
        Proposal proposal = Proposal.NONE;
        Long task;
        @Override public boolean loaded(Point source) {
            if (observer.distanceSquared(source) > 256
                    || BoundedSourceDiscovery.inNearCube(observer.block(), source)
                    || Math.abs((long) source.y() - observer.block().y()) > 1)
                throw new AssertionError("Geometry must be checked before world access");
            loadedQueries.add(source);
            return allLoaded;
        }
        @Override public boolean blockEntity(Point source) {
            if (!allLoaded || !loadedQueries.contains(source))
                throw new AssertionError("Block lookup preceded loaded check");
            entityQueries.add(source);
            return allEntities || source.equals(entity);
        }
        @Override public Observation inspect(Point source) {
            if (!entityQueries.contains(source) || !(allEntities || source.equals(entity)))
                throw new AssertionError("Inspection preceded block entity check");
            inspected.add(source);
            return new Observation(state, state == State.AVAILABLE ? 1 : 0,
                tick, state == State.UNKNOWN ? "UNSUPPORTED_INVENTORY" : "OBSERVED", task, proposal);
        }
        boolean advance(BoundedSourceDiscovery scan, Scope scope, UUID citizen, long tick) {
            this.tick = tick;
            return scan.advance(scope, citizen, observer, tick, this);
        }
    }

    private static Set<Point> eligible(Position observer, Point anchor, Point destination) {
        Set<Point> expected = new HashSet<>();
        // Independent geometry oracle: a candidate must satisfy the public
        // scan envelope and the present observer's sensing boundaries.
        for (int x = anchor.x() - 16; x <= anchor.x() + 16; x++)
            for (int y = anchor.y() - 1; y <= anchor.y() + 1; y++)
                for (int z = anchor.z() - 16; z <= anchor.z() + 16; z++) {
                    Point source = new Point(x, y, z);
                    int dx = Math.abs(x - observer.block().x());
                    int dy = Math.abs(y - observer.block().y());
                    int dz = Math.abs(z - observer.block().z());
                    if (!source.equals(destination) && dy <= 1
                            && !(dx <= 2 && dy <= 1 && dz <= 2)
                            && observer.distanceSquared(source) <= 256) expected.add(source);
                }
        return expected;
    }

    private static void sparseCoverage() {
        BoundedSourceDiscovery scan = new BoundedSourceDiscovery();
        View view = new View();
        for (int i = 0; i < 44; i++) view.advance(scan, SCOPE, CITIZEN, i * 20L);
        var result = scan.citizen(SCOPE, CITIZEN);
        check(result.cycles() == 1 && result.cursor() == 3267, "Full stationary sweep must finish in44 opportunities");
        check(result.probes() == 3267 && result.maxCycleProbes() == 75, "Probe budget and total");
        check(result.opportunities() == 44 && result.inspections() == 0, "Sparse scan count");
        check(view.loadedQueries.equals(eligible(ORIGIN, ORIGIN.block(), SCOPE.destination())),
            "Every eligible stationary candidate must be considered");
        check(view.entityQueries.equals(view.loadedQueries), "Loaded candidate checks preserved");
        check(scan.observations(SCOPE, CITIZEN).isEmpty(), "Skipped positions cannot imply EMPTY");
        var snapshot = scan.citizen(SCOPE, CITIZEN);
        scan.summary(SCOPE); scan.observations(SCOPE, CITIZEN); scan.citizen(SCOPE, CITIZEN);
        check(snapshot.equals(scan.citizen(SCOPE, CITIZEN)), "Audits cannot advance/reset cursor");
        view.advance(scan, SCOPE, CITIZEN, 880);
        check(scan.citizen(SCOPE, CITIZEN).reanchors() == 2, "Reanchor on cycle wrap");
    }

    private static void denseCoverageAndRetention() {
        BoundedSourceDiscovery scan = new BoundedSourceDiscovery();
        View view = new View(); view.allEntities = true;
        for (int i = 0; i < 1000; i++) {
            view.advance(scan, SCOPE, CITIZEN, i * 20L);
            if (scan.citizen(SCOPE, CITIZEN).cycles() == 1) break;
        }
        var result = scan.citizen(SCOPE, CITIZEN);
        Set<Point> expected = eligible(ORIGIN, ORIGIN.block(), SCOPE.destination());
        check(result.cycles() == 1, "Dense sweep must terminate");
        check(result.maxCycleInspections() == 4 && result.maxCycleProbes() <= 75,
            "Both per-opportunity caps apply");
        check(new HashSet<>(view.inspected).equals(expected), "Inspection cap must not skip positions");
        check(view.inspected.size() == expected.size(), "No duplicate inspections within stationary sweep");
        check(result.inspections() == expected.size(), "Inspection accounting equals calls");
        var retained = scan.observations(SCOPE, CITIZEN);
        check(retained.size() == 128 && scan.summary(SCOPE).observations() == 128, "Record storage cap");
        check(scan.summary(SCOPE).observationEvictions() == expected.size() - 128,
            "Eviction counts preserve interpretation");
        check(retained.stream().allMatch(e -> e.observation().state() == State.EMPTY
            && e.observation().taskId() == null && e.observation().proposal() == Proposal.NONE),
            "Empty observation cannot receive task credit");
        check(retained.get(0).sequence() == expected.size() - 127L
            && retained.get(127).sequence() == expected.size(), "Stable sequence after eviction");
    }

    private static void unknownAndPositiveEvidence() {
        BoundedSourceDiscovery scan = new BoundedSourceDiscovery();
        View unloaded = new View(); unloaded.allLoaded = false;
        for (int i = 0; i < 44; i++) unloaded.advance(scan, SCOPE, CITIZEN, i * 20L);
        check(unloaded.entityQueries.isEmpty() && unloaded.inspected.isEmpty(),
            "Unloaded chunks must never be looked up or inspected");
        check(scan.observations(SCOPE, CITIZEN).isEmpty(), "Unloaded cannot become known EMPTY");

        scan = new BoundedSourceDiscovery();
        View view = new View(); view.entity = new Point(3, 0, 0); view.state = State.UNKNOWN;
        for (int i = 0; i < 44; i++) view.advance(scan, SCOPE, CITIZEN, i * 20L);
        check(scan.observations(SCOPE, CITIZEN).size() == 1
            && scan.observations(SCOPE, CITIZEN).get(0).observation().state() == State.UNKNOWN,
            "Actual unsupported inventory observation remains UNKNOWN");
        check(scan.citizen(SCOPE, CITIZEN).proposals() == 0, "Unknown is not new work");

        view.state = State.AVAILABLE; view.proposal = Proposal.CREATED; view.task = 17L;
        for (int i = 44; i < 88; i++) view.advance(scan, SCOPE, CITIZEN, i * 20L);
        var records = scan.observations(SCOPE, CITIZEN);
        Entry positive = records.get(records.size() - 1);
        check(positive.source().equals(view.entity) && positive.citizen().equals(CITIZEN)
            && positive.scope().equals(SCOPE) && positive.observer().equals(ORIGIN),
            "Observation attribution/geometry retained");
        check(positive.observation().taskId() == 17L && scan.citizen(SCOPE, CITIZEN).proposals() == 1,
            "New proposed task recorded separately");
        view.proposal = Proposal.EXISTING;
        for (int i = 88; i < 132; i++) view.advance(scan, SCOPE, CITIZEN, i * 20L);
        check(scan.citizen(SCOPE, CITIZEN).proposals() == 1, "Existing busy/queued task is not new credit");
        view.proposal = Proposal.CAPACITY_DENIED; view.task = null;
        for (int i = 132; i < 176; i++) view.advance(scan, SCOPE, CITIZEN, i * 20L);
        check(scan.citizen(SCOPE, CITIZEN).proposals() == 1
            && scan.observations(SCOPE, CITIZEN).get(3).observation().proposal() == Proposal.CAPACITY_DENIED,
            "Capacity denial is recorded without inventing task ID");
    }

    private static void movementAndCadence() {
        BoundedSourceDiscovery scan = new BoundedSourceDiscovery();
        View view = new View();
        check(view.advance(scan, SCOPE, CITIZEN, 0), "Initial opportunity");
        var initial = scan.citizen(SCOPE, CITIZEN);
        check(!view.advance(scan, SCOPE, CITIZEN, 0) && !view.advance(scan, SCOPE, CITIZEN, 19),
            "Duplicate and early retained-actor calls cannot consume more budget");
        check(initial.equals(scan.citizen(SCOPE, CITIZEN)), "Suppressed calls are nonmutating");
        view.observer = new Position(3.5, 1.5, 0.5);
        view.advance(scan, SCOPE, CITIZEN, 20);
        var moved = scan.citizen(SCOPE, CITIZEN);
        check(moved.anchor().equals(ORIGIN.block()) && moved.cursor() == 150,
            "Small movement retains sweep progress");
        check(moved.reanchors() == 1, "Small wander cannot reset each tick");
        check(!view.advance(scan, SCOPE, CITIZEN, 10), "Clock rewind cannot replay same opportunity");
        view.observer = new Position(5.5, 1.5, 0.5);
        view.advance(scan, SCOPE, CITIZEN, 40);
        check(scan.citizen(SCOPE, CITIZEN).anchor().equals(view.observer.block())
            && scan.citizen(SCOPE, CITIZEN).reanchors() == 2, "Large move reanchors");
        var changedDestination = new Scope(WORLD, EPISODE, SCOPE.dimension(), new Point(14, 0, 0));
        view.advance(scan, changedDestination, CITIZEN, 60);
        check(scan.citizen(SCOPE, CITIZEN).reanchors() == 3, "Destination changes invalidate cursor anchor");
        view.observer = new Position(5.5, 3.5, 0.5);
        view.advance(scan, changedDestination, CITIZEN, 80);
        check(scan.citizen(SCOPE, CITIZEN).reanchors() == 4, "Vertical move reanchors");

        // The old near cube is not omitted forever after a small shift. The
        // next complete sweep at the new position must include its valid cells.
        var shifted = new BoundedSourceDiscovery();
        View shiftView = new View(); shiftView.entity = new Point(0, 0, 0);
        shiftView.advance(shifted, SCOPE, CITIZEN, 0);
        shiftView.observer = new Position(3.5, 0.5, 0.5);
        for (int i = 1; i < 88; i++) shiftView.advance(shifted, SCOPE, CITIZEN, i * 20L);
        check(shiftView.inspected.contains(shiftView.entity), "No permanent hole at original near cube");
    }

    private static void sessionAndCitizenBounds() {
        BoundedSourceDiscovery scan = new BoundedSourceDiscovery();
        View view = new View();
        for (int i = 0; i < 256; i++) view.advance(scan, SCOPE, new UUID(10, i), 0);
        var first = new UUID(10, 0);
        scan.citizen(SCOPE, first); // Audit must not refresh LRU residency.
        view.advance(scan, SCOPE, new UUID(10, 256), 0);
        check(scan.summary(SCOPE).citizens() == 256 && scan.summary(SCOPE).citizenEvictions() == 1,
            "Citizen cursor bound");
        check(scan.citizen(SCOPE, first) == null, "Audit cannot change eviction order");
        view.advance(scan, SCOPE, first, 20);
        check(scan.citizen(SCOPE, first).opportunities() == 1, "Evicted counters restart with retained lifetime");
        var episode = new Scope(WORLD, new UUID(2, 3), SCOPE.dimension(), SCOPE.destination());
        check(scan.citizen(episode, first) == null && scan.summary(episode).citizens() == 0,
            "Read cannot expose foreign episode diagnostics");
        view.advance(scan, episode, CITIZEN, 0);
        check(scan.summary(episode).citizens() == 1 && scan.summary(episode).citizenEvictions() == 0,
            "New episode resets session diagnostics");
        check(scan.citizen(SCOPE, first) == null && scan.observations(SCOPE, first).isEmpty(),
            "Old episode cannot regain authority from retained data");
        var world = new Scope(new UUID(1, 2), episode.episode(), SCOPE.dimension(), SCOPE.destination());
        view.advance(scan, world, CITIZEN, 0);
        check(scan.citizen(world, CITIZEN).opportunities() == 1, "World change resets cursor");
        var dimension = new Scope(world.world(), world.episode(), "minecraft:the_nether", SCOPE.destination());
        view.advance(scan, dimension, CITIZEN, 0);
        check(scan.citizen(dimension, CITIZEN).opportunities() == 1, "Dimension change resets cursor");
    }

    private static void malformedInputs() {
        rejected(() -> new Position(Double.NaN, 0, 0));
        rejected(() -> new Position(Integer.MAX_VALUE, 0, 0));
        rejected(() -> new Scope(null, EPISODE, SCOPE.dimension(), SCOPE.destination()));
        rejected(() -> new Observation(State.EMPTY, 1, 0, "OBSERVED", null, Proposal.NONE));
        rejected(() -> new Observation(State.UNKNOWN, 0, 0, "UNKNOWN", 1L, Proposal.CREATED));
        rejected(() -> new Observation(State.AVAILABLE, 1, 0, "OBSERVED", null, Proposal.CREATED));
        rejected(() -> new Observation(State.AVAILABLE, 1, 0, "OBSERVED", 0L, Proposal.EXISTING));
        var scan = new BoundedSourceDiscovery();
        View view = new View();
        rejected(() -> scan.advance(SCOPE, CITIZEN, ORIGIN, -1, view));
    }

    public static void main(String[] args) {
        sparseCoverage();
        denseCoverageAndRetention();
        unknownAndPositiveEvidence();
        movementAndCadence();
        sessionAndCitizenBounds();
        malformedInputs();
        System.out.println("PASS " + checks + " bounded discovery contract checks");
    }
}
