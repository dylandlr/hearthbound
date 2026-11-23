package dev.hearthbound.civilization;

import dev.hearthbound.civilization.PrivateCommunicationPolicy.Choice;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Knowledge;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.KnowledgeBook;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Origin;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Point;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Position;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.RoundBudget;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.State;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Pure boundaries only; the live Forge fixture must establish physical outcomes. */
public final class PrivateCommunicationPolicyTest {
    private static final Position OBSERVER = new Position(0.5, 0.5, 0.5);
    private static final Point DESTINATION = new Point(0, 0, 8);
    private static int checks;

    private static void check(boolean value, String reason) {
        checks++;
        if (!value) throw new AssertionError(reason);
    }
    private static void rejected(Runnable action) {
        checks++;
        try { action.run(); }
        catch (IllegalArgumentException | NullPointerException expected) { return; }
        throw new AssertionError("Expected rejected policy input");
    }
    private static Knowledge known(Point source, State state, long tick, Origin origin) {
        return new Knowledge(source, state, state == State.AVAILABLE ? 3 : 0, tick,
            origin, origin == Origin.REPORT ? "delivered:" + source + ":" + tick + ":" + state : null);
    }
    private static Choice choose(KnowledgeBook book, long now) {
        return book.choose(OBSERVER, now, Set.of(), DESTINATION);
    }

    private static void privateSourcesAndNoForwarding() {
        Point source = new Point(2, 0, 0);
        KnowledgeBook sender = new KnowledgeBook(), isolated = new KnowledgeBook();
        sender.remember(known(source, State.AVAILABLE, 100, Origin.DIRECT), 100);
        check(choose(sender, 100).source().equals(source), "Own observation supports isolated action");
        check(choose(isolated, 100) == null, "Another worker's source is not a private candidate");
        check(isolated.choose(OBSERVER, 100, Set.of(source), DESTINATION) == null,
            "A shared claim coordinate cannot introduce a source");
        Knowledge report = known(source, State.AVAILABLE, 100, Origin.REPORT);
        isolated.remember(report, 100);
        Choice cued = choose(isolated, 100);
        check(cued.reportCued() && cued.evidence().equals(report)
            && cued.kind().equals("REPORT_CUED_DIRECT_RECHECK"), "Actual report identifies the cue");
        check(isolated.ownDirect(100).isEmpty(), "Received report cannot become outgoing direct evidence");
        isolated.remember(known(source, State.EMPTY, 101, Origin.REPORT), 101);
        check(choose(isolated, 101) == null && choose(sender, 101) != null,
            "Recipient updates do not mutate another worker's private knowledge");
        sender.remember(known(source, State.EMPTY, 102, Origin.REPORT), 102);
        check(choose(sender, 102) == null, "Newer report can veto older own availability");
        check(sender.ownDirect(102).size() == 1
            && sender.ownDirect(102).get(0).origin() == Origin.DIRECT
            && sender.ownDirect(102).get(0).observedTick() == 100,
            "Own-direct export preserves the actual observation, never rewrites testimony");
        check(sender.knowledge(303).isEmpty() && sender.ownDirect(301).isEmpty(),
            "Both private views and outgoing own observations expire");
    }

    private static void commonAgeAndEmptyVeto() {
        Point source = new Point(2, 0, 0);
        for (Origin origin : Origin.values()) {
            KnowledgeBook book = new KnowledgeBook();
            check(book.remember(known(source, State.AVAILABLE, 100, origin), 300),
                "Both evidence kinds admit age200");
            check(choose(book, 300) != null && choose(book, 301) == null,
                "Both evidence kinds share the inclusive200-tick choice boundary");
            check(!book.remember(known(new Point(3, 0, 0), State.AVAILABLE, 99, origin), 300),
                "Stale admission excluded");
            check(!book.remember(known(new Point(4, 0, 0), State.AVAILABLE, 301, origin), 300),
                "Future admission excluded");
            check(book.size() == 1, "Invalid evidence cannot occupy private memory");
        }
        for (Origin oldOrigin : Origin.values()) {
            for (Origin newOrigin : Origin.values()) {
                KnowledgeBook book = new KnowledgeBook();
                book.remember(known(source, State.AVAILABLE, 100, oldOrigin), 100);
                book.remember(known(source, State.EMPTY, 101, newOrigin), 101);
                check(choose(book, 101) == null && book.knowledge(101).get(0).state() == State.EMPTY,
                    "Latest EMPTY veto applies to every origin pairing");
                check(!book.remember(known(source, State.AVAILABLE, 500, newOrigin), 102)
                    && choose(book, 102) == null, "Future evidence cannot undo a known EMPTY veto");
            }
        }
        for (boolean directEmpty : List.of(false, true)) {
            for (boolean directFirst : List.of(false, true)) {
                Knowledge direct = known(source, directEmpty ? State.EMPTY : State.AVAILABLE,
                    100, Origin.DIRECT);
                Knowledge report = known(source, directEmpty ? State.AVAILABLE : State.EMPTY,
                    100, Origin.REPORT);
                KnowledgeBook book = new KnowledgeBook();
                book.remember(directFirst ? direct : report, 100);
                book.remember(directFirst ? report : direct, 100);
                check(book.knowledge(100).equals(List.of(direct)),
                    "Equal-tick direct preference is independent of admission order");
                check((choose(book, 100) == null) == directEmpty,
                    "Equal-tick preference includes direct EMPTY");
            }
        }
        KnowledgeBook book = new KnowledgeBook();
        book.remember(known(source, State.EMPTY, 101, Origin.DIRECT), 101);
        check(!book.remember(known(source, State.AVAILABLE, 100, Origin.DIRECT), 101)
            && choose(book, 101) == null, "Older same-origin observation cannot revive a source");
        book.remember(known(source, State.AVAILABLE, 102, Origin.REPORT), 102);
        check(choose(book, 102).reportCued(), "A genuinely newer positive observation may supersede EMPTY");
    }

    private static void geometryClaimsAndStableTies() {
        KnowledgeBook book = new KnowledgeBook();
        Point x = new Point(-1, 0, 0), y = new Point(0, -1, 0), z = new Point(0, 0, -1);
        // Deliberately insert in reverse lexicographic order.
        for (Point source : List.of(z, y, x))
            book.remember(known(source, State.AVAILABLE, 100, Origin.DIRECT), 100);
        check(choose(book, 100).source().equals(x), "Equal-distance ties use stable xyz ordering");
        check(book.choose(OBSERVER, 100, Set.of(x), DESTINATION).source().equals(y),
            "A claim excludes only its known source");
        check(book.choose(OBSERVER, 100, Set.of(x, y), DESTINATION).source().equals(z),
            "Remaining coordinate tie is deterministic");
        check(book.choose(OBSERVER, 100, Set.of(x, y, z), DESTINATION) == null,
            "All-known-claimed menu abstains");
        book.remember(new Knowledge(new Point(5, 0, 0), State.AVAILABLE, 1000,
            100, Origin.REPORT, "large-stock"), 100);
        check(choose(book, 100).source().equals(x), "Common nearest-source policy is not stock weighted");

        book = new KnowledgeBook();
        Point boundary = new Point(16, 0, 0), outside = new Point(17, 0, 0);
        book.remember(known(outside, State.AVAILABLE, 100, Origin.REPORT), 100);
        check(choose(book, 100) == null, "Out-of-sphere report is not actionable");
        book.remember(known(boundary, State.AVAILABLE, 100, Origin.REPORT), 100);
        check(choose(book, 100).distanceSquared() == 256, "Sensing sphere includes its16-block boundary");
        book.remember(known(DESTINATION, State.AVAILABLE, 100, Origin.DIRECT), 100);
        check(choose(book, 100).source().equals(boundary), "Destination cannot become its own source");
        check(book.choose(new Position(1e300, 0, 0), 100, Set.of(), DESTINATION) == null,
            "Extreme finite geometry cannot overflow into a nearby source");
    }

    private static void boundedFifoAndReadOnlyViews() {
        KnowledgeBook book = new KnowledgeBook();
        for (int i = 0; i < 16; i++)
            book.remember(known(new Point(i, 0, 0), State.AVAILABLE, 100, Origin.DIRECT), 100);
        Point oldest = new Point(0, 0, 0), second = new Point(1, 0, 0);
        check(book.size() == 16, "Private source cap filled");
        check(!book.remember(known(oldest, State.AVAILABLE, 100, Origin.DIRECT), 100),
            "Exact duplicate does not refresh FIFO");
        book.knowledge(100); book.ownDirect(100); choose(book, 100);
        book.remember(known(new Point(16, 0, 0), State.AVAILABLE, 100, Origin.REPORT), 100);
        check(book.size() == 16 && book.knowledge(100).stream().noneMatch(k -> k.source().equals(oldest)),
            "Reads and duplicates cannot protect the oldest source from eviction");
        book.remember(known(second, State.EMPTY, 101, Origin.DIRECT), 101);
        book.remember(known(new Point(17, 0, 0), State.AVAILABLE, 101, Origin.DIRECT), 101);
        check(book.size() == 16 && book.knowledge(101).stream().anyMatch(k -> k.source().equals(second))
            && book.knowledge(101).stream().noneMatch(k -> k.source().equals(new Point(2, 0, 0))),
            "Accepted update moves only that source to FIFO tail");
        KnowledgeBook incomingOnly = new KnowledgeBook();
        incomingOnly.remember(known(oldest, State.AVAILABLE, 100, Origin.REPORT), 100);
        incomingOnly.remember(known(oldest, State.AVAILABLE, 101, Origin.DIRECT), 101);
        check(incomingOnly.size() == 1 && incomingOnly.knowledge(101).size() == 1
            && incomingOnly.ownDirect(101).size() == 1, "Origins share one bounded source slot");
    }

    private static void deterministicRoundOrderAndHorizon() {
        for (long seed : new long[] {0, 1, -1, 314159, Long.MIN_VALUE, Long.MAX_VALUE}) {
            Set<Integer> firstSlots = new HashSet<>();
            for (int round = 0; round < 4; round++) {
                List<Integer> order = PrivateCommunicationPolicy.roundOrder(seed, round);
                check(new HashSet<>(order).equals(Set.of(0, 1, 2, 3)),
                    "Each round grants every stable slot exactly one turn");
                check(order.equals(PrivateCommunicationPolicy.roundOrder(seed, round)),
                    "Pairing does not depend on world or entity identities");
                firstSlots.add(order.get(0));
            }
            check(firstSlots.size() == 4, "Four-round rotation balances first opportunity");
            check(PrivateCommunicationPolicy.roundOrder(seed, Long.MAX_VALUE).size() == 4,
                "Large round does not overflow order construction");
        }
        check(!PrivateCommunicationPolicy.roundOrder(0, 0)
            .equals(PrivateCommunicationPolicy.roundOrder(1, 0)), "Explicit seed affects order");
        PrivateCommunicationPolicy.validateHorizon(20);
        PrivateCommunicationPolicy.validateHorizon(1200);
        for (int invalid : new int[] {-20, 0, 1, 19, 21, 1199, 1201, 1220})
            rejected(() -> PrivateCommunicationPolicy.validateHorizon(invalid));
        rejected(() -> PrivateCommunicationPolicy.roundOrder(0, -1));
    }

    private static void strictBudgetsAndPhysicalRecheck() {
        RoundBudget budget = new RoundBudget();
        check(!budget.tryNearInspection() && !budget.tryOuterInspection(),
            "Inspection cannot precede a position probe");
        check(!budget.tryAssignment(), "Assignment cannot precede the one allowed recheck");
        for (int i = 0; i < 75; i++) {
            check(budget.tryNearPosition(), "Near position grant");
            check(budget.tryOuterPosition(), "Outer position grant");
        }
        for (int i = 0; i < 4; i++)
            check(budget.tryNearInspection() && budget.tryOuterInspection(), "Inspection grant");
        check(!budget.tryNearPosition() && !budget.tryOuterPosition()
            && !budget.tryNearInspection() && !budget.tryOuterInspection(),
            "All independent sensing caps are strict");
        check(budget.tryRecheck() && !budget.tryRecheck(), "Only one candidate recheck");
        check(budget.tryAssignment() && !budget.tryAssignment(), "Only one physical assignment attempt");
        check(budget.trySend() && !budget.trySend(), "Only one send attempt");
        var costs = budget.snapshot();
        check(costs.nearPositions() == 75 && costs.outerPositions() == 75
            && costs.nearInspections() == 4 && costs.outerInspections() == 4
            && costs.rechecks() == 1 && costs.assignments() == 1 && costs.sends() == 1,
            "Denied attempts do not increase charged operation counts");

        Point source = new Point(2, 0, 0);
        Choice reportChoice = new Choice(known(source, State.AVAILABLE, 100, Origin.REPORT), 4);
        check(!PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice,
            known(source, State.AVAILABLE, 101, Origin.REPORT), 101), "Report cannot confirm itself");
        check(!PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice,
            known(source, State.AVAILABLE, 100, Origin.DIRECT), 101), "Old own observation is not a recheck");
        check(!PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice,
            known(source, State.EMPTY, 101, Origin.DIRECT), 101), "Current empty denies assignment");
        check(!PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice,
            known(new Point(3, 0, 0), State.AVAILABLE, 101, Origin.DIRECT), 101),
            "Different-source observation cannot authorize the selected source");
        check(PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice,
            known(source, State.AVAILABLE, 101, Origin.DIRECT), 101),
            "Only same-source current positive direct observation satisfies the assignment gate");
        check(!PrivateCommunicationPolicy.isCurrentPositiveRecheck(reportChoice, null, 101),
            "Unknown recheck cannot authorize assignment");
    }

    private static void malformedInputs() {
        Point source = new Point(1, 0, 0);
        rejected(() -> new Knowledge(source, State.AVAILABLE, 0, 1, Origin.DIRECT, null));
        rejected(() -> new Knowledge(source, State.EMPTY, 1, 1, Origin.DIRECT, null));
        rejected(() -> new Knowledge(source, State.EMPTY, 0, -1, Origin.DIRECT, null));
        rejected(() -> new Knowledge(source, State.EMPTY, 0, 1, Origin.REPORT, null));
        rejected(() -> new Knowledge(source, State.EMPTY, 0, 1, Origin.REPORT, " "));
        rejected(() -> new Knowledge(source, State.EMPTY, 0, 1, Origin.DIRECT, "peer-report"));
        rejected(() -> new Position(Double.NaN, 0, 0));
        rejected(() -> new Position(0, Double.POSITIVE_INFINITY, 0));
        rejected(() -> new Choice(known(source, State.EMPTY, 1, Origin.DIRECT), 1));
        rejected(() -> new Choice(known(source, State.AVAILABLE, 1, Origin.DIRECT), 257));
        rejected(() -> new KnowledgeBook().knowledge(-1));
    }

    public static void main(String[] args) {
        privateSourcesAndNoForwarding();
        commonAgeAndEmptyVeto();
        geometryClaimsAndStableTies();
        boundedFifoAndReadOnlyViews();
        deterministicRoundOrderAndHorizon();
        strictBudgetsAndPhysicalRecheck();
        malformedInputs();
        System.out.println("PrivateCommunicationPolicyTest: " + checks + " checks passed");
    }
}
