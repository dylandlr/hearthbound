package dev.hearthbound.research;

import java.util.Objects;

/**
 * Bounded server-side execution loop for one milling assignment.
 * The Minecraft adapter observes machinery and performs authorized effects.
 * This controller never forges a Create completion or research receipt.
 */
public final class ScriptedCitizenWorkLoop {
    public enum Action { NONE, SUPPLY_WHEAT, ACTIVATE_POWER, OBSERVE, REPORT_COMPLETION, ABORT }
    public record Snapshot(boolean assigned, boolean wheatInInventory, boolean wheatInMill,
                           boolean machinePresent, boolean powerAvailable, boolean dangerous,
                           boolean alreadyCredited, boolean millingOutputObserved) {}
    public record Step(ScriptedMillingExecutor.State state, Action action) {}
    public static Step tick(ScriptedMillingExecutor.State state, Snapshot world) {
        Objects.requireNonNull(state);
        Objects.requireNonNull(world);
        if (state.phase() == ScriptedMillingExecutor.Phase.COMPLETED ||
            state.phase() == ScriptedMillingExecutor.Phase.ABORTED)
            return new Step(state, Action.NONE);
        if (!world.assigned() || world.dangerous() || world.alreadyCredited())
            return new Step(new ScriptedMillingExecutor.State(state.operationId(), state.citizenId(),
                    ScriptedMillingExecutor.Phase.ABORTED), Action.ABORT);
        if (state.phase() == ScriptedMillingExecutor.Phase.PROCESSING)
            return new Step(state, world.millingOutputObserved() ? Action.REPORT_COMPLETION : Action.OBSERVE);
        if (!world.machinePresent() || !world.powerAvailable())
            return new Step(new ScriptedMillingExecutor.State(state.operationId(), state.citizenId(),
                    ScriptedMillingExecutor.Phase.WAITING), Action.NONE);
        if (!world.wheatInMill()) {
            if (!world.wheatInInventory())
                return new Step(new ScriptedMillingExecutor.State(state.operationId(), state.citizenId(),
                        ScriptedMillingExecutor.Phase.WAITING), Action.NONE);
            return new Step(state, Action.SUPPLY_WHEAT);
        }
        var decision = ScriptedMillingExecutor.plan(state,
                new ScriptedMillingPolicy.Observation(true,true,true,true,false,false));
        return new Step(decision.state(), decision.authorizeMotorActivation()
                ? Action.ACTIVATE_POWER : Action.NONE);
    }
    private ScriptedCitizenWorkLoop() {}
}
