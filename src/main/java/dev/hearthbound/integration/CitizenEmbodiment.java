package dev.hearthbound.integration;

import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.core.BlockPos;

/**
 * First visible citizen embodiment: a vanilla villager with durable Hearthbound ID
 * stored in entity persistent NBT. Does not yet grant autonomous Hearthbound actions.
 */
public final class CitizenEmbodiment {
    private static final String CITIZEN_ID = "HearthboundCitizenId";
    private CitizenEmbodiment() {}
    public static Villager spawn(ServerLevel level, UUID citizenId, BlockPos position) {
        var existing = find(level, citizenId);
        if (existing != null) throw new IllegalStateException("Citizen already embodied");
        Villager entity = EntityType.VILLAGER.create(level);
        if (entity == null) throw new IllegalStateException("Unable to create villager");
        entity.moveTo(position.getX() + 0.5, position.getY(), position.getZ() + 0.5,
                0, 0);
        entity.getPersistentData().putUUID(CITIZEN_ID, citizenId);
        entity.setCustomName(net.minecraft.network.chat.Component.literal("Hearthbound Citizen"));
        entity.setCustomNameVisible(true);
        entity.setPersistenceRequired();
        if (!level.addFreshEntity(entity)) throw new IllegalStateException("Citizen entity spawn rejected");
        return entity;
    }
    public static UUID identity(Villager entity) {
        CompoundTag tag=entity.getPersistentData();
        return tag.hasUUID(CITIZEN_ID) ? tag.getUUID(CITIZEN_ID) : null;
    }
    public static Villager find(ServerLevel level, UUID citizenId) {
        for (var entity : level.getAllEntities()) {
            if (entity instanceof Villager villager && citizenId.equals(identity(villager)))
                return villager;
        }
        return null;
    }
}
