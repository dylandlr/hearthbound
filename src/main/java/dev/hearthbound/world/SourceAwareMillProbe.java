package dev.hearthbound.world;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.evidence.SourceAwareMillPlanner;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.AABB;

/**
 * Purely observational reference planner over real Forge/Create server state.
 * The 5-feature neural model is unchanged; no action is executed here.
 */
public final class SourceAwareMillProbe {
    private static final ResourceLocation FLOUR = new ResourceLocation("create","wheat_flour");
    private SourceAwareMillProbe() {}

    public static String inspect(ServerLevel level, BlockPos source, BlockPos millPos) {
        if (!level.hasChunkAt(millPos)
                || !(level.getBlockEntity(millPos) instanceof MillstoneBlockEntity mill))
            return "SOURCE_PLAN ABSTAIN reason=UNKNOWN_MILL EXECUTION_DISABLED";
        List<Villager> citizens=level.getEntitiesOfClass(Villager.class,
            new AABB(millPos).inflate(16),
            v -> "Sable".equals(v.getName().getString())
                && v.getPersistentData().getBoolean("hearthbound.sable"));
        if (citizens.size()!=1)
            return "SOURCE_PLAN ABSTAIN reason=REQUIRES_ONE_MARKED_SABLE EXECUTION_DISABLED";
        Villager citizen=citizens.get(0);
        var sourceObservation=SourceWheatObservation.inspect(level,source,citizen);
        SourceAwareMillPlanner.Availability state =
            SourceAwareMillPlanner.Availability.valueOf(sourceObservation.state().name());
        boolean wheat=false,flour=false,blocked=false;
        for (int i=0;i<mill.inputInv.getSlots();i++) {
            var stack=mill.inputInv.getStackInSlot(i);
            if (stack.is(Items.WHEAT) && !stack.isEmpty()) wheat=true;
            else if (!stack.isEmpty()) blocked=true;
        }
        for (int i=0;i<mill.outputInv.getSlots();i++) {
            var stack=mill.outputInv.getStackInSlot(i);
            if (stack.isEmpty()) continue;
            if (FLOUR.equals(BuiltInRegistries.ITEM.getKey(stack.getItem()))) flour=true;
            else blocked=true;
        }
        var observation=new SourceAwareMillPlanner.Observation(
            mill.getSpeed()!=0,wheat,flour,blocked,state,SableHauling.active(citizen));
        var intent=SourceAwareMillPlanner.decide(observation);
        var v2=new dev.hearthbound.evidence.MillObservationV2.Snapshot(
            observation.powered(), wheat, flour, blocked,
            CitizenMillMemory.observedProcesses(citizen),
            dev.hearthbound.evidence.MillObservationV2.SourceState.valueOf(state.name()),
            observation.taskActive(),sourceObservation.tick(),level.getGameTime());
        double[] features=dev.hearthbound.evidence.MillObservationV2.encode(v2);
        var tensorText=new java.util.StringJoiner(",");
        for (double value:features) tensorText.add(Double.toString(value));
        return "SOURCE_PLAN source=" + state + " wheat_source=" + sourceObservation.wheat()
            + " source_reason=" + sourceObservation.reason()
            + " mill_powered=" + observation.powered()
            + " mill_wheat=" + wheat + " mill_flour=" + flour
            + " mill_blocked=" + blocked + " task_active=" + observation.taskActive()
            + " action=" + intent + " dispatch_candidate="
            + SourceAwareMillPlanner.dispatchCandidate(intent)
            + " tick=" + level.getGameTime()
            + " planner=scripted_source_aware_v1"
            + " observation_schema=" + dev.hearthbound.evidence.MillObservationV2.SCHEMA
            + " tensor_v2=" + tensorText
            + " ML_MODEL_UNCHANGED EXECUTION_DISABLED";
    }
}
