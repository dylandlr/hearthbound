package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.util.UUID;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import dev.hearthbound.ai.ActionGate;
import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryStudyRuntime;
import dev.hearthbound.ai.ColonyPolicy;
import dev.hearthbound.ai.PriorityPolicy;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.player.Player;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.List;

/**
 * Minimal Minecraft embodiment: spawn a real villager and follow nearby players.
 * This intentionally does not claim to implement jobs, inventories or Create machinery.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class SableController {
    private static final String MARKER = "hearthbound.sable";
    private static final PriorityPolicy POLICY = new PriorityPolicy();

    private SableController() {}

    @SubscribeEvent
    public static void onServerStopped(ServerStoppedEvent event) {
        SableHauling.serverStopped(event.getServer());
    }

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("sable")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("spawn").executes(ctx -> {
                CommandSourceStack source = ctx.getSource();
                ServerLevel level = source.getLevel();
                Villager villager = EntityType.VILLAGER.create(level);
                if (villager == null) return 0;
                villager.moveTo(source.getPosition().x, source.getPosition().y,
                    source.getPosition().z, 0.0F, 0.0F);
                villager.getPersistentData().putBoolean(MARKER, true);
                villager.setCustomName(Component.literal("Sable"));
                villager.setCustomNameVisible(true);
                villager.setPersistenceRequired();
                if (!level.addFreshEntity(villager)) {
                    source.sendFailure(Component.literal("Unable to spawn Sable."));
                    return 0;
                }
                source.sendSuccess(() -> Component.literal("Sable spawned. She will follow nearby players."), true);
                return 1;
            }))
            .then(Commands.literal("haul")
                .then(Commands.argument("source", BlockPosArgument.blockPos())
                    .then(Commands.argument("destination", BlockPosArgument.blockPos())
                        .executes(ctx -> {
                            CommandSourceStack source = ctx.getSource();
                            Villager sable = nearestSable(source);
                            if (sable == null) {
                                source.sendFailure(Component.literal("No Sable within 16 blocks."));
                                return 0;
                            }
                            BlockPos from = BlockPosArgument.getLoadedBlockPos(ctx, "source");
                            BlockPos to = BlockPosArgument.getLoadedBlockPos(ctx, "destination");
                            try {
                                SableHauling.assign(levelOf(sable), sable, from, to);
                            } catch (IllegalArgumentException | IllegalStateException ex) {
                                source.sendFailure(Component.literal(ex.getMessage()));
                                return 0;
                            }
                            source.sendSuccess(() -> Component.literal("Sable assigned wheat haul."), true);
                            return 1;
                        }))))
            .then(Commands.literal("haul-priority")
                .then(Commands.argument("level", com.mojang.brigadier.arguments.IntegerArgumentType.integer(0,4))
                    .executes(ctx -> {
                        Villager sable = nearestSable(ctx.getSource());
                        if (sable == null) return 0;
                        SableWorkChoice.haulPriority(sable,
                                com.mojang.brigadier.arguments.IntegerArgumentType.getInteger(ctx,"level"));
                        ctx.getSource().sendSuccess(() -> Component.literal(
                                "Haul priority now " + SableWorkChoice.haulPriority(sable)), false);
                        return 1;
                    })))
            .then(Commands.literal("auto-work-config")
                .then(Commands.argument("source", BlockPosArgument.blockPos())
                    .then(Commands.argument("destination", BlockPosArgument.blockPos())
                        .then(Commands.argument("library", BlockPosArgument.blockPos())
                            .executes(ctx -> {
                                Villager sable = nearestSable(ctx.getSource());
                                if (sable == null) return 0;
                                try {
                                    SableAutoWork.configure(ctx.getSource().getLevel(), sable,
                                            BlockPosArgument.getLoadedBlockPos(ctx,"source"),
                                            BlockPosArgument.getLoadedBlockPos(ctx,"destination"),
                                            BlockPosArgument.getLoadedBlockPos(ctx,"library"));
                                    ctx.getSource().sendSuccess(() -> Component.literal(
                                            "Configured Sable auto work, initially OFF"), false);
                                    return 1;
                                } catch (IllegalStateException | IllegalArgumentException ex) {
                                    ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                                    return 0;
                                }
                            })))))
            .then(Commands.literal("auto-work-on").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                try {
                    SableAutoWork.enable(sable,true);
                    dev.hearthbound.research.LibraryAutonomyTick.setEnabled(sable,false);
                    ctx.getSource().sendSuccess(() -> Component.literal(
                            "Auto work enabled; independent library loop disabled"), false);
                    return 1;
                } catch (IllegalStateException ex) {
                    ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                    return 0;
                }
            }))
            .then(Commands.literal("auto-work-off").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                SableAutoWork.enable(sable,false);
                ctx.getSource().sendSuccess(() -> Component.literal("Auto work disabled"),false);
                return 1;
            }))
            .then(Commands.literal("auto-work-status").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                ctx.getSource().sendSuccess(() -> Component.literal(
                        SableAutoWork.inspect(sable) + " " + SableWorkChoice.inspect(sable)),false);
                return 1;
            }))
            .then(Commands.literal("work-choice-inspect").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                ctx.getSource().sendSuccess(() -> Component.literal(
                        SableWorkChoice.inspect(sable)), false);
                return 1;
            }))
            .then(Commands.literal("choose-work")
                .then(Commands.argument("source", BlockPosArgument.blockPos())
                    .then(Commands.argument("destination", BlockPosArgument.blockPos())
                        .then(Commands.argument("library", BlockPosArgument.blockPos())
                            .executes(ctx -> {
                                Villager sable = nearestSable(ctx.getSource());
                                if (sable == null) {
                                    ctx.getSource().sendFailure(Component.literal("No Sable nearby"));
                                    return 0;
                                }
                                try {
                                    String outcome = SableWorkChoice.consider(ctx.getSource().getLevel(),
                                            sable,
                                            BlockPosArgument.getLoadedBlockPos(ctx,"source"),
                                            BlockPosArgument.getLoadedBlockPos(ctx,"destination"),
                                            BlockPosArgument.getLoadedBlockPos(ctx,"library"));
                                    ctx.getSource().sendSuccess(() -> Component.literal(outcome), false);
                                    return outcome.endsWith("_ASSIGNED") ? 1 : 0;
                                } catch (IllegalArgumentException | IllegalStateException ex) {
                                    ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                                    return 0;
                                }
                            })))))
            .then(Commands.literal("fault-insert-before").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                try {
                    SableHauling.injectInsertionFault(sable, false);
                    ctx.getSource().sendSuccess(() -> Component.literal("Injection armed: before insertion"), false);
                    return 1;
                } catch (IllegalStateException ex) {
                    ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                    return 0;
                }
            }))
            .then(Commands.literal("fault-insert-after").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                try {
                    SableHauling.injectInsertionFault(sable, true);
                    ctx.getSource().sendSuccess(() -> Component.literal("Injection armed: after insertion"), false);
                    return 1;
                } catch (IllegalStateException ex) {
                    ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                    return 0;
                }
            }))
            .then(Commands.literal("haul-reconcile-close")
                .then(Commands.argument("jobId", StringArgumentType.word())
                    .executes(ctx -> {
                        Villager sable = nearestSable(ctx.getSource());
                        if (sable == null) {
                            ctx.getSource().sendFailure(Component.literal("No Sable within 16 blocks."));
                            return 0;
                        }
                        try {
                            UUID expected = UUID.fromString(StringArgumentType.getString(ctx, "jobId"));
                            SableHauling.closeReconciled(ctx.getSource().getLevel(), sable, expected);
                            ctx.getSource().sendSuccess(() -> Component.literal(
                                "Reconciled cargo-free job closed; claim released. No delivery credit awarded."), true);
                            return 1;
                        } catch (IllegalArgumentException | IllegalStateException ex) {
                            ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                            return 0;
                        }
                    })))
            .then(Commands.literal("mill-release")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .then(Commands.argument("jobId", StringArgumentType.word())
                        .executes(ctx -> {
                            Villager sable = nearestSable(ctx.getSource());
                            if (sable == null) {
                                ctx.getSource().sendFailure(Component.literal("No citizen within 16 blocks"));
                                return 0;
                            }
                            try {
                                BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                                UUID job = UUID.fromString(StringArgumentType.getString(ctx, "jobId"));
                                MillReservations.releaseCompleted(ctx.getSource().getLevel(), pos, job, sable);
                                ctx.getSource().sendSuccess(() -> Component.literal(
                                    "Mill reservation released with audit tombstone; no research credit"), true);
                                return 1;
                            } catch (IllegalArgumentException | IllegalStateException ex) {
                                ctx.getSource().sendFailure(Component.literal(ex.getMessage()));
                                return 0;
                            }
                        }))))
            .then(Commands.literal("mill-probe-open-belt")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        ServerLevel level = ctx.getSource().getLevel();
                        if (MillReservations.held(level, pos)) {
                            ctx.getSource().sendFailure(Component.literal("Positive control requires unreserved millstone"));
                            return 0;
                        }
                        var block = level.getBlockEntity(pos);
                        if (!(block instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity mill))
                            return 0;
                        var behaviour = com.simibubi.create.foundation.blockEntity.behaviour.BlockEntityBehaviour.get(
                            mill, com.simibubi.create.content.kinetics.belt.behaviour.DirectBeltInputBehaviour.TYPE);
                        if (behaviour == null) return 0;
                        var wheat = new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.WHEAT);
                        var remainder = behaviour.handleInsertion(wheat, net.minecraft.core.Direction.NORTH, false);
                        boolean accepted = remainder.isEmpty();
                        ctx.getSource().sendSuccess(() -> Component.literal(accepted
                            ? "OPEN_BELT ACCEPTED NO_RESEARCH_CREDIT"
                            : "OPEN_BELT REJECTED NO_RESEARCH_CREDIT"), false);
                        return accepted ? 1 : 0;
                    })))
            .then(Commands.literal("mill-probe-belt-insert")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        ServerLevel level = ctx.getSource().getLevel();
                        if (!MillReservations.held(level, pos)) {
                            ctx.getSource().sendFailure(Component.literal("Probe requires a reserved millstone"));
                            return 0;
                        }
                        var block = level.getBlockEntity(pos);
                        if (!(block instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity mill))
                            return 0;
                        var behaviour = com.simibubi.create.foundation.blockEntity.behaviour.BlockEntityBehaviour.get(
                            mill, com.simibubi.create.content.kinetics.belt.behaviour.DirectBeltInputBehaviour.TYPE);
                        if (behaviour == null) return 0;
                        var wheat = new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.WHEAT);
                        var remainder = behaviour.handleInsertion(wheat, net.minecraft.core.Direction.NORTH, false);
                        boolean denied = remainder.getCount() == 1;
                        String result = denied ? "BELT_INSERT DENIED NO_RESEARCH_CREDIT"
                            : "BELT_INSERT ACCEPTED WARNING_NO_RESEARCH_CREDIT";
                        ctx.getSource().sendSuccess(() -> Component.literal(result), false);
                        return denied ? 1 : 0;
                    })))
            .then(Commands.literal("mill-probe-external-insert")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        ServerLevel level = ctx.getSource().getLevel();
                        if (!MillReservations.held(level, pos)) {
                            ctx.getSource().sendFailure(Component.literal("Probe requires a reserved millstone"));
                            return 0;
                        }
                        var block = level.getBlockEntity(pos);
                        if (block == null) return 0;
                        var capability = block.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER);
                        if (!capability.isPresent()) return 0;
                        var handler = capability.orElseThrow(IllegalStateException::new);
                        var wheat = new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.WHEAT);
                        var remaining = handler.insertItem(0, wheat, false);
                        boolean denied = remaining.getCount() == 1;
                        String result = denied ? "EXTERNAL_INSERT DENIED NO_RESEARCH_CREDIT"
                            : "EXTERNAL_INSERT ACCEPTED WARNING_NO_RESEARCH_CREDIT";
                        ctx.getSource().sendSuccess(() -> Component.literal(result), false);
                        return denied ? 1 : 0;
                    })))
            .then(Commands.literal("mill-reservation")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        String audit = MillReservations.audit(ctx.getSource().getLevel(), pos);
                        ctx.getSource().sendSuccess(() -> Component.literal(audit), false);
                        return 1;
                    })))
            .then(Commands.literal("mill-process")
                .then(Commands.argument("jobId", StringArgumentType.word())
                    .executes(ctx -> {
                        try {
                            UUID job = UUID.fromString(StringArgumentType.getString(ctx, "jobId"));
                            String receipt = MillProcessReceipts.inspect(ctx.getSource().getLevel(), job);
                            ctx.getSource().sendSuccess(() -> Component.literal(receipt), false);
                            return 1;
                        } catch (IllegalArgumentException ex) {
                            ctx.getSource().sendFailure(Component.literal("Invalid job UUID"));
                            return 0;
                        }
                    })))
            .then(Commands.literal("mill-evidence")
                .then(Commands.argument("jobId", StringArgumentType.word())
                    .executes(ctx -> {
                        try {
                            UUID job = UUID.fromString(StringArgumentType.getString(ctx, "jobId"));
                            String receipt = MillEvidenceJournal.inspect(ctx.getSource().getLevel(), job);
                            ctx.getSource().sendSuccess(() -> Component.literal(receipt), false);
                            return 1;
                        } catch (IllegalArgumentException ex) {
                            ctx.getSource().sendFailure(Component.literal("Invalid job UUID"));
                            return 0;
                        }
                    })))
            .then(Commands.literal("mill-trace").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) {
                    ctx.getSource().sendFailure(Component.literal("No Sable within 16 blocks."));
                    return 0;
                }
                String trace = MillExperimentTrace.observe(ctx.getSource().getLevel(), sable);
                ctx.getSource().sendSuccess(() -> Component.literal(trace), false);
                return 1;
            }))
            .then(Commands.literal("mill-inspect")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        String observation = MillInspector.inspect(ctx.getSource().getLevel(), pos);
                        ctx.getSource().sendSuccess(() -> Component.literal(observation), false);
                        return 1;
                    })))
            .then(Commands.literal("haul-audit").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) {
                    ctx.getSource().sendFailure(Component.literal("No Sable within 16 blocks."));
                    return 0;
                }
                String snapshot = SableHauling.audit(ctx.getSource().getLevel(), sable);
                ctx.getSource().sendSuccess(() -> Component.literal(snapshot), false);
                return 1;
            }))
            .then(Commands.literal("haul-status").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null) return 0;
                ctx.getSource().sendSuccess(() -> Component.literal(SableHauling.status(sable)), false);
                return 1;
            }))
            .then(Commands.literal("haul-cancel").executes(ctx -> {
                CommandSourceStack source = ctx.getSource();
                Villager sable = nearestSable(source);
                if (sable == null) {
                    source.sendFailure(Component.literal("No Sable within 16 blocks."));
                    return 0;
                }
                if (!SableHauling.cancelBeforePickup(source.getLevel(), sable)) {
                    source.sendFailure(Component.literal(
                        "Cannot cancel: cargo may be in transit. Deliver or reconcile it first."));
                    return 0;
                }
                source.sendSuccess(() -> Component.literal("Unpicked haul cancelled; source released."), true);
                return 1;
            }))
            .then(Commands.literal("haul-resume").executes(ctx -> {
                Villager sable = nearestSable(ctx.getSource());
                if (sable == null || !SableHauling.resume(sable)) return 0;
                ctx.getSource().sendSuccess(() -> Component.literal("Hauling resumed."), true);
                return 1;
            })));
    }

    private static ServerLevel levelOf(Villager villager) {
        return (ServerLevel) villager.level();
    }

    private static Villager nearestSable(CommandSourceStack source) {
        return source.getLevel().getEntitiesOfClass(Villager.class,
            new net.minecraft.world.phys.AABB(net.minecraft.core.BlockPos.containing(source.getPosition())).inflate(16),
            v -> v.getPersistentData().getBoolean(MARKER))
            .stream().min(java.util.Comparator.comparingDouble(
                v -> v.distanceToSqr(source.getPosition().x, source.getPosition().y, source.getPosition().z))).orElse(null);
    }

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager villager)) return;
        if (!(villager.level() instanceof ServerLevel level)) return;
        if (!villager.getPersistentData().getBoolean(MARKER)) return;
        MillExperimentTrace.monitorAuthorizedInput(level, villager);
        if (villager.tickCount % 20 != 0) return;
        // Observation is read-only with respect to the millstone and never
        // awards research points or knowledge unlocks.
        MillExperimentTrace.sampleCycle(level, villager);

        if (SableHauling.active(villager)) {
            SableHauling.tick(level, villager);
            return;
        }

        // Existing library executor owns navigation until it finishes or fails.
        if (AutonomousLibraryStudy.active(villager)
                || LibraryStudyRuntime.state(villager) == LibraryStudyRuntime.State.STUDYING) {
            return;
        }

        SableAutoWork.tick(level, villager);
        if (SableHauling.active(villager) || AutonomousLibraryStudy.active(villager)
                || LibraryStudyRuntime.state(villager) == LibraryStudyRuntime.State.STUDYING)
            return;

        Player target = level.getNearestPlayer(villager, 12.0D);
        if (target == null || target.isSpectator()) {
            villager.getNavigation().stop();
            return;
        }

        double distanceSquared = villager.distanceToSqr(target);
        boolean needsToFollow = distanceSquared > 9.0D && distanceSquared <= 144.0D;
        ColonyPolicy.Action follow = new ColonyPolicy.Action(
            "follow-nearest-player", ColonyPolicy.Kind.FOLLOW, 0, needsToFollow);
        ColonyPolicy.Observation snapshot = new ColonyPolicy.Observation(
            villager.tickCount, villager.getUUID().toString(), 0, 0, 0, List.of(follow));
        ColonyPolicy.Decision decision = POLICY.choose(snapshot);

        // This is the server-side authority boundary, not arbitrary policy-driven mutation.
        if (ActionGate.allowed(snapshot, decision) && "follow-nearest-player".equals(decision.actionId())) {
            villager.getNavigation().moveTo(target, 0.85D);
        } else if (distanceSquared <= 9.0D) {
            villager.getNavigation().stop();
        }
    }
}
