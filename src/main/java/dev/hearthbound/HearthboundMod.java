package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import dev.hearthbound.integration.MillstoneDiagnostics;
import dev.hearthbound.integration.ForgeServerTickObserver;
import net.minecraftforge.fml.ModList;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
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
                    .then(Commands.literal("millstone")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.literal("inspect")
                                    .then(Commands.argument("pos", BlockPosArgument.blockPos())
                                            .executes(MillstoneDiagnostics::inspect))))
                    .then(Commands.literal("status")
                            .executes(ctx -> {
                                ctx.getSource().sendSuccess(
                                        ()-> Component.literal(
                                                "Hearthbound bootstrap=loaded; Create=" +
                                                (ModList.get().isLoaded("create") ? "loaded" : "MISSING") +
                                                "; logicalTick=" + ForgeServerTickObserver.logicalTick(ctx.getSource().getServer()) +
                                                "; dimension=" + ctx.getSource().getLevel().dimension().location() +
                                                "; researchBridge=not-connected"),
                                        false);
                                return ModList.get().isLoaded("create") ? 1 : 0;
                            })));
        }
    }
}
