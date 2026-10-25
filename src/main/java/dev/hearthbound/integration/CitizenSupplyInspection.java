package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.core.BlockPos;
import java.io.IOException;
import java.util.UUID;

/** Read-only recovery assessment against live persisted-order and entity evidence. */
public final class CitizenSupplyInspection {
    private CitizenSupplyInspection() {}
    public static CitizenSupplyRecovery.Decision inspect(
            MinecraftServer server, UUID citizenId, String dimension,
            BlockPos millPosition, Villager villager, MillstoneBlockEntity mill) {
        if(server==null || citizenId==null || villager==null || mill==null)
            return CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED;
        try {
            UUID operation=CitizenSupplyAssignment.require(server,citizenId,dimension,millPosition);
            boolean attempt=CitizenSupplyAttempt.hasAttempt(server,operation);
            var data=villager.getPersistentData();
            boolean matching=data.hasUUID("HearthboundLastSupplyOperation")
                    && operation.equals(data.getUUID("HearthboundLastSupplyOperation"))
                    && data.getLong("HearthboundLastSupplyMill")==millPosition.asLong();
            boolean idle=CitizenRegistrySavedData.get(server).snapshot().stream()
                    .anyMatch(c -> c.id().equals(citizenId) && c.task().equals("IDLE"));
            return CitizenSupplyRecovery.classify(new CitizenSupplyRecovery.Evidence(
                    attempt,mill.inputInv.getStackInSlot(0).is(net.minecraft.world.item.Items.WHEAT),
                    data.getInt("HearthboundWheat"),data.getInt("HearthboundLastSupplyBefore"),
                    matching,idle));
        } catch(IOException | IllegalArgumentException error) {
            return CitizenSupplyRecovery.Decision.AMBIGUOUS_BLOCKED;
        }
    }
}
