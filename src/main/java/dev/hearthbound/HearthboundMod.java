package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import dev.hearthbound.integration.MillstoneDiagnostics;
import dev.hearthbound.integration.ColonyInspectionCommands;
import dev.hearthbound.integration.CitizenRegistrySavedData;
import dev.hearthbound.integration.CitizenEmbodiment;
import dev.hearthbound.integration.MillstoneTrace;
import dev.hearthbound.integration.RuntimeInventoryDeltaChecks;
import com.mojang.brigadier.arguments.IntegerArgumentType;
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
                    .then(Commands.literal("mill_supply")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("citizen", net.minecraft.commands.arguments.UuidArgument.uuid())
                                    .then(Commands.argument("worksite", BlockPosArgument.blockPos())
                                            .executes(ctx -> {
                                                var source=ctx.getSource();
                                                var id=net.minecraft.commands.arguments.UuidArgument.getUuid(ctx,"citizen");
                                                var worksite=BlockPosArgument.getLoadedBlockPos(ctx,"worksite");
                                                var registry=CitizenRegistrySavedData.get(source.getServer());
                                                var villager=dev.hearthbound.integration.CitizenEmbodiment.find(source.getLevel(),id);
                                                var mill=source.getLevel().getBlockEntity(worksite.offset(1,0,0));
                                                if(villager==null || !(mill instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity)) {
                                                    source.sendFailure(Component.literal("Citizen villager or adjacent east-side millstone missing"));
                                                    return 0;
                                                }
                                                var player=source.getPlayerOrException();
                                                var held=player.getMainHandItem();
                                                if(!held.is(net.minecraft.world.item.Items.WHEAT) || held.getCount()<1) {
                                                    source.sendFailure(Component.literal("Hold wheat in main hand to fund citizen's task"));
                                                    return 0;
                                                }
                                                try {
                                                    registry.assignMillSupply(id,source.getLevel().dimension().location().toString(),
                                                            worksite.asLong(),ForgeServerTickObserver.logicalTick(source.getServer()));
                                                    villager.getPersistentData().putInt("HearthboundWheat",
                                                            villager.getPersistentData().getInt("HearthboundWheat")+1);
                                                    held.shrink(1);
                                                    source.sendSuccess(() -> Component.literal(
                                                            "Citizen assigned to deliver one player-funded wheat to millstone east of " + worksite),false);
                                                    return 1;
                                                } catch(IllegalArgumentException failure) {
                                                    source.sendFailure(Component.literal(failure.getMessage()));
                                                    return 0;
                                                }
                                            }))))
                    .then(Commands.literal("move")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("citizen", net.minecraft.commands.arguments.UuidArgument.uuid())
                                    .then(Commands.argument("target", BlockPosArgument.blockPos())
                                            .executes(ctx -> {
                                                var source = ctx.getSource();
                                                var id = net.minecraft.commands.arguments.UuidArgument.getUuid(ctx,"citizen");
                                                var target = BlockPosArgument.getLoadedBlockPos(ctx,"target");
                                                try {
                                                    var record = CitizenRegistrySavedData.get(source.getServer()).assignMove(
                                                            id,source.getLevel().dimension().location().toString(),
                                                            target.asLong(),ForgeServerTickObserver.logicalTick(source.getServer()));
                                                    source.sendSuccess(() -> Component.literal(
                                                            "Assigned citizen " + record.name() + " to " + target),false);
                                                    return 1;
                                                } catch(IllegalArgumentException failure) {
                                                    source.sendFailure(Component.literal(failure.getMessage()));
                                                    return 0;
                                                }
                                            }))))
                    .then(Commands.literal("citizen")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.literal("create")
                                    .executes(ctx -> {
                                        var source = ctx.getSource();
                                        var player = source.getPlayerOrException();
                                        var registry = CitizenRegistrySavedData.get(source.getServer());
                                        var id = java.util.UUID.randomUUID();
                                        var record = registry.register(id, "Settler-" + (registry.size() + 1),
                                                source.getLevel().dimension().location().toString(),
                                                player.blockPosition().asLong(),
                                                ForgeServerTickObserver.logicalTick(source.getServer()));
                                        var villager = CitizenEmbodiment.spawn(source.getLevel(), id,
                                                player.blockPosition());
                                        source.sendSuccess(() -> Component.literal("Created persistent citizen record "
                                                + record.name() + " id=" + record.id()
                                                + " entity=" + villager.getUUID() + " (visible villager embodiment)"), false);
                                        return 1;
                                    })))
                    .then(Commands.literal("citizens").requires(source -> source.hasPermission(2))
                            .executes(ColonyInspectionCommands::citizens))
                    .then(Commands.literal("tasks").requires(source -> source.hasPermission(2))
                            .executes(ColonyInspectionCommands::tasks))
                    .then(Commands.literal("observations").requires(source -> source.hasPermission(2))
                            .executes(ColonyInspectionCommands::observations)));
            dispatcher.register(Commands.literal("hearthbound")
                    .then(Commands.literal("millstone")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.literal("trace")
                                    .then(Commands.literal("verify_inventory_delta")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> {
                                try {
                                    int passed = RuntimeInventoryDeltaChecks.verify();
                                    ctx.getSource().sendSuccess(
                                            () -> Component.literal("Minecraft ItemStack checks passed=" + passed), false);
                                    return 1;
                                } catch (RuntimeException failure) {
                                    ctx.getSource().sendFailure(Component.literal(
                                            "Minecraft ItemStack checks failed: " + failure.getMessage()));
                                    return 0;
                                }
                            }))
                    .then(Commands.literal("status")
                                            .executes(ctx -> {
                                                ctx.getSource().sendSuccess(() -> Component.literal(MillstoneTrace.status()), false);
                                                return 1;
                                            }))
                                    .then(Commands.literal("stop")
                                            .executes(ctx -> {
                                                ctx.getSource().sendSuccess(() -> Component.literal(MillstoneTrace.stop()), false);
                                                return 1;
                                            }))
                                    .then(Commands.literal("start")
                                            .then(Commands.argument("pos", BlockPosArgument.blockPos())
                                                    .then(Commands.argument("ticks", IntegerArgumentType.integer(1, 1200))
                                                            .executes(ctx -> {
                                                                var pos = BlockPosArgument.getLoadedBlockPos(ctx, "pos");
                                                                var ticks = IntegerArgumentType.getInteger(ctx, "ticks");
                                                                try {
                                                                    var id = MillstoneTrace.begin(ctx.getSource().getLevel(), pos, ticks);
                                                                    ctx.getSource().sendSuccess(() -> Component.literal("Started diagnostic trace " + id), false);
                                                                    return 1;
                                                                } catch (IllegalArgumentException | IllegalStateException e) {
                                                                    ctx.getSource().sendFailure(Component.literal(e.getMessage()));
                                                                    return 0;
                                                                }
                                                            })))))
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
