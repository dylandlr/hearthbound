package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Operator-triggered, citizen-owned request for direct re-observation after
 * an actual failed extraction. This does NOT sense a chest or move a scout;
 * an independent citizen must still inspect and share a fresh observation.
 */
@Mod.EventBusSubscriber(modid="hearthbound",bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class SourceReobservationCommands {
    private static final String REQUEST="hearthbound.pendingSourceRecheck.v1";
    private SourceReobservationCommands() {}

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher=event.getDispatcher();
        dispatcher.register(Commands.literal("hearthbound-pickup-belief")
            .requires(s->s.hasPermission(2))
            .then(Commands.argument("executor",EntityArgument.entity())
                .then(Commands.argument("source",BlockPosArgument.blockPos())
                    .executes(ctx->{
                        var e=EntityArgument.getEntity(ctx,"executor");
                        if(!(e instanceof Villager citizen)) {
                            ctx.getSource().sendFailure(Component.literal("Executor must be a real citizen"));
                            return 0;
                        }
                        BlockPos source=BlockPosArgument.getBlockPos(ctx,"source");
                        String evidence=SourceFailureBeliefs.inspect(
                            ctx.getSource().getLevel(),citizen,source);
                        ctx.getSource().sendSuccess(()->Component.literal(evidence),false);
                        return 1;
                    }))));
        dispatcher.register(Commands.literal("hearthbound-reobserve-request")
            .requires(s->s.hasPermission(2))
            .then(Commands.argument("executor",EntityArgument.entity())
                .then(Commands.argument("source",BlockPosArgument.blockPos())
                    .executes(ctx->{
                        var e=EntityArgument.getEntity(ctx,"executor");
                        if(!(e instanceof Villager citizen)) {
                            ctx.getSource().sendFailure(Component.literal("Executor must be a real citizen"));
                            return 0;
                        }
                        ServerLevel level=ctx.getSource().getLevel();
                        BlockPos source=BlockPosArgument.getBlockPos(ctx,"source");
                        String evidence=SourceFailureBeliefs.inspect(level,citizen,source);
                        if (!evidence.contains("state=PICKUP_RETURNED_EMPTY")) {
                            ctx.getSource().sendFailure(Component.literal(
                                "No real extraction miss available to request re-observation"));
                            return 0;
                        }
                        CompoundTag pending=new CompoundTag();
                        pending.putString("schema","hearthbound.reobservation-request.v1");
                        pending.putUUID("world",HearthboundWorldIdentity.get(level));
                        pending.putUUID("recipient",citizen.getUUID());
                        pending.putLong("source",source.asLong());
                        pending.putLong("requestTick",level.getGameTime());
                        // Do not fake that any scout has accepted or fulfilled
                        // a request; explicit direct observation is still needed.
                        pending.putString("state","AWAITING_SCOUT_DIRECT_OBSERVATION");
                        citizen.getPersistentData().put(REQUEST,pending);
                        String request="SOURCE_REOBSERVATION_REQUEST status=REQUESTED"
                            +" recipient="+citizen.getUUID()
                            +" source="+ReportChoiceCommands.key(level,source)
                            +" request_tick="+level.getGameTime()
                            +" origin=FAILED_PHYSICAL_EXTRACTION"
                            +" scout_assigned=false scout_observed=false"
                            +" task_authorized=false reward_authorized=false NO_RESEARCH_CREDIT";
                        ctx.getSource().sendSuccess(()->Component.literal(request),false);
                        return 1;
                    }))));
    }
}
