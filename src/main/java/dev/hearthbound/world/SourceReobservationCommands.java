package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
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
                        String request=SourceFailureBeliefs.requestReobservation(level,citizen,source);
                        if (!request.contains("status=REQUESTED")) {
                            ctx.getSource().sendFailure(Component.literal(
                                "No real extraction miss available to request re-observation; "+request));
                            return 0;
                        }
                        ctx.getSource().sendSuccess(()->Component.literal(request),false);
                        return 1;
                    }))));
    }
}
