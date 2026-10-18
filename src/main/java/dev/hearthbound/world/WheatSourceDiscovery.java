package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Picks an available offer from the shared read-only colony work board. */
public final class WheatSourceDiscovery {
    private WheatSourceDiscovery() {}

    public static BlockPos nearest(ServerLevel level, Villager citizen, BlockPos destination) {
        for (ColonyJobBoard.HaulOffer offer :
                ColonyJobBoard.observe(level, citizen.blockPosition(), destination)) {
            if (offer.available()) return offer.source();
        }
        return null;
    }
}
