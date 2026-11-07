package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import dev.hearthbound.evidence.ReportChoiceMlp;
import dev.hearthbound.evidence.ReportConditionedChoice;
import java.nio.file.Path;
import java.util.Locale;
import java.util.List;
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
 * Operator-only frozen neural shadow. The only access to observations is
 * recipient's ALREADY DELIVERED NBT reports. No Minecraft inventory reads,
 * job assignment, recipe unlock, gradients, or reward delivery.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ReportChoiceMlpCommands {
    private static ReportChoiceMlp frozen;
    private ReportChoiceMlpCommands() {}

    private static synchronized ReportChoiceMlp model() throws Exception {
        if (frozen == null) {
            // Forge runServer working directory is ./run. A SHA manifest and
            // immutable weights are generated before the server boots.
            frozen = ReportChoiceMlp.load(
                Path.of("report-choice-mlp-v1.txt"),
                Path.of("report-choice-mlp-v1.sha256"));
        }
        return frozen;
    }

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();
        dispatcher.register(Commands.literal("hearthbound-report-mlp-choice")
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
                                String text = StringArgumentType.getString(ctx, "exposure");
                                ReportConditionedChoice.Exposure exposure;
                                try {
                                    exposure = ReportConditionedChoice.Exposure.valueOf(
                                        text.toUpperCase(Locale.ROOT));
                                } catch (IllegalArgumentException invalid) {
                                    source.sendFailure(Component.literal("Exposure must be exposed or withheld"));
                                    return 0;
                                }
                                BlockPos a = BlockPosArgument.getBlockPos(ctx, "first");
                                BlockPos b = BlockPosArgument.getBlockPos(ctx, "second");
                                if (a.equals(b)) {
                                    source.sendFailure(Component.literal("Distinct source candidates required"));
                                    return 0;
                                }
                                String result = inspect(source.getLevel(), recipient, a, b, exposure);
                                source.sendSuccess(() -> Component.literal(result), false);
                                return result.contains("status=DENIED") ? 0 : 1;
                            }))))));
    }

    private static String denied(String reason) {
        return "REPORT_MLP_CHOICE status=DENIED reason=" + reason
            + " task_authorized=false reward_authorized=false"
            + " learning_authorized=false NO_RESEARCH_CREDIT";
    }

    public static String inspect(ServerLevel level, Villager recipient, BlockPos first,
                                 BlockPos second, ReportConditionedChoice.Exposure exposure) {
        if (level == null || recipient == null || first == null || second == null
                || recipient.level() != level || !CitizenSourceKnowledge.isCitizen(recipient)
                || first.equals(second) || exposure == null)
            return denied("INVALID_REQUEST");
        String selected = "NONE";
        String status = "ABSTAIN";
        int admissible = 0;
        String reason = "REPORT_EXPOSURE_WITHHELD";
        String sha = "NOT_LOADED_WITHHELD";
        long tick = level.getGameTime();

        if (exposure == ReportConditionedChoice.Exposure.EXPOSED) {
            double[] features = new double[ReportChoiceMlp.INPUT];
            // Exactly the same source keys and recipient-scoped accessors as
            // SCRIPTED_REPORT_RANK_V1; NO SourceWheatObservation.inspect().
            List<BlockPos> candidates = List.of(first, second);
            try {
                for (int i = 0; i < candidates.size(); i++) {
                    var report = ReportChoiceCommands.report(level, recipient, candidates.get(i));
                    if (report == null) continue;
                    long age = tick - report.deliveredTick();
                    long observedAge = tick - report.observedTick();
                    ReportChoiceMlp.encode(features, i, report.wheat(), age,
                        observedAge, report.revision(), true);
                    admissible++;
                }
                ReportChoiceMlp model = model();
                sha = model.sha256();
                var action = model.choose(features);
                if (action != ReportChoiceMlp.Action.ABSTAIN) {
                    int idx = action == ReportChoiceMlp.Action.SOURCE_A ? 0 : 1;
                    selected = ReportChoiceCommands.key(level, candidates.get(idx));
                    status = "CHOOSE";
                    reason = "FROZEN_SIMULATED_OUTCOME_REGRESSION";
                } else {
                    reason = "MODEL_ABSTAIN_OR_NO_REPORT";
                }
            } catch (Exception ex) {
                return denied("FROZEN_MODEL_OR_REPORT_VALIDATION_FAILED");
            }
        }
        return "REPORT_MLP_CHOICE schema=hearthbound.report-mlp-choice.v1"
            + " status=" + status + " reason=" + reason
            + " recipient=" + recipient.getUUID()
            + " world=" + HearthboundWorldIdentity.get(level)
            + " tick=" + tick
            + " exposure=" + exposure
            + " policy=SIMULATOR_TRAINED_FROZEN_MLP"
            + " model_sha256=" + sha
            + " candidate_sources=" + ReportChoiceCommands.key(level, first)
                + ";" + ReportChoiceCommands.key(level, second)
            + " selected=" + selected
            + " admissible_reports=" + admissible
            + " evidence_origin=RECIPIENT_DELIVERED_REPORT_ONLY"
            + " inventory_read=false sensor_triggered=false"
            + " task_authorized=false reward_authorized=false"
            + " learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
