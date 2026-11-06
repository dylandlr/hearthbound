package dev.hearthbound.evidence;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;

/**
 * In-memory, fail-closed causal reward proposal ledger. It never authorizes,
 * pays, or trains from a receipt. Only a trusted server admission boundary may
 * submit an actual VerifiedMillAttribution claim to this staging component.
 */
public final class OutcomeLedger {
    public record Decision(UUID world, String id, String citizenId, String jobId,
                           long tick, String action) {
        public Decision {
            Objects.requireNonNull(world);
            if (blank(id) || blank(citizenId) || blank(jobId) || blank(action) || tick < 0)
                throw new IllegalArgumentException("invalid decision");
        }
    }

    /** A zero weight excludes a contributor from that domain. */
    public record Contribution(String decisionId, int personalWeight, int researchWeight) {
        public Contribution {
            if (blank(decisionId) || personalWeight < 0 || researchWeight < 0
                    || (personalWeight == 0 && researchWeight == 0))
                throw new IllegalArgumentException("invalid contribution");
        }
    }

    /** Domain budgets are integer milli-points, with no implicit reward defaults. */
    public record Budget(long personal, long colony, long research) {
        public Budget {
            if (personal < 0 || colony < 0 || research < 0)
                throw new IllegalArgumentException("negative reward budget");
        }
    }

    public record Award(String eventId, String physicalEvidenceId, UUID world,
                        String colonyId, String jobId, List<Contribution> contributions,
                        Budget budget, List<DurableRewardLedger.Reward> rewards) {
        public Award {
            contributions = List.copyOf(contributions);
            rewards = List.copyOf(rewards);
        }
        /** A proposal only: callers must independently authorize durable delivery. */
        public DurableRewardLedger.Credit toUncommittedCredit() {
            return new DurableRewardLedger.Credit(eventId, rewards);
        }
    }

    private final Map<String, Decision> decisions = new HashMap<>();
    private final Map<String, Award> outcomes = new HashMap<>();
    private final Map<String, String> usedPhysicalEvidence = new HashMap<>();

    public synchronized boolean register(Decision decision) {
        Objects.requireNonNull(decision);
        Decision existing = decisions.putIfAbsent(decision.id(), decision);
        if (existing != null && !existing.equals(decision))
            throw new IllegalStateException("conflicting decision identity");
        return existing == null;
    }

    /**
     * Calculates a proposal from an upstream-validated physical Create claim.
     * This method cannot independently prove that the passed claim came from
     * Minecraft; callers must use the server's verified export + fences.
     */
    public synchronized Award proposeMill(VerifiedMillAttribution.Claim claim,
                                          UUID world, String physicalEvidenceId,
                                          String colonyId, List<Contribution> contributors,
                                          Budget budget) {
        Objects.requireNonNull(claim);
        Objects.requireNonNull(world);
        Objects.requireNonNull(contributors);
        Objects.requireNonNull(budget);
        if (blank(physicalEvidenceId) || blank(colonyId) || blank(claim.jobId())
                || blank(claim.citizenId()) || blank(claim.dimension()) || blank(claim.machine())
                || claim.observedStartTick() < 0 || claim.finishTick() <= claim.observedStartTick())
            throw new IllegalArgumentException("invalid claimed physical outcome");
        String expected = "hearthbound:mill:v1:" + world + ":" + claim.dimension() + ":" + claim.jobId();
        if (!expected.equals(claim.eventId()))
            throw new IllegalArgumentException("world/job event identity mismatch");
        if (contributors.isEmpty() || contributors.size() > 128)
            throw new IllegalArgumentException("invalid contributor count");
        List<Contribution> sorted = new ArrayList<>(contributors);
        sorted.sort(Comparator.comparing(Contribution::decisionId));
        Set<String> distinct = new HashSet<>();
        boolean ownerParticipated = false;
        for (Contribution share : sorted) {
            if (!distinct.add(share.decisionId()))
                throw new IllegalArgumentException("duplicate contributing decision");
            Decision decision = decisions.get(share.decisionId());
            if (decision == null || !world.equals(decision.world())
                    || !claim.jobId().equals(decision.jobId())
                    || decision.tick() > claim.observedStartTick())
                throw new IllegalArgumentException("unknown, cross-job or future contributor");
            ownerParticipated |= claim.citizenId().equals(decision.citizenId());
        }
        if (!ownerParticipated)
            throw new IllegalArgumentException("verified mill owner missing from contributors");
        String owner = usedPhysicalEvidence.get(physicalEvidenceId);
        if (owner != null && !owner.equals(claim.eventId()))
            throw new IllegalStateException("physical evidence already assigned to another outcome");

        Map<String, Long> allocations = new TreeMap<>();
        allocate(allocations, sorted, budget.personal(), false);
        allocate(allocations, sorted, budget.research(), true);
        if (budget.colony() > 0) merge(allocations, colonyId, "colony", budget.colony());
        if (allocations.isEmpty())
            throw new IllegalArgumentException("outcome cannot propose an empty credit");
        List<DurableRewardLedger.Reward> rewards = new ArrayList<>();
        allocations.forEach((key, milli) -> {
            int separator = key.indexOf('\0');
            rewards.add(new DurableRewardLedger.Reward(
                    key.substring(0, separator), key.substring(separator + 1), milli));
        });
        Award proposed = new Award(claim.eventId(), physicalEvidenceId, world,
                colonyId, claim.jobId(), sorted, budget, rewards);
        Award previous = outcomes.get(claim.eventId());
        if (previous != null) {
            if (!previous.equals(proposed))
                throw new IllegalStateException("conflicting replay for outcome identity");
            return previous;
        }
        outcomes.put(claim.eventId(), proposed);
        usedPhysicalEvidence.put(physicalEvidenceId, claim.eventId());
        return proposed;
    }

    private void allocate(Map<String, Long> totals, List<Contribution> contributors,
                          long budget, boolean research) {
        if (budget == 0) return;
        List<Weighted> eligible = new ArrayList<>();
        long sum = 0;
        for (Contribution contributor : contributors) {
            int weight = research ? contributor.researchWeight() : contributor.personalWeight();
            if (weight == 0) continue;
            sum = Math.addExact(sum, weight);
            eligible.add(new Weighted(contributor.decisionId(), weight));
        }
        if (sum == 0) throw new IllegalArgumentException("positive budget without eligible contributor");
        BigInteger total = BigInteger.valueOf(sum);
        BigInteger amount = BigInteger.valueOf(budget);
        long allocated = 0;
        for (Weighted weighted : eligible) {
            BigInteger[] div = amount.multiply(BigInteger.valueOf(weighted.weight)).divideAndRemainder(total);
            weighted.points = div[0].longValueExact();
            weighted.remainder = div[1];
            allocated = Math.addExact(allocated, weighted.points);
        }
        eligible.sort(Comparator.comparing((Weighted w) -> w.remainder).reversed()
                .thenComparing(w -> w.decisionId));
        long extra = budget - allocated;
        for (int i = 0; i < extra; i++) eligible.get(i).points++;
        String domain = research ? "research" : "personal";
        for (Weighted weighted : eligible) {
            if (weighted.points != 0)
                merge(totals, decisions.get(weighted.decisionId).citizenId(), domain, weighted.points);
        }
    }

    private static final class Weighted {
        final String decisionId;
        final int weight;
        long points;
        BigInteger remainder;
        Weighted(String id, int weight) { this.decisionId = id; this.weight = weight; }
    }

    private static void merge(Map<String, Long> rewards, String id, String domain, long value) {
        if (blank(id) || id.indexOf('\0') >= 0)
            throw new IllegalArgumentException("invalid reward identity");
        rewards.merge(id + '\0' + domain, value, Math::addExact);
    }
    private static boolean blank(String text) { return text == null || text.isBlank(); }
    public synchronized int proposalCount() { return outcomes.size(); }
    public synchronized int registeredDecisionCount() { return decisions.size(); }
}
