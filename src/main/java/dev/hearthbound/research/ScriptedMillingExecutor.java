package dev.hearthbound.research;

import java.util.Objects;
import java.util.UUID;

/** Server-side task coordinator. Does not perform Minecraft world mutations. */
public final class ScriptedMillingExecutor {
    public enum Phase { UNASSIGNED, WAITING, READY_TO_POWER, PROCESSING, COMPLETED, ABORTED }
    public record State(UUID operationId, UUID citizenId, Phase phase) {
        public State {
            Objects.requireNonNull(operationId);
            Objects.requireNonNull(citizenId);
            Objects.requireNonNull(phase);
        }
    }
    public record Result(State state, boolean authorizeMotorActivation) {}

    public static Result plan(State prior, ScriptedMillingPolicy.Observation observation) {
        Objects.requireNonNull(prior);
        if (prior.phase() == Phase.COMPLETED || prior.phase() == Phase.ABORTED)
            return new Result(prior, false);
        ScriptedMillingPolicy.Decision decision = ScriptedMillingPolicy.choose(observation);
        return switch (decision) {
            case ABORT -> new Result(new State(prior.operationId(), prior.citizenId(), Phase.ABORTED), false);
            case WAIT -> new Result(new State(prior.operationId(), prior.citizenId(), Phase.WAITING), false);
            case PREPARE_MILLING -> {
                if (prior.phase() == Phase.PROCESSING)
                    yield new Result(prior, false);
                yield new Result(new State(prior.operationId(), prior.citizenId(), Phase.READY_TO_POWER), true);
            }
        };
    }

    /** Only an accepted receipt for this exact citizen operation completes the task. */
    public static State complete(State prior, CitizenDiscoveryGate.Eligible eligible) {
        Objects.requireNonNull(prior);
        Objects.requireNonNull(eligible);
        if (prior.phase() != Phase.PROCESSING
                || !prior.operationId().equals(eligible.operationId())
                || !prior.citizenId().equals(eligible.citizenId()))
            throw new IllegalArgumentException("Milling completion does not match active citizen operation");
        return new State(prior.operationId(), prior.citizenId(), Phase.COMPLETED);
    }
    public static State powered(State prior) {
        if (prior.phase() != Phase.READY_TO_POWER)
            throw new IllegalArgumentException("No authorization to activate milling motor");
        return new State(prior.operationId(), prior.citizenId(), Phase.PROCESSING);
    }
    private ScriptedMillingExecutor() {}
}
