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

    /**
     * A decision snapshot created before work is assigned on Minecraft's
     * authoritative server thread. No block entity or inventory is read.
     * Both the shadow command and the physical dispatch call THIS method.
     */
    static record Choice(ReportChoiceMlp.Action action, BlockPos selected,
                         String modelSha256, int reports, long tick,
                         String reason, String reportId) {}

    static Choice evaluate(ServerLevel level, Villager recipient, BlockPos first,
                           BlockPos second, ReportConditionedChoice.Exposure exposure)
                           throws Exception {
        if (level == null || recipient == null || first == null || second == null
                || recipient.level() != level || !CitizenSourceKnowledge.isCitizen(recipient)
                || first.equals(second) || exposure == null)
            throw new IllegalArgumentException("Invalid report decision request");
        long tick=level.getGameTime();
        // Do not even ask for recipient report NBT in the withheld condition.
        if (exposure == ReportConditionedChoice.Exposure.WITHHELD)
            return new Choice(ReportChoiceMlp.Action.ABSTAIN, null,
                "NOT_LOADED_WITHHELD", 0, tick, "REPORT_EXPOSURE_WITHHELD", "NONE");
        double[] features=new double[ReportChoiceMlp.INPUT];
        String[] ids={"NONE","NONE"};
        int admissible=0;
        List<BlockPos> candidates=List.of(first,second);
        for (int i=0;i<2;i++) {
            // Exactly the same recipient-only accessor as the v0.16.1
            // scripted baseline. This method NEVER consults source chests.
            var report=CitizenKnowledgeExchange.decisionReport(level,candidates.get(i),recipient);
            if (report==null) continue;
            long age=tick-report.getLong("delivered_tick");
            long observedAge=tick-report.getLong("observed_tick");
            ReportChoiceMlp.encode(features,i,report.getInt("wheat"),age,
                observedAge,report.getInt("source_revision"),true);
            String reportId=report.getString("id");
            if (reportId.isBlank())
                throw new IllegalArgumentException("Direct-origin delivered report lacks identity");
            ids[i]=reportId;
            admissible++;
        }
        ReportChoiceMlp frozen=model();
        ReportChoiceMlp.Action action=frozen.choose(features);
        BlockPos selected=action==ReportChoiceMlp.Action.SOURCE_A ? first
            : action==ReportChoiceMlp.Action.SOURCE_B ? second : null;
        int selectedIdx=action==ReportChoiceMlp.Action.SOURCE_A ? 0 : 1;
        return new Choice(action,selected,frozen.sha256(),admissible,tick,
            action==ReportChoiceMlp.Action.ABSTAIN ? "MODEL_ABSTAIN_OR_NO_REPORT"
                : "FROZEN_SIMULATED_OUTCOME_REGRESSION",
            selected==null ? "NONE" : ids[selectedIdx]);
    }

    public static String inspect(ServerLevel level, Villager recipient, BlockPos first,
                                 BlockPos second, ReportConditionedChoice.Exposure exposure) {
        Choice choice;
        try {
            choice=evaluate(level,recipient,first,second,exposure);
        } catch (IllegalArgumentException invalid) {
            return denied("INVALID_REQUEST_OR_REPORT");
        } catch (Exception failure) {
            return denied("FROZEN_MODEL_OR_REPORT_VALIDATION_FAILED");
        }
        return "REPORT_MLP_CHOICE schema=hearthbound.report-mlp-choice.v1"
            + " status=" + (choice.selected()==null ? "ABSTAIN" : "CHOOSE")
            + " reason=" + choice.reason()
            + " recipient=" + recipient.getUUID()
            + " world=" + HearthboundWorldIdentity.get(level)
            + " tick=" + choice.tick()
            + " exposure=" + exposure
            + " policy=SIMULATOR_TRAINED_FROZEN_MLP"
            + " model_sha256=" + choice.modelSha256()
            + " candidate_sources=" + ReportChoiceCommands.key(level,first)
                + ";" + ReportChoiceCommands.key(level,second)
            + " selected=" + (choice.selected()==null ? "NONE"
                : ReportChoiceCommands.key(level,choice.selected()))
            + " admissible_reports=" + choice.reports()
            + " evidence_origin=RECIPIENT_DELIVERED_REPORT_ONLY"
            + " inventory_read=false sensor_triggered=false"
            + " task_authorized=false reward_authorized=false"
            + " learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
