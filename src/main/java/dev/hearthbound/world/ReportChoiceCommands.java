package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import dev.hearthbound.evidence.ReportConditionedChoice;
import java.util.ArrayList;
import java.util.List;
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
 * Operator-only, READ-ONLY paired report visibility experiment. Never reads
 * a block entity, opens an inventory, assigns a haul or updates ML weights.
 *
 * The exposure toggle controls whether previously DELIVERED recipient-owned
 * report NBT can enter a pre-action scripted source-ranking policy.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ReportChoiceCommands {
    private ReportChoiceCommands() {}

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("hearthbound-report-choice")
            .requires(source -> source.hasPermission(2))
            .then(Commands.argument("recipient", EntityArgument.entity())
                .then(Commands.argument("first", BlockPosArgument.blockPos())
                    .then(Commands.argument("second", BlockPosArgument.blockPos())
                        .then(Commands.argument("exposure", StringArgumentType.word())
                            .executes(ctx -> {
                                var source = ctx.getSource();
                                var entity = EntityArgument.getEntity(ctx, "recipient");
                                if (!(entity instanceof Villager recipient)) {
                                    source.sendFailure(Component.literal("Recipient must be a real villager"));
                                    return 0;
                                }
                                String exposure = StringArgumentType.getString(ctx, "exposure");
                                ReportConditionedChoice.Exposure treatment;
                                try {
                                    treatment = ReportConditionedChoice.Exposure.valueOf(
                                        exposure.toUpperCase(java.util.Locale.ROOT));
                                } catch (IllegalArgumentException invalid) {
                                    source.sendFailure(Component.literal("Exposure must be exposed or withheld"));
                                    return 0;
                                }
                                BlockPos first = BlockPosArgument.getBlockPos(ctx, "first");
                                BlockPos second = BlockPosArgument.getBlockPos(ctx, "second");
                                if (first.equals(second)) {
                                    source.sendFailure(Component.literal("Distinct source candidates required"));
                                    return 0;
                                }
                                String result = inspect(source.getLevel(), recipient,
                                    first, second, treatment);
                                source.sendSuccess(() -> Component.literal(result), false);
                                return 1; // a valid, read-only ABSTAIN is success
                            }))))));
    }

    static String key(ServerLevel level, BlockPos pos) {
        return level.dimension().location() + "|" + pos.getX() + ","
            + pos.getY() + "," + pos.getZ();
    }

    static ReportConditionedChoice.Report report(ServerLevel level,
                                                         Villager recipient, BlockPos source) {
        CompoundTag r = CitizenKnowledgeExchange.decisionReport(level, source, recipient);
        if (r == null) return null;
        return new ReportConditionedChoice.Report(r.getString("source"),
            recipient.getUUID(), r.getUUID("sender"), r.getString("origin"),
            r.getString("state"), r.getInt("wheat"), r.getInt("source_revision"),
            r.getLong("observed_tick"), r.getLong("delivered_tick"));
    }

    private static String inspect(ServerLevel level, Villager recipient,
                                  BlockPos first, BlockPos second,
                                  ReportConditionedChoice.Exposure exposure) {
        if (recipient.level() != level || !CitizenSourceKnowledge.isCitizen(recipient))
            return "REPORT_CHOICE status=DENIED reason=INVALID_RECIPIENT task_authorized=false";
        List<String> candidates = List.of(key(level, first), key(level, second));
        List<ReportConditionedChoice.Report> available = new ArrayList<>();
        if (exposure == ReportConditionedChoice.Exposure.EXPOSED) {
            // WITHHELD arm deliberately never accesses even existing report
            // NBT, and there is NO call to SourceWheatObservation.inspect.
            for (BlockPos pos : List.of(first, second)) {
                var r = report(level, recipient, pos);
                if (r != null) available.add(r);
            }
        }
        var choice = ReportConditionedChoice.choose(recipient.getUUID(),
            candidates, available, exposure, level.getGameTime());
        return "REPORT_CHOICE schema=hearthbound.report-choice.v1"
            + " status=" + choice.status()
            + " reason=" + choice.reason()
            + " recipient=" + recipient.getUUID()
            + " world=" + HearthboundWorldIdentity.get(level)
            + " tick=" + level.getGameTime()
            + " exposure=" + exposure
            + " policy=SCRIPTED_REPORT_RANK_V1"
            + " candidate_sources=" + String.join(";", candidates)
            + " selected=" + (choice.source() == null ? "NONE" : choice.source())
            + " admissible_reports=" + choice.admissibleReports()
            + " evidence_origin=RECIPIENT_DELIVERED_REPORT_ONLY"
            + " inventory_read=false sensor_triggered=false"
            + " task_authorized=false reward_authorized=false"
            + " learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
