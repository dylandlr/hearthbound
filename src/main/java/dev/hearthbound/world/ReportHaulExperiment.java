package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import dev.hearthbound.evidence.ReportConditionedChoice;
import java.util.Locale;
import java.util.UUID;
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
 * Permission-2 experimental one-shot bridge from a FROZEN report-conditioned
 * MLP choice to the existing physical Minecraft hauling motor.
 *
 * This is OPERATOR-TRIGGERED, NOT autonomous learned planning. The selected
 * source comes only from the recipient's PRE-ACTION delivered reports. The
 * existing SableHauling executor performs all real source/destination work.
 * No action from this bridge is eligible for research or model rewards.
 */
@Mod.EventBusSubscriber(modid="hearthbound",bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class ReportHaulExperiment {
    private static final String HAUL="hearthbound.haul";
    private static final String RECEIPT="reportPolicyDispatch.v1";
    private ReportHaulExperiment() {}

    private static String denied(String reason) {
        return "REPORT_HAUL_DISPATCH status=DENIED reason="+reason
            +" inventory_read=false reward_authorized=false learning_authorized=false"
            +" NO_RESEARCH_CREDIT";
    }

    public static String dispatch(ServerLevel level, Villager executor, Villager recipient,
                                  BlockPos first, BlockPos second, BlockPos destination,
                                  ReportConditionedChoice.Exposure exposure) {
        return dispatchTrial(level, executor, recipient, first, second, destination,
            exposure, ReportPolicyTrialChoice.Policy.FROZEN_MLP);
    }

    public static String dispatchTrial(ServerLevel level, Villager executor, Villager recipient,
                                  BlockPos first, BlockPos second, BlockPos destination,
                                  ReportConditionedChoice.Exposure exposure,
                                  ReportPolicyTrialChoice.Policy policy) {
        if (policy == null) return denied("MISSING_TRIAL_POLICY");
        String policyName = policy == ReportPolicyTrialChoice.Policy.FROZEN_MLP
            ? "SIMULATOR_TRAINED_FROZEN_MLP" : "SCRIPTED_REPORT_RANK_V1";
        String policyOrigin = policy == ReportPolicyTrialChoice.Policy.FROZEN_MLP
            ? "OPERATOR_TRIGGERED_FROZEN_POLICY" : "OPERATOR_TRIGGERED_SCRIPTED_POLICY";
        if(level==null || executor==null || recipient==null || first==null || second==null
                || destination==null || exposure==null || first.equals(second)
                || destination.equals(first) || destination.equals(second)
                || executor.level()!=level || recipient.level()!=level
                || !executor.getUUID().equals(recipient.getUUID())
                || !executor.getPersistentData().getBoolean("hearthbound.sable")
                || !CitizenSourceKnowledge.isCitizen(recipient))
            return denied("INVALID_ACTOR_OR_CANDIDATE");
        if (SableHauling.active(executor)) return denied("EXECUTOR_HAS_ACTIVE_HAUL");

        // Make one typed decision, without consulting current source inventory.
        // All following Minecraft source checks are task-execution safeguards,
        // not added observation features or model inputs.
        final ReportChoiceMlpCommands.Choice decision;
        try {
            decision=ReportPolicyTrialChoice.evaluate(level,recipient,first,second,exposure,policy);
        } catch (Exception invalid) {
            return denied("MODEL_OR_REPORT_EVIDENCE_INVALID");
        }
        if (decision.selected()==null)
            return "REPORT_HAUL_DISPATCH status=ABSTAIN job=NONE"
                +" reason="+decision.reason()
                +" policy="+policyName
                +" decision_origin="+policyOrigin
                +" exposure="+exposure
                +" model_sha256="+decision.modelSha256()
                +" executor="+executor.getUUID()
                +" recipient="+recipient.getUUID()
                +" inventory_read=false task_assigned=false"
                +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";

        BlockPos selected=decision.selected();
        if (!selected.equals(first) && !selected.equals(second))
            return denied("SELECTED_SOURCE_NOT_BOUND_TO_MENU");
        if (decision.reportId() == null || decision.reportId().isBlank()
                || "NONE".equals(decision.reportId()))
            return denied("CHOSEN_SOURCE_HAS_NO_PRE_ACTION_REPORT");
        if (!level.hasChunkAt(selected) || !level.hasChunkAt(destination))
            return denied("SOURCE_OR_DESTINATION_CHUNK_NOT_LOADED");

        // SableHauling is the only source-claim and inventory-moving path.
        // No operator or model code manually transfers an item.
        try {
            SableHauling.assign(level,executor,selected,destination);
        } catch (IllegalArgumentException | IllegalStateException invalid) {
            return denied("PHYSICAL_HAUL_ASSIGNMENT_REJECTED");
        }

        CompoundTag haul=executor.getPersistentData().getCompound(HAUL);
        if (!haul.hasUUID("jobId") || !haul.contains("assignedTick")
                || !haul.contains("source") || !haul.contains("destination")
                || haul.getLong("source")!=selected.asLong()
                || haul.getLong("destination")!=destination.asLong()) {
            // Do not claim safe abort: the existing physical job might exist.
            return "REPORT_HAUL_DISPATCH status=POST_ASSIGNMENT_AUDIT_REQUIRED"
                +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        }
        UUID job=haul.getUUID("jobId");
        long assigned=haul.getLong("assignedTick");
        if (decision.tick()>assigned)
            return "REPORT_HAUL_DISPATCH status=POST_ASSIGNMENT_AUDIT_REQUIRED"
                +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        CompoundTag snapshot=new CompoundTag();
        snapshot.putString("schema","hearthbound.report-policy-physical-assignment.v1");
        snapshot.putUUID("world",HearthboundWorldIdentity.get(level));
        snapshot.putUUID("job",job);
        snapshot.putUUID("executor",executor.getUUID());
        snapshot.putUUID("recipient",recipient.getUUID());
        snapshot.putLong("source",selected.asLong());
        snapshot.putLong("sourceA",first.asLong());
        snapshot.putLong("sourceB",second.asLong());
        snapshot.putLong("destination",destination.asLong());
        snapshot.putLong("decisionTick",decision.tick());
        snapshot.putLong("assignedTick",assigned);
        snapshot.putString("reportId",decision.reportId());
        snapshot.putString("modelSha256",decision.modelSha256());
        snapshot.putString("policy",policyName);
        snapshot.putString("origin",policyOrigin);
        snapshot.putString("exposure",exposure.name());
        haul.put(RECEIPT,snapshot);
        executor.getPersistentData().put(HAUL,haul);
        return "REPORT_HAUL_DISPATCH status=ASSIGNED"
            +" job="+job
            +" executor="+executor.getUUID()
            +" recipient="+recipient.getUUID()
            +" source="+ReportChoiceCommands.key(level,selected)
            +" destination="+ReportChoiceCommands.key(level,destination)
            +" candidates="+ReportChoiceCommands.key(level,first)
                +";"+ReportChoiceCommands.key(level,second)
            +" decision_tick="+decision.tick()
            +" assigned_tick="+assigned
            +" source_report_id="+decision.reportId()
            +" model_sha256="+decision.modelSha256()
            +" policy="+policyName
            +" decision_origin="+policyOrigin
            +" exposure="+exposure
            +" inventory_read=false task_assigned=true"
            +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
    }

    /**
     * Read only the executor's real completed hauling job and its pre-task
     * neural-choice receipt. The operator acceptance fixture separately
     * checks physical chest deltas using direct RCON inventory reads.
     *
     * Completed haul is not proof of Create process, teaching, or science.
     */
    public static String inspect(ServerLevel level, Villager executor, UUID job) {
        String base="REPORT_HAUL_EXECUTION job="+job
            +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        if(level==null || executor==null || job==null || executor.level()!=level
                || !executor.getPersistentData().getBoolean("hearthbound.sable"))
            return base+" status=DENIED reason=INVALID_EXECUTOR";
        CompoundTag haul=executor.getPersistentData().getCompound(HAUL);
        if (!haul.hasUUID("jobId") || !job.equals(haul.getUUID("jobId"))
                || !haul.contains(RECEIPT))
            return base+" status=DENIED reason=NO_MATCHING_NEURAL_TASK";
        CompoundTag event=haul.getCompound(RECEIPT);
        if(!"hearthbound.report-policy-physical-assignment.v1".equals(event.getString("schema"))
                || !event.hasUUID("world")
                || !HearthboundWorldIdentity.get(level).equals(event.getUUID("world"))
                || !event.hasUUID("job") || !job.equals(event.getUUID("job"))
                || !event.hasUUID("executor")
                || !executor.getUUID().equals(event.getUUID("executor"))
                || !event.hasUUID("recipient")
                || !executor.getUUID().equals(event.getUUID("recipient"))
                || !("SIMULATOR_TRAINED_FROZEN_MLP".equals(event.getString("policy"))
                    && "OPERATOR_TRIGGERED_FROZEN_POLICY".equals(event.getString("origin"))
                    && event.getString("modelSha256").matches("[a-f0-9]{64}")
                    || "SCRIPTED_REPORT_RANK_V1".equals(event.getString("policy"))
                    && "OPERATOR_TRIGGERED_SCRIPTED_POLICY".equals(event.getString("origin"))
                    && ReportPolicyTrialChoice.SCRIPTED_MODEL.equals(event.getString("modelSha256")))
                || !"EXPOSED".equals(event.getString("exposure"))
                || event.getString("reportId").isBlank()
                || !event.contains("source") || !event.contains("destination")
                || !event.contains("sourceA") || !event.contains("sourceB")
                || !event.contains("decisionTick") || !event.contains("assignedTick")
                || (event.getLong("source")!=event.getLong("sourceA")
                    && event.getLong("source")!=event.getLong("sourceB"))
                || event.getLong("source")==event.getLong("destination")
                || event.getLong("decisionTick")<0
                || event.getLong("decisionTick")>event.getLong("assignedTick")
                || haul.getLong("source")!=event.getLong("source")
                || haul.getLong("destination")!=event.getLong("destination")
                || haul.getLong("assignedTick")!=event.getLong("assignedTick"))
            return base+" status=DENIED reason=INVALID_PRE_ACTION_NEURAL_PROVENANCE";

        BlockPos dest=BlockPos.of(event.getLong("destination"));
        if (SableHauling.completedJob(executor,job,dest)) {
            try {
                SableHauling.Assignment a=
                    SableHauling.completedAssignment(level,executor,job,dest);
                if (a.source()!=event.getLong("source")
                        || a.assignedTick()!=event.getLong("assignedTick"))
                    return base+" status=DENIED reason=EXECUTOR_SOURCE_OR_TIME_MISMATCH";
                return base+" status=EXECUTOR_COMPLETED"
                    +" source="+ReportChoiceCommands.key(level,BlockPos.of(a.source()))
                    +" destination="+ReportChoiceCommands.key(level,dest)
                    +" model_sha256="+event.getString("modelSha256")
                    +" decision_tick="+event.getLong("decisionTick")
                    +" assigned_tick="+a.assignedTick()
                    +" source_report_id="+event.getString("reportId")
                    +" policy="+event.getString("policy")
                    +" decision_origin="+event.getString("origin")
                    +" inventory_delta_verified=false"
                    +" physical_completion_receipt=EXECUTOR_NBT"
                    +" research_authorized=false";
            } catch (IllegalArgumentException | IllegalStateException ex) {
                return base+" status=DENIED reason=COMPLETION_PROOF_INVALID";
            }
        }
        return base+" status=INCOMPLETE"
            +" executor_state="+SableHauling.status(executor).replace(' ','_')
            +" inventory_delta_verified=false";
    }

    @SubscribeEvent
    public static void registerCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher=event.getDispatcher();
        dispatcher.register(Commands.literal("hearthbound-report-dispatch")
            .requires(s->s.hasPermission(2))
            .then(Commands.argument("executor",EntityArgument.entity())
                .then(Commands.argument("first",BlockPosArgument.blockPos())
                        .then(Commands.argument("second",BlockPosArgument.blockPos())
                            .then(Commands.argument("destination",BlockPosArgument.blockPos())
                                .then(Commands.argument("exposure",StringArgumentType.word())
                                    .executes(ctx->{
                                        var source=ctx.getSource();
                                        var ex=EntityArgument.getEntity(ctx,"executor");
                                        if (!(ex instanceof Villager executor)) {
                                            source.sendFailure(Component.literal("Executor must be a real villager"));
                                            return 0;
                                        }
                                        ReportConditionedChoice.Exposure exposure;
                                        try {
                                            exposure=ReportConditionedChoice.Exposure.valueOf(
                                                StringArgumentType.getString(ctx,"exposure")
                                                    .toUpperCase(Locale.ROOT));
                                        } catch (IllegalArgumentException e) {
                                            source.sendFailure(Component.literal("Exposure must be EXPOSED or WITHHELD"));
                                            return 0;
                                        }
                                        String result=dispatch(source.getLevel(),executor,executor,
                                            BlockPosArgument.getBlockPos(ctx,"first"),
                                            BlockPosArgument.getBlockPos(ctx,"second"),
                                            BlockPosArgument.getBlockPos(ctx,"destination"),exposure);
                                        source.sendSuccess(()->Component.literal(result),false);
                                        return result.contains("status=DENIED")?0:1;
                                    })))))));
        dispatcher.register(Commands.literal("hearthbound-report-dispatch-trial")
            .requires(source->source.hasPermission(2))
            .then(Commands.argument("executor",EntityArgument.entity())
                .then(Commands.argument("first",BlockPosArgument.blockPos())
                    .then(Commands.argument("second",BlockPosArgument.blockPos())
                        .then(Commands.argument("destination",BlockPosArgument.blockPos())
                            .then(Commands.argument("policy",StringArgumentType.word())
                                .then(Commands.argument("exposure",StringArgumentType.word())
                                    .executes(ctx->{
                                        var source=ctx.getSource();
                                        var candidate=EntityArgument.getEntity(ctx,"executor");
                                        if(!(candidate instanceof Villager executor)) {
                                            source.sendFailure(Component.literal("Executor must be a real villager"));
                                            return 0;
                                        }
                                        ReportPolicyTrialChoice.Policy policy;
                                        ReportConditionedChoice.Exposure exposure;
                                        try {
                                            policy=ReportPolicyTrialChoice.Policy.valueOf(
                                                StringArgumentType.getString(ctx,"policy")
                                                    .toUpperCase(Locale.ROOT));
                                            exposure=ReportConditionedChoice.Exposure.valueOf(
                                                StringArgumentType.getString(ctx,"exposure")
                                                    .toUpperCase(Locale.ROOT));
                                        } catch (IllegalArgumentException invalid) {
                                            source.sendFailure(Component.literal(
                                                "Policy must be SCRIPTED or FROZEN_MLP, exposure EXPOSED or WITHHELD"));
                                            return 0;
                                        }
                                        String result=dispatchTrial(source.getLevel(),executor,executor,
                                            BlockPosArgument.getBlockPos(ctx,"first"),
                                            BlockPosArgument.getBlockPos(ctx,"second"),
                                            BlockPosArgument.getBlockPos(ctx,"destination"),exposure,policy);
                                        source.sendSuccess(()->Component.literal(result),false);
                                        return result.contains("status=DENIED") ? 0 : 1;
                                    }))))))));
        dispatcher.register(Commands.literal("hearthbound-report-execution")
            .requires(s->s.hasPermission(2))
            .then(Commands.argument("executor",EntityArgument.entity())
                .then(Commands.argument("jobId",StringArgumentType.word())
                    .executes(ctx->{
                        var entity=EntityArgument.getEntity(ctx,"executor");
                        if(!(entity instanceof Villager citizen)) {
                            ctx.getSource().sendFailure(Component.literal("Executor must be a villager"));
                            return 0;
                        }
                        try {
                            UUID job=UUID.fromString(StringArgumentType.getString(ctx,"jobId"));
                            String result=inspect(ctx.getSource().getLevel(),citizen,job);
                            ctx.getSource().sendSuccess(()->Component.literal(result),false);
                            return 1;
                        } catch (IllegalArgumentException invalid) {
                            ctx.getSource().sendFailure(Component.literal("Invalid job UUID"));
                            return 0;
                        }
                    }))));
    }
}
