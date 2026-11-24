package dev.hearthbound.civilization;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import dev.hearthbound.civilization.ServiceValueLearner.*;

/** Numerical and evidence contracts only; these constructed DTOs are not Minecraft evidence. */
public final class ServiceValueLearnerTest {
    static UUID id(String name) { return UUID.nameUUIDFromBytes(name.getBytes(StandardCharsets.UTF_8)); }
    static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    static void close(double actual, double expected) {
        if (Math.abs(actual - expected) > 1e-10) throw new AssertionError(actual + " != " + expected);
    }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("Expected invalid learning evidence to be rejected");
    }
    static final Scope SCOPE = new Scope(id("value-world"), "minecraft:overworld");
    static final UUID CITIZEN = id("worker"), PARTNER = id("requester"), NEED = id("need");
    static Features features(Kind kind) { return ServiceValueLearner.features(kind, 2, 1., 0, 0, .5); }
    static Candidate candidate(String name, Kind kind) {
        return new Candidate(name, CITIZEN, NEED, PARTNER, kind, features(kind), 1.);
    }
    static ServiceOutcome service(String name, long duration, double cost, Outcome outcome) {
        return new ServiceOutcome(id(name), SCOPE, id(name + "-commitment"), CITIZEN,
            id(name + "-job"), Kind.SUPPLY_WHEAT, PARTNER, features(Kind.SUPPLY_WHEAT),
            10, 10 + duration, cost, outcome);
    }
    static ProductionReceipt production(String name, ServiceOutcome service) {
        return new ProductionReceipt(id(name), SCOPE, "create-physical-event:" + name,
            service.commitment(), service.citizen(), service.job(), service.finishedTick() + 20, 1);
    }
    static double dot(List<Double> a, List<Double> b) {
        double result = 0.; for (int i = 0; i < a.size(); i++) result += a.get(i) * b.get(i); return result;
    }
    static void numericalUpdatesAndChoice() {
        var model = new ServiceValueLearner(SCOPE);
        Candidate supply = candidate("a-supply", Kind.SUPPLY_WHEAT);
        Candidate inspect = candidate("b-observe", Kind.OBSERVE_BUFFER);
        check(model.choose(List.of(inspect, supply)).equals(supply)); // Explicit deterministic tie rule.
        Map<String, List<Double>> before = model.parameters();
        ServiceOutcome actual = service("slow-service", 1200, 2., Outcome.VERIFIED_TRANSFER);
        check(model.recordService(actual));
        List<Double> x = actual.features().values();
        double denominator = 1 + dot(x, x);
        Map<String, List<Double>> after = model.parameters();
        for (String head : List.of("duration", "cost", "completion")) {
            double target = head.equals("duration") ? 1. : head.equals("cost") ? 2. : 1.;
            double error = target - dot(before.get(head), x);
            for (int i = 0; i < x.size(); i++)
                close(after.get(head).get(i), before.get(head).get(i) + x.get(i) / denominator * error);
        }
        check(model.choose(List.of(supply, inspect)).equals(inspect)); // Learned measured costs change ranking.
        check(model.score(supply).authoredPrior() == 1.);
        check(model.score(supply).estimatedDurationTicks() > 24.);
        check(model.score(supply).estimatedPersonalCost() > 0.);
        check(after.get("production").equals(before.get("production")));
        check(model.status().serviceSamples() == 1 && model.status().productionSamples() == 0);
        check(!model.status().productionLearningActive());
        check(model.status().learningScope().equals("SERVICE_DURATION_COST_COMPLETION_ONLY"));
        check(!model.recordService(actual));
        check(model.parameters().equals(after));
        reject(() -> model.recordService(new ServiceOutcome(id("duplicate-job"), SCOPE,
            actual.commitment(), actual.citizen(), actual.job(), actual.kind(), actual.partner(), actual.features(),
            actual.startedTick(), actual.finishedTick(), actual.personalCost(), actual.outcome())));
    }
    static void independentProductionAndIdempotence() {
        var model = new ServiceValueLearner(SCOPE);
        ServiceOutcome actual = service("productive-service", 100, .1, Outcome.VERIFIED_TRANSFER);
        ProductionReceipt output = production("actual-output", actual);
        reject(() -> model.recordProduction(output)); // No linked physical transfer yet.
        model.recordService(actual);
        check(model.score(candidate("supply", Kind.SUPPLY_WHEAT)).learnedProductionUnits() == 0.);
        check(model.recordProduction(output));
        var learned = model.parameters();
        check(model.status().productionSamples() == 1);
        check(model.status().independentlyVerifiedOutputUnits() == 1);
        check(model.status().productionLearningActive());
        check(model.score(candidate("supply", Kind.SUPPLY_WHEAT)).learnedProductionUnits() > 0.);
        check(!model.recordProduction(output));
        check(model.parameters().equals(learned));
        reject(() -> model.recordProduction(new ProductionReceipt(id("different-id-same-output"), SCOPE,
            output.physicalEvidence(), actual.commitment(), CITIZEN, actual.job(), output.tick(), 1)));
        reject(() -> model.recordProduction(new ProductionReceipt(id("second-chunk-same-commitment"), SCOPE,
            "different-physical-event", actual.commitment(), CITIZEN, actual.job(), output.tick()+1, 1)));
        reject(() -> model.recordProduction(new ProductionReceipt(output.id(), SCOPE,
            output.physicalEvidence(), actual.commitment(), CITIZEN, actual.job(), output.tick(), 2)));
        reject(() -> model.recordProduction(new ProductionReceipt(id("wrong-job"), SCOPE,
            "another-evidence", actual.commitment(), CITIZEN, id("not-the-physical-job"), output.tick(), 1)));
        reject(() -> model.recordProduction(new ProductionReceipt(id("early-output"), SCOPE,
            "too-early", actual.commitment(), CITIZEN, actual.job(), actual.finishedTick()-1, 1)));
        var canceled = service("canceled", 30, .02, Outcome.VERIFIED_NO_CARGO_CANCEL);
        model.recordService(canceled);
        reject(() -> model.recordProduction(production("cannot-credit-cancel", canceled)));
    }
    static void privatePartnerHistoryAndPersistentLearning() {
        var model = new ServiceValueLearner(SCOPE);
        close(model.partnerSuccess(CITIZEN, PARTNER), .5);
        var first = service("first", 100, .1, Outcome.VERIFIED_TRANSFER);
        var second = service("second", 200, .2, Outcome.VERIFIED_FAILURE_NO_CARGO);
        model.recordService(first);
        close(model.partnerSuccess(CITIZEN, PARTNER), 2. / 3.);
        close(model.partnerSuccess(id("another-worker"), PARTNER), .5);
        close(model.partnerSuccess(CITIZEN, id("unknown-partner")), .5);
        model.recordProduction(production("output-one", first));
        model.recordService(second);
        close(model.partnerSuccess(CITIZEN, PARTNER), .5);
        var snapshot = model.snapshot();
        var restored = ServiceValueLearner.restore(snapshot, SCOPE, 1000);
        check(restored.snapshot().equals(snapshot));
        check(restored.parameters().equals(model.parameters()));
        check(restored.score(candidate("supply", Kind.SUPPLY_WHEAT)).equals(model.score(candidate("supply", Kind.SUPPLY_WHEAT))));
        reject(() -> ServiceValueLearner.restore(snapshot, new Scope(id("other-world"), "minecraft:overworld"), 1000));
        reject(() -> ServiceValueLearner.restore(snapshot, SCOPE, 50));
        var duplicate = new Snapshot(snapshot.schemaVersion(), snapshot.scope(), snapshot.featureNames(),
            List.of(first, first), snapshot.production());
        reject(() -> ServiceValueLearner.restore(duplicate, SCOPE, 1000));
    }
    static void contractsRejectBadOrUncertainData() {
        var model = new ServiceValueLearner(SCOPE);
        check(model.status().learningScope().equals("AUTHORED_PRIORS_ONLY"));
        check(model.choose(List.of()) == null);
        reject(() -> model.choose(List.of(candidate("same", Kind.SUPPLY_WHEAT), candidate("same", Kind.OBSERVE_BUFFER))));
        reject(() -> ServiceValueLearner.features(Kind.SUPPLY_WHEAT, 2, Double.NaN, 0, 0, .5));
        reject(() -> new Candidate("bad-kind", CITIZEN, NEED, PARTNER, Kind.WAIT, features(Kind.SUPPLY_WHEAT), 1.));
        reject(() -> new ServiceOutcome(id("speech-is-not-transfer"), SCOPE, id("attempt"), CITIZEN, id("job"),
            Kind.CARRY_REQUEST, PARTNER, features(Kind.CARRY_REQUEST), 0, 10, .1, Outcome.VERIFIED_TRANSFER));
        var values = new ArrayList<>(features(Kind.SUPPLY_WHEAT).values()); values.set(1, Double.NaN);
        reject(() -> new Features(values));
        reject(() -> new ProductionReceipt(id("zero-without-output-proof"), SCOPE, "unknown", id("attempt"),
            CITIZEN, id("job"), 1, 0));
    }
    static void fastFailureDoesNotBecomeValuableBecauseItEndsQuickly() {
        var model = new ServiceValueLearner(SCOPE);
        Candidate failing = candidate("fast-failure", Kind.SUPPLY_WHEAT);
        Candidate reliable = candidate("slower-completion", Kind.OBSERVE_BUFFER);
        for (int i = 0; i < 20; i++) {
            model.recordService(service("fast-failure-" + i, 1, 0., Outcome.VERIFIED_FAILURE_NO_CARGO));
            model.recordService(new ServiceOutcome(id("observation-" + i), SCOPE, id("obs-option-" + i),
                CITIZEN, null, Kind.OBSERVE_BUFFER, PARTNER, features(Kind.OBSERVE_BUFFER),
                10, 110, 0., Outcome.VERIFIED_OBSERVATION));
        }
        check(model.score(failing).estimatedDurationTicks() < model.score(reliable).estimatedDurationTicks());
        check(model.score(failing).estimatedSuccess() < model.score(reliable).estimatedSuccess());
        check(model.choose(List.of(failing, reliable)).equals(reliable));
    }
    public static void main(String[] args) {
        numericalUpdatesAndChoice(); independentProductionAndIdempotence();
        privatePartnerHistoryAndPersistentLearning(); contractsRejectBadOrUncertainData();
        fastFailureDoesNotBecomeValuableBecauseItEndsQuickly();
        System.out.println("Service value learner: PASS (actual parameter/ranking updates, separate output evidence, replay)");
    }
}
