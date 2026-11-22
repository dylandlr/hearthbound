package dev.hearthbound.evidence;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Disposable, success-only terminal action-value replay. No gameplay authority.
 * The server must supply freshly reconciled journal views AND live Create claims;
 * these public data types are not authentication tokens. Rebuild from zero on
 * every query so withdrawn evidence cannot survive in cached learned weights.
 */
public final class VerifiedMillLearning {
    public static final String ACTION = "EXECUTOR_ASSIGNED_WHEAT_HAUL";
    public static final double ALPHA = 0.25;
    public static final double GAMMA_PER_TICK = 0.999;
    public static final long PERSONAL_MILLI = 500;
    public static final int MAX_SAMPLES = 128;

    private VerifiedMillLearning() {}

    public record Input(CausalEvidenceJournal.View view, VerifiedMillAttribution.Claim claim) {}
    public record Step(String eventId, String physicalEvidenceId, long durationTicks,
                       long personalMilli, double target, double before, double after) {}
    public record Replay(UUID world, String citizenId, List<Step> steps, double value) {
        public Replay { steps = List.copyOf(steps); }
    }

    /**
     * Fixed single-action, terminal Monte Carlo update Q += alpha*(r*gamma^dt-Q).
     * No inferred failures, unseen observations, bootstrapping, or policy promotion.
     * Duplicate evidence is replayed once; conflicting duplicates reject the batch.
     */
    public static Replay replay(UUID world, String citizenId, List<Input> inputs) {
        Objects.requireNonNull(world);
        if (!UUID.fromString(citizenId).toString().equals(citizenId))
            throw new IllegalArgumentException("noncanonical citizen");
        if (inputs.size() > MAX_SAMPLES) throw new IllegalArgumentException("replay limit exceeded");
        var unique = new LinkedHashMap<String, Input>();
        for (Input input : inputs) {
            Objects.requireNonNull(input);
            var view = Objects.requireNonNull(input.view());
            var o = Objects.requireNonNull(view.observation());
            var c = Objects.requireNonNull(input.claim());
            if (!view.activeForAudit() || !world.equals(o.world())
                    || !citizenId.equals(o.citizenId()) || !o.eventId().equals(c.eventId())
                    || !o.citizenId().equals(c.citizenId()) || !o.jobId().equals(c.jobId())
                    || !o.dimension().equals(c.dimension())
                    || !Long.toString(o.machinePos()).equals(c.machine())
                    || o.startTick() != c.observedStartTick() || o.finishTick() != c.finishTick())
                throw new IllegalArgumentException("unreconciled or mismatched learning evidence");
            Input prior = unique.putIfAbsent(o.eventId(), input);
            if (prior != null && !prior.equals(input))
                throw new IllegalArgumentException("conflicting learning event");
        }
        // Stable replay independent of hash iteration or operator query ordering.
        var ordered = new ArrayList<>(unique.values());
        ordered.sort(Comparator.comparingLong((Input i) -> i.view().observation().finishTick())
                .thenComparing(i -> i.view().observation().eventId()));
        OutcomeLedger ledger = new OutcomeLedger();
        var steps = new ArrayList<Step>();
        double value = 0.0;
        for (Input input : ordered) {
            var o = input.view().observation();
            String decision = "hearthbound:executor-haul:v1:" + world + ":"
                    + o.jobId() + ":" + citizenId;
            ledger.register(new OutcomeLedger.Decision(world, decision, citizenId,
                    o.jobId(), o.assignedTick(), ACTION));
            OutcomeLedger.Award award = ledger.proposeMill(input.claim(), world,
                    o.physicalEvidenceId(), "UNASSIGNED_COLONY",
                    List.of(new OutcomeLedger.Contribution(decision, 1, 0)),
                    new OutcomeLedger.Budget(PERSONAL_MILLI, 0, 0));
            long reward = award.rewards().stream()
                    .filter(r -> r.citizenId().equals(citizenId) && r.domain().equals("personal"))
                    .mapToLong(DurableRewardLedger.Reward::milliPoints).sum();
            long duration = o.finishTick() - o.assignedTick();
            double target = (reward / 1000.0) * StrictMath.pow(GAMMA_PER_TICK, duration);
            double before = value;
            value += ALPHA * (target - value);
            steps.add(new Step(o.eventId(), o.physicalEvidenceId(), duration,
                    reward, target, before, value));
        }
        return new Replay(world, citizenId, steps, value);
    }
}
