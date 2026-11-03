package dev.hearthbound.world;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.evidence.MillMlpInference;
import dev.hearthbound.evidence.MillPolicyShadow;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.common.capabilities.ForgeCapabilities;

/**
 * Operator-invoked ONE-SHOT decision-to-task bridge, not autonomous AI.
 * Only REQUEST_WHEAT_HAUL can delegate to the existing reservation-aware
 * SableHauling.assign. All inventory manipulation remains in that controller.
 */
public final class MillPolicyTrial {
    private MillPolicyTrial() {}

    public static String assignOne(ServerLevel level, BlockPos source, BlockPos millPos,
                                   MillPolicyShadow.Mode mode) {
        if (level == null || source == null || millPos == null || mode == null)
            throw new IllegalArgumentException("Missing trial argument");
        if (source.equals(millPos) || !level.hasChunkAt(source) || !level.hasChunkAt(millPos))
            throw new IllegalStateException("Endpoints must be distinct loaded positions");
        if (!MillReservations.isMill(level, millPos)
                || !(level.getBlockEntity(millPos) instanceof MillstoneBlockEntity mill))
            throw new IllegalStateException("Destination is not an available Create millstone");
        if (mill.getSpeed() == 0)
            throw new IllegalStateException("Create millstone has no kinetic power");
        for (int i = 0; i < mill.inputInv.getSlots(); i++)
            if (!mill.inputInv.getStackInSlot(i).isEmpty())
                throw new IllegalStateException("Millstone input not empty");
        for (int i = 0; i < mill.outputInv.getSlots(); i++)
            if (!mill.outputInv.getStackInSlot(i).isEmpty())
                throw new IllegalStateException("Millstone output not empty");
        BlockEntity sourceEntity = level.getBlockEntity(source);
        if (sourceEntity == null || !hasWheat(sourceEntity))
            throw new IllegalStateException("Source inventory has no real wheat");

        List<Villager> citizens = level.getEntitiesOfClass(
            Villager.class, new AABB(millPos).inflate(16),
            villager -> "Sable".equals(villager.getName().getString())
                && villager.getPersistentData().getBoolean("hearthbound.sable"));
        if (citizens.size() != 1)
            throw new IllegalStateException("Exactly one marked Sable required near mill");
        Villager citizen = citizens.get(0);
        if (SableHauling.active(citizen))
            throw new IllegalStateException("Citizen already has a pending task");

        var observation = new MillPolicyShadow.Observation(
            true, false, false, false, CitizenMillMemory.observedProcesses(citizen));
        var decision = MillPolicyShadow.decide(mode, observation, MillMlpInference.loadBundled());
        if (decision.selected() != MillPolicyShadow.Action.REQUEST_WHEAT_HAUL
                || decision.masked())
            throw new IllegalStateException("Policy did not authorize hauling");
        // This existing method acquires the source claim and exclusive mill
        // reservation before persisting the citizen's task.
        SableHauling.assign(level, citizen, source, millPos);
        String outcome = "POLICY_TRIAL_ASSIGNED mode=" + mode
            + " action=REQUEST_WHEAT_HAUL citizen=" + citizen.getUUID()
            + " source=" + source + " mill=" + millPos
            + " model=mill-mlp-v1 existing_executor=SableHauling";
        org.apache.logging.log4j.LogManager.getLogger("HearthboundPolicyTrial")
            .info("HEARTHBOUND_POLICY_TRIAL {}", outcome);
        return outcome;
    }

    private static boolean hasWheat(BlockEntity entity) {
        var capability = entity.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (capability.isPresent()) {
            var inventory = capability.orElseThrow(IllegalStateException::new);
            for (int i = 0; i < inventory.getSlots(); i++)
                if (inventory.getStackInSlot(i).is(Items.WHEAT)
                        && inventory.getStackInSlot(i).getCount() > 0)
                    return true;
        }
        if (entity instanceof Container inventory) {
            for (int i = 0; i < inventory.getContainerSize(); i++)
                if (inventory.getItem(i).is(Items.WHEAT)
                        && inventory.getItem(i).getCount() > 0)
                    return true;
        }
        return false;
    }
}
