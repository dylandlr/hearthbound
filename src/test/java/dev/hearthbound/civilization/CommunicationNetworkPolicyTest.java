package dev.hearthbound.civilization;

import dev.hearthbound.civilization.CommunicationNetworkPolicy.Arm;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Knowledge;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.KnowledgeBook;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Origin;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Point;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Position;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.RoundBudget;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.State;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicInteger;

/** Engineering contracts; physical transport and outcomes require live evidence. */
public final class CommunicationNetworkPolicyTest {
    private static int checks;

    private static void check(boolean value, String reason) {
        checks++;
        if (!value) throw new AssertionError(reason);
    }
    private static void rejected(Runnable action) {
        checks++;
        try { action.run(); }
        catch (IllegalArgumentException | IllegalStateException | NullPointerException expected) { return; }
        throw new AssertionError("Expected invalid qualification input to be rejected");
    }

    private static void exactDirectedEdgesAndNoSelfLinks() {
        Map<Arm, List<String>> expected = Map.of(
            Arm.NO_MESSAGES, List.of("0000", "0000", "0000", "0000"),
            Arm.DIRECT, List.of("0111", "1011", "1101", "1110"),
            Arm.DIRECT_UNREAD, List.of("0111", "1011", "1101", "1110"),
            Arm.STAR, List.of("0111", "1000", "1000", "1000"),
            Arm.CHAIN, List.of("0100", "1010", "0101", "0010"),
            Arm.CYCLE, List.of("0101", "1010", "0101", "1010"));
        Map<Arm, Integer> undirectedCounts = Map.of(Arm.NO_MESSAGES, 0,
            Arm.DIRECT, 6, Arm.DIRECT_UNREAD, 6, Arm.STAR, 3, Arm.CHAIN, 3, Arm.CYCLE, 4);
        for (Arm arm : Arm.values()) {
            Set<List<Integer>> declared = new HashSet<>(arm.undirectedEdges());
            check(declared.size() == undirectedCounts.get(arm), "Exact distinct undirected edge count");
            for (int sender = 0; sender < 4; sender++) {
                for (int recipient = 0; recipient < 4; recipient++) {
                    boolean permits = expected.get(arm).get(sender).charAt(recipient) == '1';
                    check(arm.permits(sender, recipient) == permits, "Full declared directed adjacency matrix");
                    check(arm.permits(sender, recipient) == arm.permits(recipient, sender), "Undirected permission is symmetric");
                    if (sender < recipient)
                        check(declared.contains(List.of(sender, recipient)) == permits,
                            "Exported undirected table exactly matches permission");
                    if (sender == recipient) {
                        final int self = sender;
                        rejected(() -> arm.edgeDecision(self, self));
                    } else {
                        String expectedDecision = arm == Arm.NO_MESSAGES ? "NETWORK_DISABLED"
                            : permits ? "ALLOWED" : "TOPOLOGY_BLOCKED";
                        check(arm.edgeDecision(sender, recipient).equals(expectedDecision),
                            "Disabled transport and blocked topology stay distinct");
                    }
                }
            }
        }
    }

    private static void recipientRotationAndChargedRejections() {
        int[][] expected = {{1, 2, 3}, {2, 3, 0}, {3, 0, 1}, {0, 1, 2}};
        Map<Arm, Integer> allowed = Map.of(Arm.NO_MESSAGES, 0,
            Arm.DIRECT, 120, Arm.DIRECT_UNREAD, 120, Arm.STAR, 60, Arm.CHAIN, 60, Arm.CYCLE, 80);
        for (Arm arm : Arm.values()) {
            int actual = 0;
            for (int round = 0; round < 30; round++) {
                for (int sender = 0; sender < 4; sender++) {
                    check(CommunicationNetworkPolicy.recipientSlot(sender, round) == expected[sender][round % 3],
                        "Fixed recipient rotation without a substitute peer");
                    RoundBudget budget = new RoundBudget();
                    String decision = CommunicationNetworkPolicy.chargeAndCheck(arm, sender, round, budget);
                    check(budget.snapshot().sends() == 1, "Disabled and topology-blocked sends consume the same attempt budget");
                    if (decision.equals("ALLOWED")) actual++;
                    final int slot = sender, tickRound = round;
                    rejected(() -> CommunicationNetworkPolicy.chargeAndCheck(arm, slot, tickRound, budget));
                    check(budget.snapshot().sends() == 1, "A denied second attempt cannot spend or route again");
                }
            }
            check(actual == allowed.get(arm), "Predeclared permission volume over 120 opportunities");
        }
        check(CommunicationNetworkPolicy.recipientSlot(0, Long.MAX_VALUE) == 2,
            "Large round preserves bounded remainder without overflow");
    }

    private static void unreadDoesNotFetchOrAffectPrivateDecisions() {
        Point ownSource = new Point(5, 0, 0), peerSource = new Point(1, 0, 0);
        Knowledge own = new Knowledge(ownSource, State.AVAILABLE, 1, 100, Origin.DIRECT, null);
        Knowledge report = new Knowledge(peerSource, State.AVAILABLE, 2, 100, Origin.REPORT, "actual-delivery-id");
        for (Arm arm : Arm.values()) {
            var inbox = new ArrayList<>(List.of(report));
            AtomicInteger fetches = new AtomicInteger();
            List<Knowledge> inputs = CommunicationNetworkPolicy.policyReports(arm, () -> {
                fetches.incrementAndGet(); return inbox;
            });
            boolean exposed = arm == Arm.DIRECT || arm == Arm.STAR || arm == Arm.CHAIN || arm == Arm.CYCLE;
            check(fetches.get() == (exposed ? 1 : 0), "The unread control never fetches the inbox");
            check(inbox.equals(List.of(report)), "Access control leaves truthful inbox history intact");
            check(inputs.equals(exposed ? List.of(report) : List.of()), "Only exposed arms receive policy report inputs");
            inbox.clear();
            check(inputs.size() == (exposed ? 1 : 0), "Policy view is isolated from later inbox mutation");
            KnowledgeBook menu = new KnowledgeBook();
            menu.remember(own, 100);
            for (Knowledge input : inputs) menu.remember(input, 100);
            var choice = menu.choose(new Position(0.5, 0.5, 0.5), 100, Set.of(), new Point(0, 0, 8));
            check(choice.reportCued() == exposed, "An unread nearby report cannot change the private decision");
            check(choice.source().equals(exposed ? peerSource : ownSource), "Grounded private menu remains independent");
            check(menu.ownDirect(100).equals(List.of(own)), "A received report never becomes outgoing direct evidence");
        }
        for (Arm arm : List.of(Arm.NO_MESSAGES, Arm.DIRECT_UNREAD))
            check(CommunicationNetworkPolicy.policyReports(arm, () -> {
                throw new AssertionError("Unreachable private inbox supplier");
            }).isEmpty(), "Unread exclusion is lazy, not an after-read filter");
        check(Arm.DIRECT_UNREAD.transportEnabled(), "Unread preserves true transport permission");
        check(!Arm.NO_MESSAGES.transportEnabled(), "Isolated workers disable transport");
    }

    private static void counterbalancedSeatsAndClosedLegacyInterface() {
        List<String> permutations = List.of("0123", "0132", "0213", "0231", "0312", "0321",
            "1023", "1032", "1203", "1230", "1302", "1320", "2013", "2031", "2103", "2130",
            "2301", "2310", "3012", "3021", "3102", "3120", "3201", "3210");
        int[][] counts = new int[4][4];
        Set<List<Integer>> maps = new HashSet<>();
        for (String value : permutations) {
            List<Integer> map = CommunicationNetworkPolicy.seatMap(value);
            check(maps.add(map) && new HashSet<>(map).equals(Set.of(0, 1, 2, 3)), "All 24 seat maps are unique bijections");
            for (int slot = 0; slot < 4; slot++) counts[slot][map.get(slot)]++;
        }
        for (int[] row : counts) for (int count : row)
            check(count == 6, "Each logical role occupies each physical seat six times");
        check(CommunicationNetworkPolicy.seatMap("2031").equals(List.of(2, 0, 3, 1)),
            "Qualification mapping is logical-slot to physical-seat, not its inverse");
        check(CommunicationNetworkPolicy.seatPosition(0).equals(new Position(5.5, 101, 7.5))
            && CommunicationNetworkPolicy.seatPosition(1).equals(new Position(12.5, 101, 7.5))
            && CommunicationNetworkPolicy.seatPosition(2).equals(new Position(14.5, 101, 10.5))
            && CommunicationNetworkPolicy.seatPosition(3).equals(new Position(12.5, 101, 12.5)),
            "Physical positions exactly match the frozen scene");
        for (Arm arm : Arm.values()) {
            if (arm == Arm.NO_MESSAGES || arm == Arm.DIRECT)
                check(CommunicationNetworkPolicy.legacyArm(arm.name()) == arm, "Existing arm remains available through legacy configure");
            else rejected(() -> CommunicationNetworkPolicy.legacyArm(arm.name()));
        }
        CommunicationNetworkPolicy.validateQualification(56101, 600, new Point(10, 101, 8));
        for (long seed = 55101; seed <= 55124; seed++) {
            final long reserved = seed;
            rejected(() -> CommunicationNetworkPolicy.validateQualification(reserved, 600, new Point(10, 101, 8)));
        }
    }

    private static void malformedInputs() {
        for (String value : new String[] {"", "012", "01234", "0012", "0124", "-123", "012x", "0,1,2,3"})
            rejected(() -> CommunicationNetworkPolicy.seatMap(value));
        rejected(() -> CommunicationNetworkPolicy.seatMap(null));
        rejected(() -> CommunicationNetworkPolicy.seatPosition(-1));
        rejected(() -> CommunicationNetworkPolicy.seatPosition(4));
        rejected(() -> CommunicationNetworkPolicy.recipientSlot(0, -1));
        rejected(() -> CommunicationNetworkPolicy.recipientSlot(4, 0));
        rejected(() -> Arm.CHAIN.permits(-1, 0));
        rejected(() -> Arm.STAR.permits(0, 4));
        rejected(() -> CommunicationNetworkPolicy.legacyArm("direct"));
        rejected(() -> CommunicationNetworkPolicy.qualificationIdentity("../world"));
        rejected(() -> CommunicationNetworkPolicy.qualificationIdentity("x".repeat(97)));
        rejected(() -> CommunicationNetworkPolicy.validateQualification(56101, 580, new Point(10, 101, 8)));
        rejected(() -> CommunicationNetworkPolicy.validateQualification(56101, 600, new Point(11, 101, 8)));
        check(CommunicationNetworkPolicy.qualificationIdentity("qual-direct-unread").equals("qual-direct-unread"),
            "Bounded engineering identity accepted");
    }

    private static void nativeSessionAndDerivedEpisodeStayDistinct() {
        // Archived PR218 pair-01-direct report ID and runtime episode; this is
        // an identity regression fixture, not a new qualification observation.
        UUID world = UUID.fromString("b540facc-e1aa-4fe6-8f4f-252411afb6d0");
        UUID session = UUID.fromString("65419d4c-cebe-4f7f-9b98-0cbf979d951a");
        UUID episode = UUID.fromString("afbf9d64-c4e9-31c1-b884-640eb4e9bded");
        String dimension = "minecraft:overworld";
        check(session.version() == 4 && episode.version() == 3 && !session.equals(episode),
            "The actual native server session and derived decision episode are distinct identities");
        check(CommunicationNetworkPolicy.observationEpisode(world, session, dimension).equals(episode),
            "Exact UTF-8 name-UUID derivation reproduces the archived live episode");
        check(CommunicationNetworkPolicy.bindObservationEpisode(world, episode, world, session, dimension).equals(episode),
            "A valid native observation binds to its configured episode without treating the raw session as an episode");

        UUID restartedSession = UUID.fromString("12345678-90ab-4cde-8f01-23456789abcd");
        UUID restartedEpisode = CommunicationNetworkPolicy.observationEpisode(world, restartedSession, dimension);
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, restartedEpisode, world, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, episode, world, restartedSession, dimension));
        check(CommunicationNetworkPolicy.bindObservationEpisode(world, restartedEpisode, world, restartedSession, dimension)
            .equals(restartedEpisode), "Only the matching native session binds after a new server lifetime");
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, session, world, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, episode, world, episode, dimension));

        UUID otherWorld = UUID.fromString("01234567-89ab-4def-8123-456789abcdef");
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, episode, otherWorld, session, dimension));
        UUID otherWorldEpisode = CommunicationNetworkPolicy.observationEpisode(otherWorld, session, dimension);
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, otherWorldEpisode, otherWorld, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, episode, world, session, "minecraft:the_nether"));
        UUID otherDimensionEpisode = CommunicationNetworkPolicy.observationEpisode(world, session, "minecraft:the_nether");
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, otherDimensionEpisode, world, session, dimension));

        // A separately declared vector anchors the encoding and separator bytes.
        check(CommunicationNetworkPolicy.observationEpisode(otherWorld, restartedSession, dimension)
            .equals(UUID.fromString("163ed56f-c2ed-3070-8bc0-19a426af0612")), "Declared derivation vector is stable");
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(null, episode, world, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.bindObservationEpisode(world, null, world, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.observationEpisode(null, session, dimension));
        rejected(() -> CommunicationNetworkPolicy.observationEpisode(world, null, dimension));
        rejected(() -> CommunicationNetworkPolicy.observationEpisode(world, session, null));
    }

    public static void main(String[] args) {
        exactDirectedEdgesAndNoSelfLinks();
        recipientRotationAndChargedRejections();
        unreadDoesNotFetchOrAffectPrivateDecisions();
        counterbalancedSeatsAndClosedLegacyInterface();
        malformedInputs();
        nativeSessionAndDerivedEpisodeStayDistinct();
        System.out.println("CommunicationNetworkPolicyTest: " + checks + " checks passed");
    }
}
