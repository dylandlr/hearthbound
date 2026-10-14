package dev.hearthbound;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import dev.hearthbound.jobs.SableJobController;
import dev.hearthbound.create.CreateMillDiscovery;
import dev.hearthbound.create.MillstoneProbe;
import dev.hearthbound.create.MillstoneItemInput;
import dev.hearthbound.create.MillSupplyTransfer;
import dev.hearthbound.create.FlourCollection;
import dev.hearthbound.jobs.BarrelHaulController;
import dev.hearthbound.jobs.HaulE2EProbe;
import dev.hearthbound.jobs.HaulRestartProbe;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.phys.Vec3;
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
                    .then(Commands.literal("ci_flour_collect")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("mill", BlockPosArgument.blockPos())
                                .then(Commands.argument("storage", BlockPosArgument.blockPos())
                                    .then(Commands.argument("count", IntegerArgumentType.integer(1,64))
                                        .executes(ctx -> FlourCollection.collect(ctx.getSource(),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "mill"),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "storage"),
                                            IntegerArgumentType.getInteger(ctx, "count")))))))
                    .then(Commands.literal("ci_mill_supply")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("from", BlockPosArgument.blockPos())
                                .then(Commands.argument("mill", BlockPosArgument.blockPos())
                                    .then(Commands.argument("count", IntegerArgumentType.integer(1,64))
                                        .executes(ctx -> MillSupplyTransfer.transfer(ctx.getSource(),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "from"),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "mill"),
                                            IntegerArgumentType.getInteger(ctx, "count")))))))
                    .then(Commands.literal("ci_mill_feed")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("position", BlockPosArgument.blockPos())
                                .then(Commands.argument("count", IntegerArgumentType.integer(1,64))
                                    .executes(ctx -> MillstoneItemInput.feed(ctx.getSource(),
                                        BlockPosArgument.getLoadedBlockPos(ctx, "position"),
                                        IntegerArgumentType.getInteger(ctx, "count"))))))
                    .then(Commands.literal("ci_mill_nbt")
                            .requires(source -> source.hasPermission(2))
                            .then(Commands.argument("position", BlockPosArgument.blockPos())
                                .executes(ctx -> MillstoneProbe.inspect(ctx.getSource(),
                                    BlockPosArgument.getLoadedBlockPos(ctx, "position")))))
                    .then(Commands.literal("create_status")
                            .executes(ctx -> CreateMillDiscovery.status(ctx.getSource())))
                    .then(Commands.literal("inspect_mill")
                            .then(Commands.argument("position", BlockPosArgument.blockPos())
                                    .executes(ctx -> CreateMillDiscovery.inspect(ctx.getSource(),
                                            BlockPosArgument.getLoadedBlockPos(ctx, "position")))))
                    .then(Commands.literal("ci_haul_start")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulE2EProbe.start(ctx.getSource())))
                    .then(Commands.literal("ci_haul_full_start")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulE2EProbe.startFullDestination(ctx.getSource())))
                    .then(Commands.literal("ci_haul_block_after_pickup")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulE2EProbe.startBlockAfterPickup(ctx.getSource())))
                    .then(Commands.literal("ci_restart_stage")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulE2EProbe.startRestart(ctx.getSource())))
                    .then(Commands.literal("ci_restart_unblock")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulRestartProbe.unblock(ctx.getSource())))
                    .then(Commands.literal("ci_restart_delivered")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulRestartProbe.delivered(ctx.getSource())))
                    .then(Commands.literal("ci_restart_check")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulRestartProbe.check(ctx.getSource())))
                    .then(Commands.literal("ci_haul_check")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> HaulE2EProbe.check(ctx.getSource())))
                    .then(Commands.literal("ci_probe")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> {
                                ServerLevel level = ctx.getSource().getLevel();
                                BlockPos center = BlockPos.containing(ctx.getSource().getPosition());
                                // World mutations occur on the Minecraft server command thread.
                                BlockPos sourcePos = center.offset(2, 0, 0);
                                BlockPos destPos = center.offset(4, 0, 0);
                                if (!level.hasChunkAt(sourcePos) || !level.hasChunkAt(destPos)) {
                                    ctx.getSource().sendFailure(Component.literal("HB_CI_PROBE_FAIL chunks"));
                                    return 0;
                                }
                                level.setBlockAndUpdate(sourcePos, Blocks.BARREL.defaultBlockState());
                                level.setBlockAndUpdate(destPos, Blocks.BARREL.defaultBlockState());
                                if (!(level.getBlockEntity(sourcePos) instanceof BarrelBlockEntity input)
                                        || !(level.getBlockEntity(destPos) instanceof BarrelBlockEntity output)) {
                                    ctx.getSource().sendFailure(Component.literal("HB_CI_PROBE_FAIL barrels"));
                                    return 0;
                                }
                                input.setItem(0, new ItemStack(Items.WHEAT, 8));
                                boolean ok = input.getItem(0).getCount() == 8
                                        && output.isEmpty();
                                Villager probe = EntityType.VILLAGER.create(level);
                                if (probe == null) ok = false;
                                else {
                                    probe.moveTo(center.getX() + .5, center.getY(), center.getZ() + .5,
                                            0.0F, 0.0F);
                                    SableJobController.markSable(probe);
                                    probe.setCustomName(Component.literal("Sable [CI probe]"));
                                    probe.setPersistenceRequired();
                                    ok = level.addFreshEntity(probe)
                                            && probe.getTags().contains("hearthbound.sable") && ok;
                                    probe.discard();
                                }
                                final boolean passed = ok;
                                if (!passed) {
                                    ctx.getSource().sendFailure(Component.literal("HB_CI_PROBE_FAIL entity_or_inventory"));
                                    return 0;
                                }
                                ctx.getSource().sendSuccess(
                                        () -> Component.literal("HB_CI_PROBE_PASS real_barrels_wheat_8_tagged_villager"),
                                        true);
                                return 1;
                            }))
                    .then(Commands.literal("ci_haul_probe")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> {
                                ServerLevel level = ctx.getSource().getLevel();
                                BlockPos center = BlockPos.containing(ctx.getSource().getPosition());
                                BlockPos inputPos = center.offset(2, 0, 0);
                                BlockPos outputPos = center.offset(4, 0, 0);
                                level.setBlockAndUpdate(inputPos, Blocks.BARREL.defaultBlockState());
                                level.setBlockAndUpdate(outputPos, Blocks.BARREL.defaultBlockState());
                                if (!(level.getBlockEntity(inputPos) instanceof BarrelBlockEntity input)
                                        || !(level.getBlockEntity(outputPos) instanceof BarrelBlockEntity output)) {
                                    ctx.getSource().sendFailure(Component.literal("HB_HAUL_FAIL setup"));
                                    return 0;
                                }
                                input.setItem(0, new ItemStack(Items.WHEAT, 8));
                                int baseline = input.getItem(0).getCount();
                                // Stage 1: real-world inventory presence. No synthetic claim of item transport.
                                if (baseline != 8 || !output.isEmpty()) {
                                    ctx.getSource().sendFailure(Component.literal("HB_HAUL_FAIL baseline"));
                                    return 0;
                                }
                                ctx.getSource().sendSuccess(() -> Component.literal(
                                        "HB_HAUL_SETUP_PASS source=8 destination=0; physical movement not yet tested"), true);
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
                    .then(Commands.literal("haul_status")
                            .executes(ctx -> BarrelHaulController.status(ctx.getSource())))
                    .then(Commands.literal("sable_status")
                            .executes(ctx -> SableJobController.status(ctx.getSource())))
                    .then(Commands.literal("cancel_sable")
                            .requires(source -> source.hasPermission(2))
                            .executes(ctx -> SableJobController.cancel(ctx.getSource()))));
        }
    }
}
