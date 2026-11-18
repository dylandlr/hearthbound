package dev.hearthbound.civilization;

import java.util.*;

public final class CivilizationContracts {
  private CivilizationContracts() {}

  /** Compatibility scope only. Live adapters must supply an explicit episode and revision. */
  public static final UUID LEGACY_EPISODE_ID = new UUID(0L, 0L);
  /** Provisional policy contract; this is not evidence of a calibrated Minecraft sensing window. */
  public static final long MAX_GATHER_EVIDENCE_AGE_TICKS = 20L;

  public enum EvidenceKind { DIRECT, REPORTED, INFERRED }
  public enum ActionKind { OBSERVE, GATHER, DELIVER, COMMUNICATE, WAIT, EXPLORE }

  /** snapshotRevision is the revision of the originating observation, not the recipient's inbox. */
  public record Evidence(UUID id, UUID sourceAgent, UUID recipient, String target,
                         EvidenceKind kind, long observedTick, long receivedTick, int quantity,
                         UUID episodeId, long snapshotRevision) {
    public Evidence(UUID id, UUID sourceAgent, UUID recipient, String target,
                    EvidenceKind kind, long observedTick, long receivedTick, int quantity) {
      this(id, sourceAgent, recipient, target, kind, observedTick, receivedTick, quantity,
          LEGACY_EPISODE_ID, 0L);
    }

    public Evidence {
      Objects.requireNonNull(id);
      Objects.requireNonNull(sourceAgent);
      Objects.requireNonNull(recipient);
      Objects.requireNonNull(target);
      Objects.requireNonNull(kind);
      Objects.requireNonNull(episodeId);
      if (target.isBlank() || observedTick < 0 || receivedTick < observedTick
          || quantity < 0 || snapshotRevision < 0) {
        throw new IllegalArgumentException("Invalid evidence");
      }
      if (kind == EvidenceKind.DIRECT && !sourceAgent.equals(recipient)) {
        throw new IllegalArgumentException("Direct evidence must be a personal observation");
      }
    }
  }

  public record Observation(UUID agentId, long tick, List<Evidence> evidence,
                            Set<ActionKind> allowedActions, UUID episodeId,
                            long snapshotRevision) {
    public Observation(UUID agentId, long tick, List<Evidence> evidence,
                       Set<ActionKind> allowedActions) {
      this(agentId, tick, evidence, allowedActions, LEGACY_EPISODE_ID, 0L);
    }

    public Observation {
      Objects.requireNonNull(agentId);
      Objects.requireNonNull(episodeId);
      evidence = List.copyOf(evidence);
      allowedActions = Set.copyOf(allowedActions);
      if (tick < 0 || snapshotRevision < 0 || allowedActions.isEmpty()) {
        throw new IllegalArgumentException("Invalid observation");
      }
      Set<UUID> ids = new HashSet<>();
      for (Evidence e : evidence) {
        if (!agentId.equals(e.recipient()) || !episodeId.equals(e.episodeId())
            || e.receivedTick() > tick || e.observedTick() > tick || !ids.add(e.id())
            || (e.kind() == EvidenceKind.DIRECT && e.snapshotRevision() > snapshotRevision)) {
          throw new IllegalArgumentException("Inaccessible evidence");
        }
        for (Evidence other : evidence) {
          if (e != other && e.kind() == EvidenceKind.DIRECT
              && other.kind() == EvidenceKind.DIRECT && e.target().equals(other.target())
              && e.observedTick() == other.observedTick()
              && e.snapshotRevision() == other.snapshotRevision()
              && e.quantity() != other.quantity()) {
            throw new IllegalArgumentException("Conflicting direct observations");
          }
        }
      }
    }
  }

  public record Decision(UUID id, UUID agentId, ActionKind action, String target,
                         UUID evidenceId, long tick, UUID episodeId, long snapshotRevision) {
    public Decision(UUID id, UUID agentId, ActionKind action, String target,
                    UUID evidenceId, long tick) {
      this(id, agentId, action, target, evidenceId, tick, LEGACY_EPISODE_ID, 0L);
    }

    public Decision {
      Objects.requireNonNull(id);
      Objects.requireNonNull(agentId);
      Objects.requireNonNull(action);
      Objects.requireNonNull(episodeId);
      if (tick < 0 || snapshotRevision < 0) throw new IllegalArgumentException("Invalid decision");
    }
  }

  public record Outcome(UUID decisionId, boolean accepted, boolean worldEffectVerified,
                        long completedTick, int itemDelta) {
    public Outcome {
      Objects.requireNonNull(decisionId);
      if (completedTick < 0 || (worldEffectVerified && !accepted)) {
        throw new IllegalArgumentException("Invalid outcome");
      }
    }
  }

  public interface AgentPolicy { Decision decide(Observation observation); }

  /** Decision-time check retained for callers; live dispatch must use validateAt with server time. */
  public static void validate(Observation o, Decision d) {
    validateAt(o, d, o.tick());
  }

  /**
   * Checks observation authority and evidence age, not current world stock or reachability.
   * The executor must supply authoritative time and revalidate world preconditions before mutation.
   */
  public static void validateAt(Observation o, Decision d, long executionTick) {
    Objects.requireNonNull(o);
    Objects.requireNonNull(d);
    if (!o.agentId().equals(d.agentId()) || o.tick() != d.tick()
        || !o.episodeId().equals(d.episodeId()) || o.snapshotRevision() != d.snapshotRevision()
        || !o.allowedActions().contains(d.action()) || executionTick < o.tick()) {
      throw new IllegalArgumentException("Invalid action scope or execution time");
    }
    if (d.action() == ActionKind.WAIT || d.action() == ActionKind.EXPLORE) {
      if (d.target() != null || d.evidenceId() != null) {
        throw new IllegalArgumentException("Fallback action must not reference a target");
      }
      return;
    }
    if (d.action() == ActionKind.DELIVER || d.action() == ActionKind.COMMUNICATE) {
      throw new IllegalArgumentException("Action needs an explicit contract before execution");
    }
    Evidence e = o.evidence().stream().filter(x -> x.id().equals(d.evidenceId()))
        .findFirst().orElseThrow(() -> new IllegalArgumentException("Unknown evidence"));
    if (!e.target().equals(d.target())) throw new IllegalArgumentException("Evidence-target mismatch");
    if (d.action() == ActionKind.OBSERVE) {
      // An old report is a reason to investigate, never proof of present stock.
      return;
    }
    if (!canGather(o, e, executionTick)) {
      throw new IllegalArgumentException("Gather requires the latest fresh positive personal observation");
    }
  }

  private static boolean canGather(Observation o, Evidence e, long executionTick) {
    if (e.kind() != EvidenceKind.DIRECT || !e.sourceAgent().equals(o.agentId())
        || e.quantity() <= 0 || executionTick < e.observedTick()
        || executionTick - e.observedTick() > MAX_GATHER_EVIDENCE_AGE_TICKS) return false;
    return o.evidence().stream().noneMatch(other -> other.kind() == EvidenceKind.DIRECT
        && other.sourceAgent().equals(o.agentId()) && other.target().equals(e.target())
        && (other.observedTick() > e.observedTick()
            || (other.observedTick() == e.observedTick()
                && other.snapshotRevision() > e.snapshotRevision())));
  }

  public static final class ScriptedPolicy implements AgentPolicy {
    public Decision decide(Observation o) {
      if (o.allowedActions().contains(ActionKind.GATHER)) {
        for (Evidence e : o.evidence()) {
          if (canGather(o, e, o.tick())) return make(o, ActionKind.GATHER, e);
        }
      }
      if (o.allowedActions().contains(ActionKind.OBSERVE)) {
        for (Evidence e : o.evidence()) {
          if (e.kind() == EvidenceKind.REPORTED && !e.sourceAgent().equals(o.agentId())
              && e.quantity() > 0) return make(o, ActionKind.OBSERVE, e);
        }
      }
      if (o.allowedActions().contains(ActionKind.EXPLORE)) return make(o, ActionKind.EXPLORE, null);
      if (o.allowedActions().contains(ActionKind.WAIT)) return make(o, ActionKind.WAIT, null);
      throw new IllegalStateException("No safe fallback");
    }

    private Decision make(Observation o, ActionKind a, Evidence e) {
      return new Decision(UUID.randomUUID(), o.agentId(), a, e == null ? null : e.target(),
          e == null ? null : e.id(), o.tick(), o.episodeId(), o.snapshotRevision());
    }
  }
}
