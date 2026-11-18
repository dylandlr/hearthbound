package dev.hearthbound.civilization;

import java.util.*;
import dev.hearthbound.civilization.CivilizationContracts.*;

public final class CivilizationContractsTest {
  private static final UUID SELF = new UUID(1L, 1L);
  private static final UUID SCOUT = new UUID(1L, 2L);
  private static final UUID EPISODE = new UUID(2L, 1L);
  private static final UUID OTHER_EPISODE = new UUID(2L, 2L);
  private static final Set<ActionKind> ACTIONS = Set.of(ActionKind.GATHER, ActionKind.OBSERVE,
      ActionKind.WAIT, ActionKind.EXPLORE);
  private static int checks;

  private static void verify(String name, boolean yes) {
    checks++;
    if (!yes) throw new AssertionError(name);
  }

  private static void reject(String name, Runnable action) {
    checks++;
    try {
      action.run();
    } catch (IllegalArgumentException expected) {
      return;
    }
    throw new AssertionError("Expected rejection: " + name);
  }

  private static Evidence direct(long id, String target, long observed, int quantity, long revision) {
    return new Evidence(new UUID(3L, id), SELF, SELF, target, EvidenceKind.DIRECT,
        observed, observed, quantity, EPISODE, revision);
  }

  private static Observation observation(long tick, long revision, Evidence... evidence) {
    return new Observation(SELF, tick, List.of(evidence), ACTIONS, EPISODE, revision);
  }

  private static Decision decision(Observation o, ActionKind action, String target, UUID evidence) {
    return new Decision(new UUID(4L, 1L), SELF, action, target, evidence,
        o.tick(), o.episodeId(), o.snapshotRevision());
  }

  public static void main(String[] args) {
    ScriptedPolicy policy = new ScriptedPolicy();
    Evidence resource = direct(1L, "chest-A", 10L, 3, 1L);
    Evidence report = new Evidence(new UUID(3L, 2L), SCOUT, SELF, "chest-B",
        EvidenceKind.REPORTED, 10L, 11L, 4, EPISODE, 99L);
    Observation first = observation(12L, 2L, resource, report);
    Decision gather = policy.decide(first);
    CivilizationContracts.validateAt(first, gather, 12L);
    verify("policy gathers known resource", gather.action() == ActionKind.GATHER);
    verify("policy copies episode", gather.episodeId().equals(EPISODE));
    verify("policy copies snapshot revision", gather.snapshotRevision() == 2L);

    reject("same evidence ID cannot authorize another target", () ->
        CivilizationContracts.validate(first,
            decision(first, ActionKind.GATHER, "chest-B", resource.id())));
    reject("unknown evidence", () -> CivilizationContracts.validate(first,
        decision(first, ActionKind.GATHER, "chest-A", new UUID(9L, 9L))));
    reject("missing gather evidence", () -> CivilizationContracts.validate(first,
        decision(first, ActionKind.GATHER, "chest-A", null)));
    reject("missing gather target", () -> CivilizationContracts.validate(first,
        decision(first, ActionKind.GATHER, null, resource.id())));
    reject("reported stock cannot authorize gather", () -> CivilizationContracts.validate(first,
        decision(first, ActionKind.GATHER, report.target(), report.id())));
    Evidence inferred = new Evidence(new UUID(3L, 3L), SCOUT, SELF, "chest-C",
        EvidenceKind.INFERRED, 10L, 11L, 5, EPISODE, 3L);
    Observation inference = observation(12L, 2L, inferred);
    reject("inferred stock cannot authorize gather", () -> CivilizationContracts.validate(inference,
        decision(inference, ActionKind.GATHER, inferred.target(), inferred.id())));
    reject("another agent cannot fabricate direct provenance", () -> new Evidence(new UUID(3L, 4L),
        SCOUT, SELF, "chest-A", EvidenceKind.DIRECT, 10L, 10L, 3, EPISODE, 1L));

    Observation reportOnly = observation(12L, 2L, report);
    Decision inspect = policy.decide(reportOnly);
    CivilizationContracts.validate(reportOnly, inspect);
    verify("report leads to investigation", inspect.action() == ActionKind.OBSERVE);
    Observation oldReport = observation(100L, 3L, report);
    Decision oldInspect = policy.decide(oldReport);
    CivilizationContracts.validateAt(oldReport, oldInspect, 150L);
    verify("old report can still prompt inspection", oldInspect.action() == ActionKind.OBSERVE);
    reject("inspection target must match its evidence", () -> CivilizationContracts.validate(oldReport,
        decision(oldReport, ActionKind.OBSERVE, "chest-Z", report.id())));

    // A finding from another agent's revision 99 can be received in our revision 2.
    verify("reported origin revision is not receiving revision", reportOnly.evidence().get(0)
        .snapshotRevision() == 99L);
    reject("future personal observation revision", () -> observation(12L, 0L, resource));
    reject("future evidence tick", () -> observation(9L, 2L, resource));
    reject("future receipt tick", () -> new Observation(SELF, 10L, List.of(report),
        ACTIONS, EPISODE, 2L));
    reject("duplicate fact identity", () -> observation(12L, 2L, resource, resource));
    reject("other recipient", () -> new Observation(SCOUT, 12L, List.of(resource),
        ACTIONS, EPISODE, 2L));
    reject("cross-episode evidence", () -> new Observation(SELF, 12L, List.of(resource),
        ACTIONS, OTHER_EPISODE, 2L));
    reject("cross-episode decision with same tick and agent", () -> CivilizationContracts.validate(first,
        new Decision(gather.id(), SELF, gather.action(), gather.target(), gather.evidenceId(),
            gather.tick(), OTHER_EPISODE, gather.snapshotRevision())));
    Observation sameTickNewSnapshot = observation(12L, 3L, resource, report);
    reject("same tick does not authorize prior snapshot decision", () ->
        CivilizationContracts.validate(sameTickNewSnapshot, gather));
    reject("decision from future tick", () -> CivilizationContracts.validate(first,
        new Decision(gather.id(), SELF, gather.action(), gather.target(), gather.evidenceId(),
            13L, EPISODE, 2L)));
    reject("execution precedes snapshot", () -> CivilizationContracts.validateAt(first, gather, 11L));

    CivilizationContracts.validateAt(first, gather, 30L);
    verify("inclusive freshness boundary", true);
    reject("fresh decision cannot execute after evidence expires", () ->
        CivilizationContracts.validateAt(first, gather, 31L));
    Observation stale = observation(31L, 3L, resource);
    reject("stale direct evidence", () -> CivilizationContracts.validate(stale,
        decision(stale, ActionKind.GATHER, resource.target(), resource.id())));
    verify("scripted policy does not gather stale stock", policy.decide(stale).action()
        == ActionKind.EXPLORE);
    CivilizationContracts.validate(stale,
        decision(stale, ActionKind.OBSERVE, resource.target(), resource.id()));

    Evidence depleted = direct(5L, "chest-A", 11L, 0, 2L);
    Observation updated = observation(12L, 3L, resource, depleted);
    reject("new zero-stock observation supersedes old positive stock", () ->
        CivilizationContracts.validate(updated,
            decision(updated, ActionKind.GATHER, resource.target(), resource.id())));
    verify("scripted policy respects depletion", policy.decide(updated).action() == ActionKind.EXPLORE);
    Observation reverse = observation(12L, 3L, depleted, resource);
    verify("depletion is respected independently of evidence ordering", policy.decide(reverse).action()
        == ActionKind.EXPLORE);
    Evidence sameTickDepleted = direct(6L, "chest-A", 10L, 0, 2L);
    Observation revised = observation(12L, 3L, resource, sameTickDepleted);
    reject("same-tick later revision supersedes earlier observation", () ->
        CivilizationContracts.validate(revised,
            decision(revised, ActionKind.GATHER, resource.target(), resource.id())));
    Evidence conflict = direct(7L, "chest-A", 10L, 0, 1L);
    reject("conflicting direct observations at identical scope", () ->
        observation(12L, 3L, resource, conflict));

    Observation none = observation(12L, 2L);
    Decision explore = policy.decide(none);
    CivilizationContracts.validate(none, explore);
    verify("withheld reports retain exploration", explore.action() == ActionKind.EXPLORE);
    verify("explore has no hidden target", explore.target() == null && explore.evidenceId() == null);
    reject("explore cannot smuggle a target", () -> CivilizationContracts.validate(none,
        decision(none, ActionKind.EXPLORE, "unseen-chest", null)));
    reject("wait cannot carry evidence", () -> CivilizationContracts.validate(first,
        decision(first, ActionKind.WAIT, null, resource.id())));
    Observation waitOnly = new Observation(SELF, 12L, List.of(), Set.of(ActionKind.WAIT), EPISODE, 2L);
    verify("wait fallback remains available", policy.decide(waitOnly).action() == ActionKind.WAIT);
    reject("unsupported capability", () -> CivilizationContracts.validate(waitOnly,
        decision(waitOnly, ActionKind.GATHER, resource.target(), resource.id())));
    Observation futureActions = new Observation(SELF, 12L, List.of(resource),
        Set.of(ActionKind.DELIVER, ActionKind.COMMUNICATE), EPISODE, 2L);
    reject("delivery requires a complete contract", () -> CivilizationContracts.validate(futureActions,
        decision(futureActions, ActionKind.DELIVER, resource.target(), resource.id())));
    reject("communication requires a complete contract", () -> CivilizationContracts.validate(futureActions,
        decision(futureActions, ActionKind.COMMUNICATE, resource.target(), resource.id())));

    Evidence legacyEvidence = new Evidence(new UUID(5L, 1L), SELF, SELF, "legacy-chest",
        EvidenceKind.DIRECT, 10L, 10L, 3);
    Observation legacy = new Observation(SELF, 12L, List.of(legacyEvidence),
        Set.of(ActionKind.GATHER, ActionKind.OBSERVE, ActionKind.WAIT));
    Decision legacyGather = policy.decide(legacy);
    CivilizationContracts.validate(legacy, legacyGather);
    Decision legacyDecision = new Decision(new UUID(5L, 2L), SELF, ActionKind.GATHER,
        legacyEvidence.target(), legacyEvidence.id(), 12L);
    CivilizationContracts.validate(legacy, legacyDecision);
    verify("old constructors retain legacy scope", legacyGather.episodeId()
        .equals(CivilizationContracts.LEGACY_EPISODE_ID));
    verify("legacy wait behavior is preserved", policy.decide(new Observation(SELF, 12L,
        List.of(), Set.of(ActionKind.WAIT))).action() == ActionKind.WAIT);
    verify("acceptance remains distinct from verified effect",
        !new Outcome(gather.id(), true, false, 13L, 0).worldEffectVerified());

    System.out.println("Civilization contracts: PASS (" + checks + " checks; contract reference only)");
  }
}
