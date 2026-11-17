package dev.hearthbound.civilization;
import java.util.*;
public final class CivilizationContracts {
  private CivilizationContracts() {}
  public enum EvidenceKind { DIRECT, REPORTED, INFERRED }
  public enum ActionKind { OBSERVE, GATHER, DELIVER, COMMUNICATE, WAIT }
  public record Evidence(UUID id, UUID sourceAgent, UUID recipient, String target, EvidenceKind kind, long observedTick, long receivedTick, int quantity) {
    public Evidence {
      Objects.requireNonNull(id); Objects.requireNonNull(sourceAgent); Objects.requireNonNull(recipient); Objects.requireNonNull(target); Objects.requireNonNull(kind);
      if (target.isBlank() || observedTick < 0 || receivedTick < observedTick || quantity < 0) throw new IllegalArgumentException("Invalid evidence");
    }
  }
  public record Observation(UUID agentId, long tick, List<Evidence> evidence, Set<ActionKind> allowedActions) {
    public Observation {
      Objects.requireNonNull(agentId); evidence=List.copyOf(evidence); allowedActions=Set.copyOf(allowedActions);
      if (tick < 0 || allowedActions.isEmpty()) throw new IllegalArgumentException("Invalid observation");
      Set<UUID> ids=new HashSet<>();
      for (Evidence e:evidence) if (!agentId.equals(e.recipient()) || e.receivedTick()>tick || e.observedTick()>tick || !ids.add(e.id())) throw new IllegalArgumentException("Inaccessible evidence");
    }
  }
  public record Decision(UUID id, UUID agentId, ActionKind action, String target, UUID evidenceId, long tick) {
    public Decision { Objects.requireNonNull(id); Objects.requireNonNull(agentId); Objects.requireNonNull(action); if (tick<0) throw new IllegalArgumentException("Invalid decision"); }
  }
  public record Outcome(UUID decisionId, boolean accepted, boolean worldEffectVerified, long completedTick, int itemDelta) {
    public Outcome { Objects.requireNonNull(decisionId); if (completedTick<0 || (worldEffectVerified && !accepted)) throw new IllegalArgumentException("Invalid outcome"); }
  }
  public interface AgentPolicy { Decision decide(Observation observation); }
  public static void validate(Observation o, Decision d) {
    if (!o.agentId().equals(d.agentId()) || o.tick()!=d.tick() || !o.allowedActions().contains(d.action())) throw new IllegalArgumentException("Invalid action");
    if (d.evidenceId()!=null && o.evidence().stream().noneMatch(e->e.id().equals(d.evidenceId()))) throw new IllegalArgumentException("Unknown evidence");
  }
  public static final class ScriptedPolicy implements AgentPolicy {
    public Decision decide(Observation o) {
      for (Evidence e:o.evidence()) if (e.kind()==EvidenceKind.DIRECT && e.sourceAgent().equals(o.agentId()) && e.quantity()>0 && o.allowedActions().contains(ActionKind.GATHER)) return make(o,ActionKind.GATHER,e);
      for (Evidence e:o.evidence()) if (e.kind()==EvidenceKind.REPORTED && !e.sourceAgent().equals(o.agentId()) && e.quantity()>0 && o.allowedActions().contains(ActionKind.OBSERVE)) return make(o,ActionKind.OBSERVE,e);
      if (!o.allowedActions().contains(ActionKind.WAIT)) throw new IllegalStateException("No safe fallback");
      return make(o,ActionKind.WAIT,null);
    }
    private Decision make(Observation o,ActionKind a,Evidence e) { return new Decision(UUID.randomUUID(),o.agentId(),a,e==null?null:e.target(),e==null?null:e.id(),o.tick()); }
  }
}
