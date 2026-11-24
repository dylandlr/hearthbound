package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;

/**
 * Small online contextual service estimator for the live option layer.
 * Recursive least squares learns execution duration, measured personal cost,
 * and observed completion from explicit settled service outcomes. A different
 * head consumes independently verified downstream production settlements.
 * A chest insertion never becomes a production sample. Public DTOs are not
 * proof: only the trusted Forge outcome adapter may admit them.
 *
 * Choice includes an explicitly authored utility prior and time-cost rate.
 * Persistent motor commitments, initial priorities and tie breaking are authored
 * behavior; fitting these outcome heads does not establish an occupation.
 */
public final class ServiceValueLearner {
    public static final int SCHEMA_VERSION = 1, MAX_SAMPLES = 8192;
    public static final List<String> FEATURE_NAMES = List.of("bias", "need_units", "distance",
        "evidence_age", "competition", "partner_success", "supply", "observe", "carry_request", "wait");
    public static final int DIMENSIONS = FEATURE_NAMES.size();
    public static final double DURATION_SCALE = 1200., TIME_COST_PER_TICK = .001;
    public enum Kind { SUPPLY_WHEAT, OBSERVE_BUFFER, CARRY_REQUEST, WAIT }
    public enum Outcome {
        VERIFIED_TRANSFER, VERIFIED_OBSERVATION, VERIFIED_REQUEST_DELIVERY, VERIFIED_WAIT,
        VERIFIED_NO_CARGO_CANCEL, VERIFIED_FAILURE_NO_CARGO;
        public boolean completed() { return this != VERIFIED_NO_CARGO_CANCEL && this != VERIFIED_FAILURE_NO_CARGO; }
    }
    public record Features(List<Double> values) {
        public Features {
            values = List.copyOf(values);
            if (values.size() != DIMENSIONS || values.get(0) != 1.
                    || values.stream().anyMatch(v -> !Double.isFinite(v) || v < 0 || v > 1))
                throw new IllegalArgumentException("Invalid local service features");
        }
        double[] vector() { return values.stream().mapToDouble(Double::doubleValue).toArray(); }
    }
    public record Candidate(String id, UUID citizen, UUID needId, UUID partner,
                            Kind kind, Features features, double authoredPrior) {
        public Candidate {
            bounded(id); Objects.requireNonNull(citizen); Objects.requireNonNull(kind); Objects.requireNonNull(features);
            if (!Double.isFinite(authoredPrior) || Math.abs(authoredPrior) > 100)
                throw new IllegalArgumentException("Invalid explicit authored prior");
            matchingKind(kind, features);
        }
    }
    public record Score(String candidateId, double authoredPrior, double learnedProductionUnits,
                         double estimatedDurationTicks, double estimatedPersonalCost,
                         double estimatedSuccess, double total, long serviceSamples, long productionSamples) {}
    public record ServiceOutcome(UUID id, Scope scope, UUID commitment, UUID citizen, UUID job,
                                  Kind kind, UUID partner, Features features, long startedTick,
                                  long finishedTick, double personalCost, Outcome outcome) {
        public ServiceOutcome {
            Objects.requireNonNull(id); Objects.requireNonNull(scope); Objects.requireNonNull(commitment);
            Objects.requireNonNull(citizen); Objects.requireNonNull(kind); Objects.requireNonNull(features);
            Objects.requireNonNull(outcome); matchingKind(kind, features);
            if (startedTick < 0 || finishedTick < startedTick || finishedTick - startedTick > 24000
                    || !Double.isFinite(personalCost) || personalCost < 0 || personalCost > 1000
                    || (outcome == Outcome.VERIFIED_TRANSFER && (kind != Kind.SUPPLY_WHEAT || job == null))
                    || (outcome == Outcome.VERIFIED_OBSERVATION && kind != Kind.OBSERVE_BUFFER)
                    || (outcome == Outcome.VERIFIED_REQUEST_DELIVERY && kind != Kind.CARRY_REQUEST)
                    || (outcome == Outcome.VERIFIED_WAIT && kind != Kind.WAIT))
                throw new IllegalArgumentException("Invalid independently settled service outcome");
        }
    }
    /** One final positive output settlement per commitment; aggregate process output before admission. */
    public record ProductionReceipt(UUID id, Scope scope, String physicalEvidence, UUID commitment,
                                     UUID citizen, UUID job, long tick, int units) {
        public ProductionReceipt {
            Objects.requireNonNull(id); Objects.requireNonNull(scope); bounded(physicalEvidence);
            Objects.requireNonNull(commitment); Objects.requireNonNull(citizen); Objects.requireNonNull(job);
            if (tick < 0 || units < 1 || units > 64)
                throw new IllegalArgumentException("Production must contain independently verified positive output");
        }
    }
    public record Snapshot(int schemaVersion, Scope scope, List<String> featureNames,
                           List<ServiceOutcome> services, List<ProductionReceipt> production) {
        public Snapshot {
            Objects.requireNonNull(scope); featureNames = List.copyOf(featureNames);
            services = List.copyOf(services); production = List.copyOf(production);
            if (schemaVersion != SCHEMA_VERSION || !featureNames.equals(FEATURE_NAMES)
                    || services.size() > MAX_SAMPLES || production.size() > MAX_SAMPLES)
                throw new IllegalArgumentException("Invalid learned service snapshot");
        }
    }
    public record Status(int serviceSamples, int productionSamples, long independentlyVerifiedOutputUnits,
                          String learningScope, boolean productionLearningActive) {}

    private static final class Regression {
        final double[] weights = new double[DIMENSIONS];
        final double[][] inverse = new double[DIMENSIONS][DIMENSIONS];
        Regression() { for (int i = 0; i < DIMENSIONS; i++) inverse[i][i] = 1.; }
        double predict(double[] x) {
            double value = 0.; for (int i = 0; i < DIMENSIONS; i++) value += weights[i] * x[i];
            return value;
        }
        void fit(double[] x, double target) {
            double[] px = new double[DIMENSIONS];
            for (int i = 0; i < DIMENSIONS; i++) for (int j = 0; j < DIMENSIONS; j++) px[i] += inverse[i][j] * x[j];
            double denominator = 1.; for (int i = 0; i < DIMENSIONS; i++) denominator += x[i] * px[i];
            if (!Double.isFinite(target) || !Double.isFinite(denominator) || denominator <= 0)
                throw new IllegalStateException("Invalid recursive regression update");
            double error = target - predict(x);
            for (int i = 0; i < DIMENSIONS; i++) {
                weights[i] += px[i] / denominator * error;
                for (int j = 0; j < DIMENSIONS; j++) inverse[i][j] -= px[i] * px[j] / denominator;
                if (!Double.isFinite(weights[i])) throw new IllegalStateException("Nonfinite learned service parameter");
            }
        }
    }
    private final Scope scope;
    private final Regression duration = new Regression(), cost = new Regression(), success = new Regression();
    private final Regression output = new Regression();
    private final LinkedHashMap<UUID, ServiceOutcome> services = new LinkedHashMap<>();
    private final Map<UUID, UUID> serviceForCommitment = new LinkedHashMap<>();
    private final Map<UUID, UUID> serviceForJob = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, ProductionReceipt> production = new LinkedHashMap<>();
    private final Map<String, UUID> physicalEvidence = new LinkedHashMap<>();
    private final Map<UUID, Integer> producedByCommitment = new LinkedHashMap<>();

    public ServiceValueLearner(Scope scope) {
        this.scope = Objects.requireNonNull(scope);
        // Transparent engineering priors, present even before any learned sample.
        duration.weights[0] = 20. / DURATION_SCALE;
        duration.weights[2] = 256. / DURATION_SCALE; // Four ticks per estimated block, up to64 blocks.
        success.weights[0] = .5;
    }
    private static void bounded(String value) {
        if (value == null || value.isBlank() || value.length() > 2048)
            throw new IllegalArgumentException("Invalid bounded identifier");
    }
    private static void matchingKind(Kind kind, Features features) {
        for (int i = 0; i < Kind.values().length; i++) if (features.values().get(6 + i) != (i == kind.ordinal() ? 1. : 0.))
            throw new IllegalArgumentException("Skill kind disagrees with its feature vector");
    }
    public static Features features(Kind kind, int needUnits, double distanceBlocks, long evidenceAgeTicks,
                                     int competitors, double partnerSuccess) {
        Objects.requireNonNull(kind);
        if (needUnits < 0 || needUnits > 64 || !Double.isFinite(distanceBlocks) || distanceBlocks < 0
                || evidenceAgeTicks < 0 || competitors < 0 || !Double.isFinite(partnerSuccess)
                || partnerSuccess < 0 || partnerSuccess > 1)
            throw new IllegalArgumentException("Invalid local feature inputs");
        var values = new ArrayList<Double>(List.of(1., needUnits / 64., Math.min(1., distanceBlocks / 64.),
            Math.min(1., evidenceAgeTicks / 600.), Math.min(1., competitors / 16.), partnerSuccess));
        for (Kind candidate : Kind.values()) values.add(candidate == kind ? 1. : 0.);
        return new Features(values);
    }
    /** Only this actor's own settled interactions inform its partner statistic. */
    public synchronized double partnerSuccess(UUID citizen, UUID partner) {
        Objects.requireNonNull(citizen);
        if (partner == null) return .5;
        long count = 0, completed = 0;
        for (ServiceOutcome sample : services.values()) if (sample.citizen().equals(citizen) && partner.equals(sample.partner())) {
            count++; if (sample.outcome().completed()) completed++;
        }
        return (completed + 1.) / (count + 2.);
    }
    public synchronized Score score(Candidate candidate) {
        Objects.requireNonNull(candidate); double[] x = candidate.features().vector();
        double ticks = Math.max(0., Math.min(24000., duration.predict(x) * DURATION_SCALE));
        double personal = Math.max(0., cost.predict(x));
        double completion = Math.max(0., Math.min(1., success.predict(x)));
        double produced = production.isEmpty() ? 0. : Math.max(0., output.predict(x));
        double value = completion * (candidate.authoredPrior() + produced) - TIME_COST_PER_TICK * ticks - personal;
        return new Score(candidate.id(), candidate.authoredPrior(), produced, ticks, personal,
            completion, value, services.size(), production.size());
    }
    public synchronized Candidate choose(List<Candidate> candidates) {
        Objects.requireNonNull(candidates);
        if (candidates.stream().map(Candidate::id).distinct().count() != candidates.size())
            throw new IllegalArgumentException("Duplicate candidate identity");
        return candidates.stream().min(Comparator.<Candidate>comparingDouble(c -> -score(c).total())
            .thenComparing(Candidate::id)).orElse(null);
    }
    public synchronized boolean recordService(ServiceOutcome receipt) {
        Objects.requireNonNull(receipt);
        if (!scope.equals(receipt.scope())) throw new IllegalArgumentException("Foreign service learning scope");
        ServiceOutcome prior = services.get(receipt.id());
        if (prior != null) {
            if (!prior.equals(receipt)) throw new IllegalStateException("Conflicting service learning receipt");
            return false;
        }
        if (services.size() >= MAX_SAMPLES || serviceForCommitment.containsKey(receipt.commitment())
                || (receipt.job() != null && serviceForJob.containsKey(receipt.job())))
            throw new IllegalStateException("Duplicate commitment/job or exhausted learning ledger");
        double[] x = receipt.features().vector();
        duration.fit(x, (receipt.finishedTick() - receipt.startedTick()) / DURATION_SCALE);
        cost.fit(x, receipt.personalCost()); success.fit(x, receipt.outcome().completed() ? 1. : 0.);
        services.put(receipt.id(), receipt); serviceForCommitment.put(receipt.commitment(), receipt.id());
        if (receipt.job() != null) serviceForJob.put(receipt.job(), receipt.id());
        return true;
    }
    public synchronized boolean recordProduction(ProductionReceipt receipt) {
        Objects.requireNonNull(receipt);
        if (!scope.equals(receipt.scope())) throw new IllegalArgumentException("Foreign production scope");
        ProductionReceipt prior = production.get(receipt.id());
        if (prior != null) {
            if (!prior.equals(receipt)) throw new IllegalStateException("Conflicting production settlement");
            return false;
        }
        ServiceOutcome service = services.get(serviceForCommitment.get(receipt.commitment()));
        if (service == null || service.outcome() != Outcome.VERIFIED_TRANSFER || service.job() == null
                || !service.job().equals(receipt.job()) || !service.citizen().equals(receipt.citizen())
                || receipt.tick() < service.finishedTick() || physicalEvidence.containsKey(receipt.physicalEvidence())
                || producedByCommitment.containsKey(receipt.commitment())
                || production.size() >= MAX_SAMPLES)
            throw new IllegalStateException("Production is not independently linked to a settled transfer");
        output.fit(service.features().vector(), receipt.units());
        producedByCommitment.put(receipt.commitment(), receipt.units());
        production.put(receipt.id(), receipt); physicalEvidence.put(receipt.physicalEvidence(), receipt.id());
        return true;
    }
    public synchronized Status status() {
        long units = production.values().stream().mapToLong(ProductionReceipt::units).sum();
        String mode = services.isEmpty() ? "AUTHORED_PRIORS_ONLY" : production.isEmpty()
            ? "SERVICE_DURATION_COST_COMPLETION_ONLY" : "SETTLED_SERVICE_AND_VERIFIED_OUTPUT";
        return new Status(services.size(), production.size(), units, mode, !production.isEmpty());
    }
    /** Copies only: callers cannot mutate learned tensors through this audit. */
    public synchronized Map<String, List<Double>> parameters() {
        var result = new LinkedHashMap<String, List<Double>>();
        result.put("duration", doubles(duration.weights)); result.put("cost", doubles(cost.weights));
        result.put("completion", doubles(success.weights)); result.put("production", doubles(output.weights));
        return Map.copyOf(result);
    }
    private static List<Double> doubles(double[] values) {
        var result = new ArrayList<Double>(); for (double value : values) result.add(value); return List.copyOf(result);
    }
    public synchronized Snapshot snapshot() {
        return new Snapshot(SCHEMA_VERSION, scope, FEATURE_NAMES, List.copyOf(services.values()), List.copyOf(production.values()));
    }
    /** Rebuild small regressions deterministically from the retained settled ledger. */
    public static ServiceValueLearner restore(Snapshot snapshot, Scope expected, long now) {
        Objects.requireNonNull(snapshot);
        if (now < 0 || !snapshot.scope().equals(expected)) throw new IllegalArgumentException("Invalid restored learning scope/tick");
        var result = new ServiceValueLearner(expected);
        for (ServiceOutcome receipt : snapshot.services()) {
            if (receipt.finishedTick() > now || !result.recordService(receipt))
                throw new IllegalArgumentException("Future or duplicate restored service sample");
        }
        for (ProductionReceipt receipt : snapshot.production()) {
            if (receipt.tick() > now || !result.recordProduction(receipt))
                throw new IllegalArgumentException("Future or duplicate restored production sample");
        }
        return result;
    }
}
