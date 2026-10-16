package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;
import dev.hearthbound.research.LibraryStudyRuntime;
import dev.hearthbound.research.CitizenTechnologyKnowledge;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/** Bootstrap only: no fabricated Create integration or citizen AI yet. */
@Mod(HearthboundMod.MOD_ID)
public final class HearthboundMod {
    public static final String MOD_ID = "hearthbound";
    private static final Logger LOGGER = LogManager.getLogger();

    public HearthboundMod() {
        LOGGER.info("Hearthbound bootstrap loaded. First Mill controller not installed yet.");
    }

    @Mod.EventBusSubscriber(modid = MOD_ID)
    public static final class CommandsHandler {
        @SubscribeEvent
        public static void onCommands(RegisterCommandsEvent event) {
            CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
            dispatcher.register(Commands.literal("hearthbound")
                    .then(Commands.literal("library")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.literal("study")
                                    .then(Commands.argument("shelf", BlockPosArgument.blockPos())
                                            .executes(ctx -> {
                                                var source = ctx.getSource();
                                                BlockPos shelf = BlockPosArgument.getLoadedBlockPos(ctx, "shelf");
                                                Villager citizen = nearestVillager(source);
                                                if (citizen == null) {
                                                    source.sendFailure(Component.literal("No villager within 8 blocks"));
                                                    return 0;
                                                }
                                                try {
                                                    LibraryStudyRuntime.begin(source.getLevel(), citizen, shelf, 60);
                                                    source.sendSuccess(
                                                            () -> Component.literal("Library study started for " + citizen.getUUID()),
                                                            false);
                                                    return 1;
                                                } catch (IllegalArgumentException | IllegalStateException ex) {
                                                    source.sendFailure(Component.literal("Library study rejected: " + ex.getMessage()));
                                                    return 0;
                                                }
                                            })))
                            .then(Commands.literal("inspect")
                                    .executes(ctx -> {
                                        Villager citizen = nearestVillager(ctx.getSource());
                                        if (citizen == null) {
                                            ctx.getSource().sendFailure(Component.literal("No villager within 8 blocks"));
                                            return 0;
                                        }
                                        ctx.getSource().sendSuccess(
                                                () -> Component.literal(LibraryStudyRuntime.inspect(citizen)
                                                        + " " + CitizenTechnologyKnowledge.inspect(citizen)), false);
                                        return 1;
                                    }))))
                    .then(Commands.literal("status")
                            .executes(ctx -> {
                                ctx.getSource().sendSuccess(
                                        () -> Component.literal("Hearthbound 0.1 dev: bootstrap active. Citizen and Create controllers pending."),
                                        false);
                                return 1;
                            })));
        }
    }

    private static Villager nearestVillager(CommandSourceStack source) {
        var origin = source.getPosition();
        return source.getLevel().getEntitiesOfClass(
                        Villager.class, new AABB(origin, origin).inflate(8.0))
                .stream()
                .min(java.util.Comparator.comparingDouble(citizen -> citizen.distanceToSqr(origin)))
                .orElse(null);
    }
}
