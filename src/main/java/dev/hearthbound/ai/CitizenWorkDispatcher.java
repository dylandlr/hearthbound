package dev.hearthbound.ai;

import dev.hearthbound.research.CitizenTaskArbiter;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;
import static dev.hearthbound.ai.ColonyPolicy.*;

/**
 * Single decision-boundary dispatcher. No Minecraft world mutations occur here.
 * A server adapter must build a fresh observation and implement the chosen executor.
 * Only tasks supported by that adapter may appear as executable actions.
 */
public final class CitizenWorkDispatcher {
    public interface Executor {
        /** Return true only if the server accepted the work assignment. */
        boolean start(Action action, CitizenTaskArbiter.Lease lease);
    }
    public record Trace(String citizen, long observationVersion, String actionId,
                        String outcome, String reason) {}
    public record Result(boolean accepted, CitizenTaskArbiter.Lease lease, Trace trace) {}

    private final CitizenTaskArbiter arbiter;
    private final List<Trace> traces = new ArrayList<>();
    public CitizenWorkDispatcher(CitizenTaskArbiter arbiter) {
        this.arbiter = Objects.requireNonNull(arbiter);
    }

    public Result dispatch(UUID citizen, Observation current, ColonyPolicy policy, Executor executor) {
        Objects.requireNonNull(citizen);
        Objects.requireNonNull(current);
        Objects.requireNonNull(policy);
        Objects.requireNonNull(executor);
        if (!citizen.toString().equals(current.citizenId()))
            throw new IllegalArgumentException("Observation belongs to different citizen");
        if (arbiter.active(citizen) != null)
            return rejected(current, "", "BUSY", "Active task lease");
        Decision decision = policy.choose(current);
        if (!ActionGate.allowed(current, decision))
            return rejected(current, decision.actionId(), "REJECTED", "ActionGate denied proposal");
        Action action = current.availableActions().stream()
                .filter(a -> a.id().equals(decision.actionId())).findFirst().orElseThrow();
        CitizenTaskArbiter.Kind kind = switch(action.kind()) {
            case STUDY -> CitizenTaskArbiter.Kind.STUDY;
            case HAUL, DELIVER -> CitizenTaskArbiter.Kind.HAUL;
            case OPERATE -> CitizenTaskArbiter.Kind.EXPERIMENT;
            case REST -> CitizenTaskArbiter.Kind.REST;
            default -> null;
        };
        if (kind == null)
            return rejected(current, action.id(), "UNSUPPORTED", "No task ownership adapter");
        CitizenTaskArbiter.Lease lease = arbiter.acquire(citizen, kind, current.version());
        boolean accepted = false;
        try {
            accepted = executor.start(action, lease);
        } finally {
            if (!accepted) arbiter.release(citizen, lease.assignmentId());
        }
        if (!accepted) return rejected(current, action.id(), "DECLINED", "Executor rejected task");
        Trace trace = new Trace(current.citizenId(), current.version(), action.id(),
                "ASSIGNED", decision.rationale());
        traces.add(trace);
        return new Result(true, lease, trace);
    }

    public boolean complete(UUID citizen, UUID assignmentId) {
        return arbiter.release(citizen, assignmentId);
    }

    public List<Trace> traces() { return List.copyOf(traces); }

    private Result rejected(Observation o, String action, String outcome, String reason) {
        Trace trace = new Trace(o.citizenId(), o.version(), action, outcome, reason);
        traces.add(trace);
        return new Result(false, null, trace);
    }
}
