package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import dev.hearthbound.jobs.SableJobController;
import dev.hearthbound.jobs.BarrelHaulController;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Initial in-game embodiment probe.
 * Sable is a persistent vanilla Villager until a dedicated colony controller exists.
 */
@Mod(HearthboundMod.MOD_ID)
public final class HearthboundMod {
    public static final String MOD_ID = "hearthbound";
    private static final Logger LOGGER = LogManager.getLogger();

    public HearthboundMod() {
        LOGGER.info("Hearthbound bootstrap loaded. Create integration pending.");
    }

    @Mod.EventBusSubscriber(modid = MOD_ID)
    public static final class CommandsHandler {
        @SubscribeEvent
        public static void onCommands(RegisterCommandsEvent event) {
            CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
            dispatcher.register(Commands.literal("hearthbound")
                    .then(Commands.literal("status")
                            .executes(ctx -> {
                                ctx.getSource().sendSuccess(
                                        () -> Component.literal("Hearthbound dev: Forge bootstrap. Sable embodiment probe available; Create controller pending."),
                                        false);
                                return 1;
                            }))
                    .then(Commands.literal("spawn_sable")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> {
                                CommandSourceStack source = ctx.getSource();
                                ServerLevel level = source.getLevel();
                                Villager sable = EntityType.VILLAGER.create(level);
                                if (sable == null) {
                                    source.sendFailure(Component.literal("Failed to create Sable."));
                                    return 0;
                                }
                                sable.moveTo(source.getPosition().x, source.getPosition().y,
                                        source.getPosition().z, 0.0F, 0.0F);
                                sable.setCustomName(Component.literal("Sable [prototype]"));
                                sable.setCustomNameVisible(true);
                                sable.setPersistenceRequired();
                                SableJobController.markSable(sable);
                                if (!level.addFreshEntity(sable)) {
                                    source.sendFailure(Component.literal("Failed to add Sable to world."));
                                    return 0;
                                }
                                source.sendSuccess(() -> Component.literal(
                                        "Spawned persistent vanilla Sable. AI jobs and Create milling are NOT active."), true);
                                return 1;
                            }))
                    .then(Commands.literal("assign_sable")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("target", BlockPosArgument.blockPos())
                                    .executes(ctx -> SableJobController.assign(ctx.getSource(),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "target")))))
                    .then(Commands.literal("haul_sable")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("source", BlockPosArgument.blockPos())
                                .then(Commands.argument("destination", BlockPosArgument.blockPos())
                                    .then(Commands.argument("count", IntegerArgumentType.integer(1, 64))
                                        .executes(ctx -> BarrelHaulController.assign(ctx.getSource(),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "source"),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "destination"),
                                            IntegerArgumentType.getInteger(ctx, "count")))))))
                    .then(Commands.literal("sable_status")
                            .executes(ctx -> SableJobController.status(ctx.getSource())))
                    .then(Commands.literal("cancel_sable")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> SableJobController.cancel(ctx.getSource()))));
        }
    }
}
