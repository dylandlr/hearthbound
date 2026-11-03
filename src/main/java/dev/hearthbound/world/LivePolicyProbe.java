package dev.hearthbound.world;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.item.Items;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;

/**
 * Read-only, server-authoritative decision probe. No policy action is executed.
 * Compares scripted reference and bundled trained MLP; no actions are executed.
 */
public final class LivePolicyProbe {
    private static final ResourceLocation FLOUR = new ResourceLocation("create", "wheat_flour");
    private LivePolicyProbe() {}

    public enum Intent {
        ABSTAIN, REQUEST_WHEAT_HAUL, WAIT_FOR_PROCESSING, COLLECT_OUTPUT, INSPECT_UNPOWERED
    }

    public record Snapshot(boolean citizenObserved, long experience, boolean powered,
                           int wheat, int flour, boolean blocked) {}

    public static Intent scripted(Snapshot obs) {
        if (obs == null || !obs.citizenObserved()) return Intent.ABSTAIN;
        if (!obs.powered()) return Intent.INSPECT_UNPOWERED;
        if (obs.flour() > 0 || obs.blocked()) return Intent.COLLECT_OUTPUT;
        if (obs.wheat() > 0) return Intent.WAIT_FOR_PROCESSING;
        return Intent.REQUEST_WHEAT_HAUL;
    }

    public static String inspect(ServerLevel level, BlockPos millPos) {
        return inspect(level,millPos,dev.hearthbound.evidence.MillPolicyShadow.Mode.SCRIPTED);
    }

    public static String inspect(ServerLevel level, BlockPos millPos,
            dev.hearthbound.evidence.MillPolicyShadow.Mode mode) {
        if (mode == null) throw new IllegalArgumentException("missing shadow policy mode");
        if (!level.hasChunkAt(millPos) || !MillReservations.isMill(level, millPos)
                || !(level.getBlockEntity(millPos) instanceof MillstoneBlockEntity mill))
            return "POLICY_PROBE ABSTAIN reason=NOT_LOADED_CREATE_MILLSTONE pos=" + millPos;

        var citizens = level.getEntitiesOfClass(Villager.class,
            new AABB(millPos).inflate(32),
            citizen -> "Sable".equals(citizen.getName().getString()));
        if (citizens.size() != 1)
            return "POLICY_PROBE ABSTAIN reason=REQUIRES_ONE_NEARBY_SABLE count=" + citizens.size();

        Villager citizen = citizens.get(0);
        int wheat=0, flour=0;
        boolean blocked=false;
        for (int i = 0; i < mill.inputInv.getSlots(); i++) {
            var stack=mill.inputInv.getStackInSlot(i);
            if (stack.is(Items.WHEAT)) wheat += stack.getCount();
            else if (!stack.isEmpty()) blocked=true;
        }
        for (int i = 0; i < mill.outputInv.getSlots(); i++) {
            var stack=mill.outputInv.getStackInSlot(i);
            if (FLOUR.equals(BuiltInRegistries.ITEM.getKey(stack.getItem())))
                flour += stack.getCount();
            else if (!stack.isEmpty()) blocked=true;
        }
        Snapshot snapshot=new Snapshot(true, CitizenMillMemory.observedProcesses(citizen),
            mill.getSpeed()!=0, wheat, flour, blocked);
        Intent action=scripted(snapshot);
        dev.hearthbound.evidence.MillPolicyShadow.Decision shadow;
        try {
            var model = dev.hearthbound.evidence.MillMlpInference.loadBundled();
            var obs = new dev.hearthbound.evidence.MillPolicyShadow.Observation(
                snapshot.powered(),snapshot.wheat()>0,snapshot.flour()>0,
                snapshot.blocked(),snapshot.experience());
            shadow = dev.hearthbound.evidence.MillPolicyShadow.decide(mode,obs,model);
        } catch (RuntimeException invalidModel) {
            return "POLICY_PROBE ABSTAIN reason=MLP_UNAVAILABLE type="
                + invalidModel.getClass().getSimpleName() + " EXECUTION_DISABLED";
        }
        return "POLICY_PROBE policy=scripted_reference action=" + action
            + " citizen=" + citizen.getUUID() + " pos=" + millPos
            + " powered=" + snapshot.powered()
            + " wheat=" + wheat + " flour=" + flour
            + " blocked=" + blocked + " experience=" + snapshot.experience()
            + " mlp_action=" + shadow.rawMlp() + " model=mill-mlp-v1"
            + " shadow_mode=" + shadow.mode()
            + " selected_action=" + shadow.selected()
            + " model_disagreement=" + shadow.disagreement()
            + " action_masked=" + shadow.masked()
            + " EXECUTION_DISABLED ML_INFERENCE_READ_ONLY";
    }
}
