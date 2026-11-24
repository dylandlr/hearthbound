package dev.hearthbound.civilization;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import dev.hearthbound.civilization.ServiceValueLearner.*;
import dev.hearthbound.civilization.CitizenServiceLearning.Decision;

/** Private-learning and replay contracts; DTOs here are not Minecraft witnesses. */
public final class CitizenServiceLearningTest {
    static UUID id(String name) { return UUID.nameUUIDFromBytes(name.getBytes(StandardCharsets.UTF_8)); }
    static void check(boolean condition) { if (!condition) throw new AssertionError(); }
    static void reject(Runnable action) {
        try { action.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("Expected rejection of invalid private learning evidence");
    }
    static final Scope SCOPE = new Scope(id("private-learning-world"), "minecraft:overworld");
    static final UUID A = id("citizen-a"), B = id("citizen-b"), PARTNER = id("partner"), NEED = id("flour-need");
    static Candidate candidate(String name, UUID citizen, Kind kind) {
        return new Candidate(name, citizen, NEED, PARTNER, kind,
            ServiceValueLearner.features(kind, 3, 10, 0, 0, .5), 1.);
    }
    static ProductionReceipt output(String name, UUID commitment, UUID job, long tick, int units) {
        return new ProductionReceipt(id(name), SCOPE, "create-final-output:" + name, commitment, A, job, tick, units);
    }
    static void capturedContextAndRealRankingChange() {
        var model = new CitizenServiceLearning(SCOPE, A);
        Candidate supply = candidate("a-supply", A, Kind.SUPPLY_WHEAT);
        Candidate observe = candidate("b-observe", A, Kind.OBSERVE_BUFFER);
        check(model.choose(List.of(observe, supply)).equals(supply));
        var initial = model.parameters();
        Decision d = model.begin(id("option-one"), supply, 10);
        check(d.commitment() == null && d.job() == null && d.startedTick() == 10);
        check(model.parameters().equals(initial));
        check(model.status().serviceSamples() == 0);
        check(model.begin(d.optionId(), supply, 10).equals(d));
        reject(() -> model.begin(id("second-before-finish"), observe, 11));
        model.bind(d.optionId(), id("commitment-one"), id("job-one"), 12);
        check(model.bind(d.optionId(), id("commitment-one"), id("job-one"), 13).boundTick() == 12);
        reject(() -> model.bind(d.optionId(), id("another-commitment"), id("job-one"), 14));
        check(model.settle(d.optionId(), id("service-one"), 1210, 2., Outcome.VERIFIED_TRANSFER));
        var actual = model.serviceOutcome(d.optionId());
        check(actual.startedTick() == 10 && actual.finishedTick() == 1210);
        check(actual.features().equals(supply.features()) && actual.partner().equals(PARTNER));
        check(model.choose(List.of(supply, observe)).equals(observe));
        check(model.status().productionSamples() == 0); // Missing output is unknown, not zero output.
        check(model.active() == null);
        reject(() -> model.begin(id("time-travel-decision"), observe, 1209));
        check(!model.settle(d.optionId(), id("service-one"), 1210, 2., Outcome.VERIFIED_TRANSFER));
        reject(() -> model.settle(d.optionId(), id("conflicting-service"), 1210, 2., Outcome.VERIFIED_TRANSFER));
    }
    static void finalizationPreflightAndOutputPrivacy() {
        var model = new CitizenServiceLearning(SCOPE, A);
        var supply = candidate("supply", A, Kind.SUPPLY_WHEAT);
        UUID option = id("production-option"), commitment = id("production-commitment"), job = id("production-job");
        model.begin(option, supply, 10); model.bind(option, commitment, job, 11);
        var output = output("verified-flour", commitment, job, 300, 3);
        var before = model.snapshot();
        reject(() -> model.recordProduction(output));
        model.validateSettlement(option, id("final-service"), 300, .4, Outcome.VERIFIED_TRANSFER, output);
        check(model.snapshot().equals(before)); // Preflight cannot train or settle custody.
        var bad = new ProductionReceipt(id("foreign-owner"), SCOPE, "foreign-output", commitment, B, job, 300, 3);
        reject(() -> model.validateSettlement(option, id("final-service"), 300, .4, Outcome.VERIFIED_TRANSFER, bad));
        reject(() -> model.validateSettlement(option, id("final-service"), 300, .4, Outcome.VERIFIED_TRANSFER,
            output("wrong-job", commitment, id("wrong-job"), 300, 3)));
        check(model.snapshot().equals(before));
        model.settle(option, id("final-service"), 300, .4, Outcome.VERIFIED_TRANSFER);
        check(model.recordProduction(output));
        check(!model.recordProduction(output));
        check(model.status().independentlyVerifiedOutputUnits() == 3);
        check(model.score(supply).learnedProductionUnits() > 0);
        for (Kind kind : List.of(Kind.CARRY_REQUEST, Kind.OBSERVE_BUFFER, Kind.WAIT))
            check(model.score(candidate("no-borrowed-output:" + kind, A, kind)).learnedProductionUnits() == 0);
        reject(() -> model.recordProduction(bad));
        reject(() -> model.score(candidate("foreign-score", B, Kind.WAIT)));
        reject(() -> model.choose(List.of(supply, candidate("foreign-choice", B, Kind.CARRY_REQUEST))));
        reject(() -> model.begin(id("foreign-option"), candidate("foreign-start", B, Kind.WAIT), 301));
        var other = new CitizenServiceLearning(SCOPE, B);
        check(other.status().serviceSamples() == 0 && other.status().productionSamples() == 0);
        check(other.partnerSuccess(PARTNER) == .5);
    }
    static CitizenServiceLearning completedAndPending() {
        var model = new CitizenServiceLearning(SCOPE, A);
        var supply = candidate("persist-supply", A, Kind.SUPPLY_WHEAT);
        model.begin(id("persist-option"), supply, 10);
        model.bind(id("persist-option"), id("persist-commitment"), id("persist-job"), 12);
        model.settle(id("persist-option"), id("persist-service"), 100, .1, Outcome.VERIFIED_TRANSFER);
        model.recordProduction(output("persist-output", id("persist-commitment"), id("persist-job"), 100, 2));
        var observe = candidate("persist-observe", A, Kind.OBSERVE_BUFFER);
        Decision second = model.begin(id("persist-second"), observe, 110);
        check(second.commitment().equals(second.optionId()) && second.job() == null);
        model.settle(second.optionId(), id("persist-observation"), 150, 0, Outcome.VERIFIED_OBSERVATION);
        model.begin(id("persist-unresolved"), candidate("unresolved-supply", A, Kind.SUPPLY_WHEAT), 160);
        model.bind(id("persist-unresolved"), id("unresolved-commitment"), id("unresolved-job"), 162);
        return model;
    }
    static void exactReplayAndUncertainWorkStaysUntrained() {
        var model = completedAndPending(); var snapshot = model.snapshot();
        var restored = CitizenServiceLearning.restore(snapshot, SCOPE, A, 200);
        check(restored.snapshot().equals(snapshot));
        check(restored.parameters().equals(model.parameters()));
        check(restored.active().equals(model.active()));
        check(restored.status().serviceSamples() == 2 && restored.status().productionSamples() == 1);
        reject(() -> restored.begin(id("cannot-replace-unresolved"), candidate("another", A, Kind.WAIT), 201));
        reject(() -> CitizenServiceLearning.restore(snapshot, SCOPE, B, 200));
        reject(() -> CitizenServiceLearning.restore(snapshot, new Scope(id("foreign-world"), "minecraft:overworld"), A, 200));
        reject(() -> CitizenServiceLearning.restore(snapshot, SCOPE, A, 161));
        check(restored.score(candidate("after-restart", A, Kind.SUPPLY_WHEAT))
            .equals(model.score(candidate("after-restart", A, Kind.SUPPLY_WHEAT))));
    }
    static void corruptedDecisionOrForeignReplayRejected() {
        var snapshot = completedAndPending().snapshot();
        var decisions = new ArrayList<>(snapshot.decisions()); Decision d = decisions.get(0); Score s = d.selectedScore();
        var changed = new Score(s.candidateId(), s.authoredPrior(), s.learnedProductionUnits(), s.estimatedDurationTicks(),
            s.estimatedPersonalCost(), s.estimatedSuccess(), s.total() + 1, s.serviceSamples(), s.productionSamples());
        decisions.set(0, new Decision(d.optionId(), d.candidate(), changed, d.startedTick(), d.commitment(), d.job(), d.boundTick()));
        var altered = new CitizenServiceLearning.Snapshot(1, SCOPE, A, decisions, snapshot.learner());
        reject(() -> CitizenServiceLearning.restore(altered, SCOPE, A, 200));
        var missing = new CitizenServiceLearning.Snapshot(1, SCOPE, A, snapshot.decisions().subList(1, 3), snapshot.learner());
        reject(() -> CitizenServiceLearning.restore(missing, SCOPE, A, 200));
        var samples = new ArrayList<>(snapshot.learner().services()); ServiceOutcome r = samples.get(0);
        samples.set(0, new ServiceOutcome(r.id(), r.scope(), r.commitment(), B, r.job(), r.kind(), r.partner(),
            r.features(), r.startedTick(), r.finishedTick(), r.personalCost(), r.outcome()));
        var foreignBase = new ServiceValueLearner.Snapshot(1, SCOPE, ServiceValueLearner.FEATURE_NAMES,
            samples, snapshot.learner().production());
        var foreign = new CitizenServiceLearning.Snapshot(1, SCOPE, A, snapshot.decisions(), foreignBase);
        reject(() -> CitizenServiceLearning.restore(foreign, SCOPE, A, 200));
    }
    static void safeFailureNeedsNoFabricatedJob() {
        var model = new CitizenServiceLearning(SCOPE, A);
        UUID option = id("rejected-before-motor");
        model.begin(option, candidate("unaccepted-supply", A, Kind.SUPPLY_WHEAT), 10);
        reject(() -> model.settle(option, id("cannot-complete"), 20, 0, Outcome.VERIFIED_TRANSFER));
        model.settle(option, id("safe-no-cargo-failure"), 20, 0, Outcome.VERIFIED_FAILURE_NO_CARGO);
        check(model.serviceOutcome(option).commitment().equals(option));
        check(model.serviceOutcome(option).job() == null);
        check(model.status().serviceSamples() == 1 && model.status().productionSamples() == 0);
        check(CitizenServiceLearning.restore(model.snapshot(), SCOPE, A, 20).snapshot().equals(model.snapshot()));
    }
    public static void main(String[] args) {
        capturedContextAndRealRankingChange(); finalizationPreflightAndOutputPrivacy();
        exactReplayAndUncertainWorkStaysUntrained(); corruptedDecisionOrForeignReplayRejected();
        safeFailureNeedsNoFabricatedJob();
        System.out.println("Citizen service learning: PASS (private decisions, full-duration outcomes, output gate, exact replay)");
    }
}
