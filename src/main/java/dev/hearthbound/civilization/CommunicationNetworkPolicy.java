package dev.hearthbound.civilization;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import java.util.function.Supplier;

/** Permission and access rules for the separately qualified communication modes. */
public final class CommunicationNetworkPolicy {
    public static final String DESIGN_SHA256 =
        "43588a883e3c5674deff44e022ca9c4819d5e1ca48c82b664884ff603fdc6b45";
    public static final int HORIZON_TICKS = 600;
    public static final PrivateCommunicationPolicy.Point DESTINATION =
        new PrivateCommunicationPolicy.Point(10, 101, 8);
    private static final List<PrivateCommunicationPolicy.Position> SEATS = List.of(
        new PrivateCommunicationPolicy.Position(5.5, 101, 7.5),
        new PrivateCommunicationPolicy.Position(12.5, 101, 7.5),
        new PrivateCommunicationPolicy.Position(14.5, 101, 10.5),
        new PrivateCommunicationPolicy.Position(12.5, 101, 12.5));

    private CommunicationNetworkPolicy() {}

    /** Same derivation as SourceReportSession; the native session is not itself an episode. */
    public static UUID observationEpisode(UUID world, UUID session, String dimension) {
        Objects.requireNonNull(world); Objects.requireNonNull(session); Objects.requireNonNull(dimension);
        return UUID.nameUUIDFromBytes((world + "|" + session + "|" + dimension)
            .getBytes(StandardCharsets.UTF_8));
    }

    /** Bind an already active-fence-validated native observation to the configured trial. */
    public static UUID bindObservationEpisode(UUID trialWorld, UUID trialEpisode,
                                              UUID observationWorld, UUID observationSession,
                                              String dimension) {
        Objects.requireNonNull(trialWorld); Objects.requireNonNull(trialEpisode);
        UUID derived = observationEpisode(observationWorld, observationSession, dimension);
        if (!trialWorld.equals(observationWorld) || !trialEpisode.equals(derived))
            throw new IllegalStateException("Outgoing observation does not belong to the configured trial episode");
        return derived;
    }

    public enum Arm {
        NO_MESSAGES, DIRECT, DIRECT_UNREAD, STAR, CHAIN, CYCLE;

        public boolean transportEnabled() { return this != NO_MESSAGES; }
        public boolean reportsExposedToDecisions() {
            return this != NO_MESSAGES && this != DIRECT_UNREAD;
        }
        public boolean permits(int sender, int recipient) {
            validateSlot(sender); validateSlot(recipient);
            if (sender == recipient) return false;
            int low = Math.min(sender, recipient), high = Math.max(sender, recipient);
            return switch (this) {
                case NO_MESSAGES -> false;
                case DIRECT, DIRECT_UNREAD -> true;
                case STAR -> low == 0;
                case CHAIN -> high - low == 1;
                case CYCLE -> high - low == 1 || (low == 0 && high == 3);
            };
        }
        public String edgeDecision(int sender, int recipient) {
            validateSlot(sender); validateSlot(recipient);
            if (sender == recipient) throw new IllegalArgumentException("Self communication is not a proposal");
            return !transportEnabled() ? "NETWORK_DISABLED"
                : permits(sender, recipient) ? "ALLOWED" : "TOPOLOGY_BLOCKED";
        }
        public List<List<Integer>> undirectedEdges() {
            var result = new ArrayList<List<Integer>>();
            for (int a = 0; a < PrivateCommunicationPolicy.WORKERS; a++)
                for (int b = a + 1; b < PrivateCommunicationPolicy.WORKERS; b++)
                    if (permits(a, b)) result.add(List.of(a, b));
            return List.copyOf(result);
        }
    }

    /** The original configure command remains a closed two-arm interface. */
    public static Arm legacyArm(String value) {
        Arm arm = Arm.valueOf(Objects.requireNonNull(value));
        if (arm != Arm.NO_MESSAGES && arm != Arm.DIRECT)
            throw new IllegalArgumentException("New network arms require configure-network");
        return arm;
    }

    private static void validateSlot(int slot) {
        if (slot < 0 || slot >= PrivateCommunicationPolicy.WORKERS)
            throw new IllegalArgumentException("Logical slot must be 0..3");
    }

    public static int recipientSlot(int sender, long round) {
        validateSlot(sender);
        if (round < 0) throw new IllegalArgumentException("Negative communication round");
        return (sender + 1 + (int) (round % 3)) % PrivateCommunicationPolicy.WORKERS;
    }

    /** Call only with an eligible own-direct payload; blocked edges still pay. */
    public static String chargeAndCheck(Arm arm, int sender, long round,
                                       PrivateCommunicationPolicy.RoundBudget budget) {
        Objects.requireNonNull(arm); Objects.requireNonNull(budget);
        int recipient = recipientSlot(sender, round);
        if (!budget.trySend()) throw new IllegalStateException("Send budget exceeded");
        return arm.edgeDecision(sender, recipient);
    }

    /** Unread controls do not even invoke the private-inbox supplier. */
    public static <T> List<T> policyReports(Arm arm, Supplier<List<T>> inbox) {
        Objects.requireNonNull(arm); Objects.requireNonNull(inbox);
        return arm.reportsExposedToDecisions() ? List.copyOf(inbox.get()) : List.of();
    }

    public static List<Integer> seatMap(String value) {
        if (value == null || !value.matches("[0-3]{4}"))
            throw new IllegalArgumentException("Seat map must be a four-digit permutation of 0123");
        List<Integer> result = value.chars().map(c -> c - '0').boxed().toList();
        if (new HashSet<>(result).size() != PrivateCommunicationPolicy.WORKERS)
            throw new IllegalArgumentException("Seat map contains a duplicate seat");
        return result;
    }

    public static PrivateCommunicationPolicy.Position seatPosition(int seat) {
        validateSlot(seat);
        return SEATS.get(seat);
    }

    public static String qualificationIdentity(String identity) {
        if (identity == null || !identity.matches("[a-z0-9][a-z0-9-]{0,95}"))
            throw new IllegalArgumentException("Qualification identity must be a bounded lowercase token");
        return identity;
    }

    /** This engineering command cannot consume a frozen expanded-study seed. */
    public static void validateQualification(long worldSeed, int horizon,
                                              PrivateCommunicationPolicy.Point destination) {
        if (worldSeed >= 55101 && worldSeed <= 55124)
            throw new IllegalArgumentException("Expanded-study seeds require a separate execution binding");
        if (horizon != HORIZON_TICKS || !DESTINATION.equals(destination))
            throw new IllegalArgumentException("Network qualification must preserve the frozen horizon and destination");
    }
}
