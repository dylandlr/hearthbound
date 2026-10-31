package dev.hearthbound.integration;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.research.DurableOperationIntents;
import java.io.IOException;
import java.nio.file.Files;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.LevelResource;

/** Fail-closed first collection attempt: each mill/citizen pair needs reconciliation before reuse. */
public final class CitizenMillCollection {
    private CitizenMillCollection() {}
    private static final String RECEIPT="HearthboundMillCollected";
    public static boolean collect(MinecraftServer server, UUID citizen, String dimension,
                                  BlockPos millPos, net.minecraft.world.entity.npc.Villager villager,
                                  MillstoneBlockEntity mill) {
        if(server==null || citizen==null || villager==null || mill==null
                || !citizen.equals(CitizenEmbodiment.identity(villager))) return false;
        var data=villager.getPersistentData();
        // One outstanding collection at a time; preserve evidence until a
        // separate durable storage handoff can reconcile and retire it.
        if(data.contains(RECEIPT)) return false;
        ItemStack available=mill.outputInv.getStackInSlot(0);
        if(available.isEmpty()) return false;
        var directory=server.getWorldPath(LevelResource.ROOT)
                .resolve("hearthbound-citizen-mill-collection-attempts");
        String key="collect/"+citizen+"/"+dimension+"/"+millPos.asLong();
        try {
            Files.createDirectories(directory);
            var intents=new DurableOperationIntents(directory);
            String evidence=citizen+"|"+dimension+"|"+millPos.asLong()+"|"
                    +available.getItem().toString()+"|"+available.getCount();
            var prepared=intents.prepare(key,evidence);
            if(!prepared.newlyCreated()) return false;
            ItemStack moved=ServerMillingActions.collectOutput(mill,0,available.getCount());
            if(moved.isEmpty()) return false;
            var receipt=new net.minecraft.nbt.CompoundTag();
            moved.save(receipt);
            data.put(RECEIPT,receipt);
            data.putUUID("HearthboundLastCollectionOperation",prepared.intent().operationId());
            return true;
        } catch(IOException failure) {
            return false; // Unknown journal state never permits blind retry.
        }
    }
}
