package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import com.mojang.brigadier.arguments.StringArgumentType;
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
                    .then(Commands.literal("policy_probe")
                            .then(Commands.argument("mill", BlockPosArgument.blockPos())
                                    .executes(ctx -> {
                                        var pos = BlockPosArgument.getLoadedBlockPos(ctx, "mill");
                                        String result = dev.hearthbound.world.LivePolicyProbe.inspect(
                                            ctx.getSource().getLevel(), pos);
                                        ctx.getSource().sendSuccess(
                                            () -> Component.literal(result), false);
                                        return 1;
                                    })))
                    .then(Commands.literal("policy_shadow")
                            .then(Commands.argument("mill", BlockPosArgument.blockPos())
                                .then(Commands.argument("mode", StringArgumentType.word())
                                    .executes(ctx -> {
                                        String name = StringArgumentType.getString(ctx, "mode");
                                        dev.hearthbound.evidence.MillPolicyShadow.Mode mode;
                                        try {
                                            mode = dev.hearthbound.evidence.MillPolicyShadow.Mode.valueOf(
                                                name.toUpperCase(java.util.Locale.ROOT));
                                        } catch (IllegalArgumentException invalid) {
                                            ctx.getSource().sendFailure(
                                                Component.literal("Invalid mode: use SCRIPTED or TRAINED_MLP"));
                                            return 0;
                                        }
                                        var pos = BlockPosArgument.getLoadedBlockPos(ctx, "mill");
                                        String result = dev.hearthbound.world.LivePolicyProbe.inspect(
                                            ctx.getSource().getLevel(), pos, mode);
                                        ctx.getSource().sendSuccess(
                                            () -> Component.literal(result), false);
                                        return 1;
                                    }))))
                    .then(Commands.literal("policy_trial")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("source", BlockPosArgument.blockPos())
                                .then(Commands.argument("mill", BlockPosArgument.blockPos())
                                    .then(Commands.argument("mode", StringArgumentType.word())
                                        .executes(ctx -> {
                                            String label = StringArgumentType.getString(ctx, "mode");
                                            dev.hearthbound.evidence.MillPolicyShadow.Mode mode;
                                            try {
                                                mode = dev.hearthbound.evidence.MillPolicyShadow.Mode.valueOf(
                                                    label.toUpperCase(java.util.Locale.ROOT));
                                            } catch (IllegalArgumentException invalid) {
                                                ctx.getSource().sendFailure(
                                                    Component.literal("Expected SCRIPTED or TRAINED_MLP"));
                                                return 0;
                                            }
                                            try {
                                                var from = BlockPosArgument.getLoadedBlockPos(ctx,"source");
                                                var to = BlockPosArgument.getLoadedBlockPos(ctx,"mill");
                                                var message = dev.hearthbound.world.MillPolicyTrial.assignOne(
                                                    ctx.getSource().getLevel(),from,to,mode);
                                                ctx.getSource().sendSuccess(
                                                    () -> Component.literal(message),true);
                                                return 1;
                                            } catch (IllegalArgumentException | IllegalStateException failure) {
                                                ctx.getSource().sendFailure(Component.literal(failure.getMessage()));
                                                return 0;
                                            }
                                        })))))
                    .then(Commands.literal("research_status")
                            .executes(ctx -> {
                                ctx.getSource().sendSuccess(
                                        () -> Component.literal(dev.hearthbound.world.ResearchStartupObserver.status()),
                                        false);
                                return 1;
                            }))
                    .then(Commands.literal("status")
                            .executes(ctx -> {
                                ctx.getSource().sendSuccess(
                                        () -> Component.literal("Hearthbound 0.1 dev: bootstrap active. Citizen and Create controllers pending."),
                                        false);
                                return 1;
                            })));
        }
    }
}
