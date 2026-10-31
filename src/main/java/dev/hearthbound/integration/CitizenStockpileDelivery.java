package dev.hearthbound.integration;

import dev.hearthbound.research.DurableOperationIntents;
import java.io.IOException;
import java.nio.file.Files;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.LevelResource;

/** First fail-closed physical chest handoff from a citizen's collected items. */
public final class CitizenStockpileDelivery {
    private CitizenStockpileDelivery() {}
    public static boolean deliver(MinecraftServer server, UUID citizen, String dimension,
                                  BlockPos destination, Villager villager, Container container) {
        if(server==null || citizen==null || villager==null || container==null
                || !citizen.equals(CitizenEmbodiment.identity(villager))) return false;
        var data=villager.getPersistentData();
        if(!data.contains("HearthboundMillCollected")
                || !data.hasUUID("HearthboundLastCollectionOperation")
                || data.hasUUID("HearthboundLastStockpileOperation")) return false;
        ItemStack carried=ItemStack.of(data.getCompound("HearthboundMillCollected"));
        if(carried.isEmpty()) return false;
        int slot=-1;
        for(int i=0;i<container.getContainerSize();i++) {
            if(container.getItem(i).isEmpty() && container.canPlaceItem(i,carried)) {slot=i;break;}
        }
        if(slot<0) return false;
        try {
            var folder=server.getWorldPath(LevelResource.ROOT)
                    .resolve("hearthbound-citizen-stockpile-attempts");
            Files.createDirectories(folder);
            var intents=new DurableOperationIntents(folder);
            String key="stockpile/"+citizen+"/"+data.getUUID("HearthboundLastCollectionOperation");
            String evidence=citizen+"|"+dimension+"|"+destination.asLong()+"|"
                    +data.getUUID("HearthboundLastCollectionOperation")+"|"+carried.getItem()+"|"+carried.getCount();
            var attempt=intents.prepare(key,evidence);
            if(!attempt.newlyCreated()) return false;
            container.setItem(slot,carried.copy());
            container.setChanged();
            data.putUUID("HearthboundLastStockpileOperation",attempt.intent().operationId());
            data.remove("HearthboundMillCollected");
            return true;
        } catch(IOException failure) {
            return false; // In doubt, retain the work order instead of replaying.
        }
    }
}
