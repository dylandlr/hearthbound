package dev.hearthbound.integration;

import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraft.core.BlockPos;
import java.util.UUID;

/** First server-authoritative Hearthbound movement loop over loaded vanilla villagers. */
@Mod.EventBusSubscriber(modid="hearthbound",bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class CitizenMovementObserver {
    private CitizenMovementObserver() {}
    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event) {
        if(event.phase!=TickEvent.Phase.END) return;
        var server=event.getServer();
        long tick=ForgeServerTickObserver.logicalTick(server);
        if(tick%10!=0) return;
        var registry=CitizenRegistrySavedData.get(server);
        for(var citizen:registry.snapshot()) {
            boolean supply = citizen.task().startsWith("MILL_SUPPLY:");
            if(!supply && !citizen.task().startsWith("MOVE:")) continue;
            var level=server.getLevel(net.minecraft.resources.ResourceKey.create(
                    net.minecraft.core.registries.Registries.DIMENSION,
                    new net.minecraft.resources.ResourceLocation(citizen.dimension())));
            if(level==null)continue;
            var villager=CitizenEmbodiment.find(level,citizen.id());
            if(villager==null || !villager.isAlive())continue;
            long encoded;
            try {encoded=Long.parseLong(citizen.task().substring(supply ? 12 : 5));}
            catch(NumberFormatException badTask){continue;}
            BlockPos target=BlockPos.of(encoded);
            boolean arrived=villager.blockPosition().distSqr(target)<=4;
            if(!arrived) {
                boolean accepted = villager.getNavigation().moveTo(
                        target.getX()+0.5,target.getY(),target.getZ()+0.5,0.7);
                if(tick%40==0) org.apache.logging.log4j.LogManager.getLogger().info(
                        "HEARTHBOUND_CITIZEN_NAVIGATION_PROGRESS citizen={} actual={} target={} pathAccepted={} navigationDone={} tick={}",
                        citizen.id(),villager.blockPosition(),target,accepted,
                        villager.getNavigation().isDone(),tick);
            }
            if(supply && arrived) {
                var millPos=target.offset(1,0,0);
                var entity=level.getBlockEntity(millPos);
                if(entity instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity mill) {
                    var data=villager.getPersistentData();
                    int wheat=data.getInt("HearthboundWheat");
                    if(wheat>0) {
                        // Fail closed if a previous interruption or external actor
                        // left the mill occupied. Never debit citizen wheat when
                        // we cannot attribute the machine input to this task.
                        if(!mill.inputInv.getStackInSlot(0).isEmpty()) {
                            if(tick%100==0) org.apache.logging.log4j.LogManager.getLogger().warn(
                                    "HEARTHBOUND_CITIZEN_SUPPLY_BLOCKED citizen={} mill={} reason=occupied_input task=retained",
                                    citizen.id(),millPos);
                            continue;
                        }
                        var held=new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.WHEAT,wheat);
                        if(CitizenSupplyAssignment.isAuthorized(server,citizen.id(),citizen.dimension(),millPos)
                                && ServerMillingActions.supplyWheat(mill,held)) {
                            data.putInt("HearthboundWheat",held.getCount());
                            data.putLong("HearthboundLastSupplyMill",millPos.asLong());
                            data.putLong("HearthboundLastSupplyTick",tick);
                            registry.completeSupply(citizen.id(),villager.blockPosition().asLong(),tick);
                            org.apache.logging.log4j.LogManager.getLogger().info(
                                    "HEARTHBOUND_CITIZEN_AUTOMATED_SUPPLY citizen={} mill={} remainingWheat={} tick={}",
                                    citizen.id(),millPos,held.getCount(),tick);
                        }
                    }
                }
            } else if(!supply) registry.observe(citizen.id(),villager.blockPosition().asLong(),tick,arrived);
            if(arrived && !supply) org.apache.logging.log4j.LogManager.getLogger().info(
                    "HEARTHBOUND_CITIZEN_ARRIVED citizen={} pos={} tick={}",
                    citizen.id(),villager.blockPosition(),tick);
        }
    }
}
