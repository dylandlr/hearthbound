package dev.hearthbound.agent.minecraft;

import dev.hearthbound.agent.v02.DecisionGateV02;
import dev.hearthbound.agent.v02.HierarchicalTask;
import dev.hearthbound.agent.v02.MillObservation;
import dev.hearthbound.agent.v02.PolicyDecisionV02;
import dev.hearthbound.jobs.BarrelHaulController;
import dev.hearthbound.jobs.WorkshopRegistry;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Server-thread execution boundary for v0.2 decisions. Every call re-observes and
 * validates freshness, mask, workshop authority, and active-haul state before mutation.
 */
public final class MinecraftMillActionExecutor {
    public static final String VERSION = "hearthbound.agent.minecraft-executor.v0.2";
    private static final String ORDER = "HearthboundMillOrder";
    private static final String HAUL = "HearthboundHaul";

    public enum Outcome {
        ACCEPTED_WAIT,
        ACCEPTED_SUPPLY,
        ACCEPTED_COLLECTION,
        ACCEPTED_ACTIVE_DELIVERY,
        REJECTED_STALE,
        REJECTED_MASKED,
        REJECTED_DISABLED,
        REJECTED_ACCESS,
        REJECTED_BUSY,
        REJECTED_RESERVATION
    }

    public record Result(Outcome outcome, MillObservation observation) {
        public boolean accepted() {
            return outcome == Outcome.ACCEPTED_WAIT || outcome == Outcome.ACCEPTED_SUPPLY
                    || outcome == Outcome.ACCEPTED_COLLECTION
                    || outcome == Outcome.ACCEPTED_ACTIVE_DELIVERY;
        }
    }

    private MinecraftMillActionExecutor() {}

    public static Result execute(Villager worker, PolicyDecisionV02 decision) {
        if (!(worker.level() instanceof ServerLevel level))
            throw new IllegalArgumentException("Server worker required");

        MillObservation current = MinecraftMillObservationAdapter.observe(worker);
        DecisionGateV02.Rejection rejection = DecisionGateV02.validate(current, decision);
        if (rejection == DecisionGateV02.Rejection.STALE_OBSERVATION)
            return new Result(Outcome.REJECTED_STALE, current);
        if (rejection == DecisionGateV02.Rejection.ACTION_MASKED)
            return new Result(Outcome.REJECTED_MASKED, current);

        CompoundTag data = worker.getPersistentData();
        CompoundTag order = data.getCompound(ORDER);
        if (!order.getBoolean("Enabled"))
            return new Result(Outcome.REJECTED_DISABLED, current);

        BlockPos mill = BlockPos.of(order.getLong("Mill"));
        java.util.UUID manager = order.hasUUID("WorkshopManager")
                ? order.getUUID("WorkshopManager")
                : order.hasUUID("WorkshopOwner") ? order.getUUID("WorkshopOwner") : null;
        if (!WorkshopRegistry.get(level).canUse(mill, manager, false))
            return new Result(Outcome.REJECTED_ACCESS, current);

        HierarchicalTask action = decision.action();
        if (action == HierarchicalTask.WAIT)
            return new Result(Outcome.ACCEPTED_WAIT, current);

        if (action == HierarchicalTask.RETURN_TO_WAIT) {
            if (!data.contains(HAUL, 10)) return new Result(Outcome.REJECTED_MASKED, current);
            CompoundTag haul = data.getCompound(HAUL);
            if (!"create:wheat_flour".equals(haul.getString("Item"))
                    || haul.getInt("Cargo") <= 0 || !"DELIVER".equals(haul.getString("Phase")))
                return new Result(Outcome.REJECTED_MASKED, current);
            return new Result(Outcome.ACCEPTED_ACTIVE_DELIVERY, current);
        }

        if (data.contains(HAUL, 10) || data.getBoolean("HearthboundTravelActive"))
            return new Result(Outcome.REJECTED_BUSY, current);

        boolean assigned;
        if (action == HierarchicalTask.SUPPLY_MILL) {
            int count = Math.min(4, current.sourceWheat());
            assigned = count > 0 && BarrelHaulController.assignCitizen(worker,
                    BlockPos.of(order.getLong("Wheat")), mill, count);
            if (assigned) order.putString("State", "SUPPLYING_WHEAT");
            return new Result(assigned ? Outcome.ACCEPTED_SUPPLY : Outcome.REJECTED_RESERVATION,
                    MinecraftMillObservationAdapter.observe(worker));
        }

        assigned = BarrelHaulController.assignFlourCitizen(worker, mill,
                BlockPos.of(order.getLong("Flour")), 1);
        if (assigned) order.putString("State", "COLLECTING_FLOUR");
        return new Result(assigned ? Outcome.ACCEPTED_COLLECTION : Outcome.REJECTED_RESERVATION,
                MinecraftMillObservationAdapter.observe(worker));
    }
}
