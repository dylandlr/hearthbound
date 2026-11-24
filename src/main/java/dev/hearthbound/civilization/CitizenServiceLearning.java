package dev.hearthbound.civilization;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import dev.hearthbound.civilization.ServiceValueLearner.*;

/**
 * One citizen's persistent service decisions and private outcome estimator.
 * The Forge adapter remains the sole authority for physical authenticity.
 * Capturing a decision does not create an outcome or a learning sample, and
 * an unresolved decision remains unresolved when this ledger is restored.
 */
public final class CitizenServiceLearning {
    public static final int SCHEMA_VERSION = 1;

    public record Decision(UUID optionId, Candidate candidate, Score selectedScore,
                           long startedTick, UUID commitment, UUID job, long boundTick) {
        public Decision {
            Objects.requireNonNull(optionId); Objects.requireNonNull(candidate); Objects.requireNonNull(selectedScore);
            if (startedTick < 0 || !candidate.id().equals(selectedScore.candidateId())
                    || Double.compare(candidate.authoredPrior(), selectedScore.authoredPrior()) != 0
                    || (commitment == null ? job != null || boundTick != -1 : boundTick < startedTick)
                    || (candidate.kind() != Kind.SUPPLY_WHEAT
                        && (!optionId.equals(commitment) || job != null || boundTick != startedTick)))
                throw new IllegalArgumentException("Invalid captured private service decision");
        }
    }
    public record Snapshot(int schemaVersion, Scope scope, UUID citizen,
                           List<Decision> decisions, ServiceValueLearner.Snapshot learner) {
        public Snapshot {
            Objects.requireNonNull(scope); Objects.requireNonNull(citizen); Objects.requireNonNull(learner);
            decisions = List.copyOf(decisions);
            if (schemaVersion != SCHEMA_VERSION || decisions.size() > ServiceValueLearner.MAX_SAMPLES
                    || !scope.equals(learner.scope()))
                throw new IllegalArgumentException("Invalid private service learning snapshot");
        }
    }

    private final Scope scope;
    private final UUID citizen;
    private ServiceValueLearner learner;
    private final LinkedHashMap<UUID, Decision> decisions = new LinkedHashMap<>();
    private final Map<UUID, ServiceOutcome> settled = new LinkedHashMap<>();
    private UUID active;
    private long latestOutcomeTick = -1;

    public CitizenServiceLearning(Scope scope, UUID citizen) {
        this.scope = Objects.requireNonNull(scope); this.citizen = Objects.requireNonNull(citizen);
        learner = new ServiceValueLearner(scope);
    }
    public Scope scope() { return scope; }
    public UUID citizen() { return citizen; }
    private void own(Candidate candidate) {
        Objects.requireNonNull(candidate);
        if (!citizen.equals(candidate.citizen())) throw new IllegalArgumentException("Foreign citizen candidate");
    }
    private static void tick(long now) {
        if (now < 0) throw new IllegalArgumentException("Negative private learning tick");
    }
    private static UUID outcomeCommitment(Decision d) {
        return d.commitment() == null ? d.optionId() : d.commitment();
    }
    public synchronized Candidate choose(List<Candidate> candidates) {
        Objects.requireNonNull(candidates); candidates.forEach(this::own);
        return learner.choose(candidates);
    }
    public synchronized Score score(Candidate candidate) { own(candidate); return learner.score(candidate); }
    public synchronized double partnerSuccess(UUID partner) { return learner.partnerSuccess(citizen, partner); }

    /** Capture before executing the option; features are never rebuilt from later knowledge. */
    public synchronized Decision begin(UUID optionId, Candidate selected, long now) {
        Objects.requireNonNull(optionId); own(selected); tick(now);
        Decision previous = decisions.get(optionId);
        if (previous != null) {
            if (!previous.candidate().equals(selected) || previous.startedTick() != now)
                throw new IllegalStateException("Conflicting private decision identity");
            return previous;
        }
        if (active != null || decisions.size() >= ServiceValueLearner.MAX_SAMPLES)
            throw new IllegalStateException("Unresolved service decision or exhausted private learning ledger");
        if (now < latestOutcomeTick)
            throw new IllegalArgumentException("Decision would use future private outcomes");
        if (decisions.values().stream().anyMatch(d -> optionId.equals(outcomeCommitment(d))))
            throw new IllegalStateException("Decision identity already belongs to a commitment");
        Decision made = new Decision(optionId, selected, learner.score(selected), now,
            selected.kind() == Kind.SUPPLY_WHEAT ? null : optionId, null,
            selected.kind() == Kind.SUPPLY_WHEAT ? -1 : now);
        decisions.put(optionId, made); active = optionId; return made;
    }
    /** Bind the exact accepted motor job once; a null job is allowed for a safe no-cargo failure. */
    public synchronized Decision bind(UUID optionId, UUID commitment, UUID job, long now) {
        Objects.requireNonNull(commitment); tick(now); Decision d = require(optionId);
        if (d.candidate().kind() != Kind.SUPPLY_WHEAT || now < d.startedTick())
            throw new IllegalStateException("Only a material option can bind a physical commitment");
        if (d.commitment() != null) {
            if (!d.commitment().equals(commitment) || !Objects.equals(d.job(), job))
                throw new IllegalStateException("Conflicting physical decision binding");
            return d;
        }
        if (!optionId.equals(active) || settled.containsKey(optionId))
            throw new IllegalStateException("A settled decision cannot acquire a physical job");
        for (Decision other : decisions.values()) if (!other.optionId().equals(optionId)
                && (commitment.equals(outcomeCommitment(other)) || commitment.equals(other.optionId())
                    || (job != null && job.equals(other.job()))))
            throw new IllegalStateException("Physical commitment or job already bound to another option");
        Decision bound = new Decision(d.optionId(), d.candidate(), d.selectedScore(), d.startedTick(), commitment, job, now);
        decisions.put(optionId, bound); return bound;
    }
    private Decision require(UUID optionId) {
        Objects.requireNonNull(optionId); Decision d = decisions.get(optionId);
        if (d == null) throw new IllegalArgumentException("Unknown captured service decision");
        return d;
    }
    public synchronized Decision active() { return active == null ? null : decisions.get(active); }
    public synchronized Decision decision(UUID optionId) { return decisions.get(optionId); }
    public synchronized ServiceOutcome serviceOutcome(UUID optionId) { return settled.get(optionId); }

    private ServiceOutcome outcome(UUID optionId, UUID receiptId, long finishedTick,
                                   double personalCost, Outcome outcome) {
        Decision d = require(optionId); tick(finishedTick);
        if (finishedTick < d.boundTick()) throw new IllegalArgumentException("Outcome predates its physical binding");
        Candidate c = d.candidate();
        ServiceOutcome made = new ServiceOutcome(receiptId, scope, outcomeCommitment(d), citizen, d.job(),
            c.kind(), c.partner(), c.features(), d.startedTick(), finishedTick, personalCost, outcome);
        ServiceOutcome previous = settled.get(optionId);
        if (previous != null && !previous.equals(made)) throw new IllegalStateException("Conflicting private service outcome");
        if (previous == null && !optionId.equals(active)) throw new IllegalStateException("Outcome has no active decision");
        return made;
    }
    /**
     * Bounded, non-mutating finalization check for the server thread immediately
     * before final physical delivery/release. It checks the proposed service and
     * optional output settlement together, including all duplicate identities.
     * This is not a physical witness and is not intended as a per-tick sensor.
     */
    public synchronized void validateSettlement(UUID optionId, UUID receiptId, long finishedTick,
                                               double personalCost, Outcome outcome,
                                               ProductionReceipt productionOrNull) {
        ServiceOutcome made = outcome(optionId, receiptId, finishedTick, personalCost, outcome);
        ServiceValueLearner trial = ServiceValueLearner.restore(learner.snapshot(), scope, finishedTick);
        trial.recordService(made);
        if (productionOrNull != null) {
            ownProduction(productionOrNull);
            if (productionOrNull.tick() != finishedTick)
                throw new IllegalArgumentException("Final production settlement must use the delivery tick");
            trial.recordProduction(productionOrNull);
        }
    }
    public synchronized boolean settle(UUID optionId, UUID receiptId, long finishedTick,
                                       double personalCost, Outcome outcome) {
        ServiceOutcome made = outcome(optionId, receiptId, finishedTick, personalCost, outcome);
        boolean changed = learner.recordService(made);
        if (changed) {
            settled.put(optionId, made); active = null;
            latestOutcomeTick = Math.max(latestOutcomeTick, made.finishedTick());
        }
        return changed;
    }
    private void ownProduction(ProductionReceipt receipt) {
        Objects.requireNonNull(receipt);
        if (!scope.equals(receipt.scope()) || !citizen.equals(receipt.citizen()))
            throw new IllegalArgumentException("Foreign citizen production evidence");
    }
    public synchronized boolean recordProduction(ProductionReceipt receipt) {
        ownProduction(receipt); boolean changed = learner.recordProduction(receipt);
        if (changed) latestOutcomeTick = Math.max(latestOutcomeTick, receipt.tick());
        return changed;
    }
    public synchronized Status status() { return learner.status(); }
    public synchronized Map<String, List<Double>> parameters() { return learner.parameters(); }
    public synchronized Snapshot snapshot() {
        return new Snapshot(SCHEMA_VERSION, scope, citizen, List.copyOf(decisions.values()), learner.snapshot());
    }
    private static boolean matches(Decision d, ServiceOutcome r, Scope scope, UUID citizen) {
        Candidate c = d.candidate();
        return r.scope().equals(scope) && r.citizen().equals(citizen)
            && outcomeCommitment(d).equals(r.commitment()) && Objects.equals(d.job(), r.job())
            && c.kind() == r.kind() && Objects.equals(c.partner(), r.partner()) && c.features().equals(r.features())
            && d.startedTick() == r.startedTick() && r.finishedTick() >= d.boundTick();
    }
    /** Replays only this actor's retained evidence; unresolved decisions remain held by the caller. */
    public static CitizenServiceLearning restore(Snapshot snapshot, Scope expected, UUID expectedCitizen, long now) {
        Objects.requireNonNull(snapshot); tick(now);
        if (!snapshot.scope().equals(expected) || !snapshot.citizen().equals(expectedCitizen))
            throw new IllegalArgumentException("Restored private learner identity mismatch");
        CitizenServiceLearning result = new CitizenServiceLearning(expected, expectedCitizen);
        var allServices = snapshot.learner().services(); var allProduction = snapshot.learner().production();
        for (ServiceOutcome r : allServices) if (!r.citizen().equals(expectedCitizen))
            throw new IllegalArgumentException("Another citizen's outcome entered a private learner");
        for (ProductionReceipt r : allProduction) result.ownProduction(r);
        result.learner = ServiceValueLearner.restore(snapshot.learner(), expected, now);
        for (ServiceOutcome r : allServices) result.latestOutcomeTick = Math.max(result.latestOutcomeTick, r.finishedTick());
        for (ProductionReceipt r : allProduction) result.latestOutcomeTick = Math.max(result.latestOutcomeTick, r.tick());
        var byCommitment = new LinkedHashMap<UUID, ServiceOutcome>();
        for (ServiceOutcome r : allServices) byCommitment.put(r.commitment(), r);
        var claimedCommitments = new java.util.HashSet<UUID>();
        var claimedJobs = new java.util.HashSet<UUID>();
        ServiceValueLearner audit = new ServiceValueLearner(expected);
        int serviceIndex = 0, productionIndex = 0;
        long previousFinished = -1;
        boolean unresolved = false;
        for (Decision d : snapshot.decisions()) {
            result.own(d.candidate());
            if (d.startedTick() > now || d.boundTick() > now || d.startedTick() < previousFinished || unresolved
                    || !claimedCommitments.add(outcomeCommitment(d))
                    || (d.job() != null && !claimedJobs.add(d.job()))
                    || result.decisions.putIfAbsent(d.optionId(), d) != null)
                throw new IllegalArgumentException("Invalid restored service decision order or binding");
            long serviceCount = d.selectedScore().serviceSamples(), productionCount = d.selectedScore().productionSamples();
            if (serviceCount != serviceIndex || productionCount < productionIndex || productionCount > allProduction.size())
                throw new IllegalArgumentException("Captured score has an invalid evidence prefix");
            while (productionIndex < productionCount) {
                ProductionReceipt r = allProduction.get(productionIndex++);
                if (r.tick() > d.startedTick()) throw new IllegalArgumentException("Decision used future production evidence");
                audit.recordProduction(r);
            }
            if (!audit.score(d.candidate()).equals(d.selectedScore()))
                throw new IllegalArgumentException("Captured score does not match its private evidence prefix");
            ServiceOutcome service = byCommitment.get(outcomeCommitment(d));
            if (service == null) { unresolved = true; result.active = d.optionId(); }
            else {
                if (!matches(d, service, expected, expectedCitizen) || serviceIndex >= allServices.size()
                        || !allServices.get(serviceIndex).equals(service))
                    throw new IllegalArgumentException("Settled service lost its captured private decision");
                result.settled.put(d.optionId(), service); audit.recordService(service); serviceIndex++;
                previousFinished = service.finishedTick();
            }
        }
        if (serviceIndex != allServices.size()) throw new IllegalArgumentException("Private outcome lacks a decision");
        // A decision ID cannot alias another decision's eventual kernel commitment.
        for (Decision d : result.decisions.values())
            if (!d.optionId().equals(outcomeCommitment(d)) && result.decisions.containsKey(outcomeCommitment(d)))
                throw new IllegalArgumentException("Restored decision identity aliases another commitment");
        return result;
    }
}
