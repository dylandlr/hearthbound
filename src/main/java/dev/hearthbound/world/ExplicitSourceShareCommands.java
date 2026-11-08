package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Operator fixture for explicit scout-to-executor communication, rather than
 * v0.11's convenience "nearest Sable" sender lookup. All real direct-source,
 * role and communication-range validation remains in CitizenKnowledgeExchange.
 *
 * An explicit report can inform a policy but NEVER instructs a haul by itself.
 */
@Mod.EventBusSubscriber(modid="hearthbound",bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class ExplicitSourceShareCommands {
    private ExplicitSourceShareCommands() {}

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher=event.getDispatcher();
        dispatcher.register(Commands.literal("hearthbound-share-direct")
            .requires(s->s.hasPermission(2))
            .then(Commands.argument("source",BlockPosArgument.blockPos())
                .then(Commands.argument("sender",EntityArgument.entity())
                    .then(Commands.argument("recipient",EntityArgument.entity())
                        .executes(ctx->{
                            var from=EntityArgument.getEntity(ctx,"sender");
                            var to=EntityArgument.getEntity(ctx,"recipient");
                            if(!(from instanceof Villager scout)
                                    || !(to instanceof Villager recipient)) {
                                ctx.getSource().sendFailure(Component.literal("Source scout and recipient must be real villagers"));
                                return 0;
                            }
                            ServerLevel level=ctx.getSource().getLevel();
                            var source=BlockPosArgument.getBlockPos(ctx,"source");
                            String result=CitizenKnowledgeExchange.share(
                                level,source,scout,recipient);
                            ctx.getSource().sendSuccess(()->Component.literal(result),false);
                            return result.contains("status=DELIVERED")?1:0;
                        })))));
    }
}
