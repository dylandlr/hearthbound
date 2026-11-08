package dev.hearthbound.world;

import dev.hearthbound.evidence.ReportChoiceMlp;
import dev.hearthbound.evidence.ReportConditionedChoice;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Reuses the v0.16.2 recipient report boundary for matched physical trials.
 * Neither policy gets the world's hidden inventory or other citizens' memory.
 */
public final class ReportPolicyTrialChoice {
    public enum Policy { FROZEN_MLP, SCRIPTED }
    public static final String SCRIPTED_MODEL = "SCRIPTED_NO_MODEL";
    private ReportPolicyTrialChoice() {}

    public static ReportChoiceMlpCommands.Choice evaluate(
            ServerLevel level, Villager executor, BlockPos a, BlockPos b,
            ReportConditionedChoice.Exposure exposure, Policy policy) throws Exception {
        if (policy == null) throw new IllegalArgumentException("Missing policy");
        if (policy == Policy.FROZEN_MLP)
            return ReportChoiceMlpCommands.evaluate(level, executor, a, b, exposure);

        if (level == null || executor == null || a == null || b == null ||
                exposure == null || a.equals(b) ||
                executor.level() != level || !CitizenSourceKnowledge.isCitizen(executor))
            throw new IllegalArgumentException("Wrong scripted evaluation request");
        final long now = level.getGameTime();
        // Preserve the v0.16.1 control: the WITHHELD arm must never look
        // at recipient reports, even when they are present in persistent NBT.
        if (exposure == ReportConditionedChoice.Exposure.WITHHELD)
            return new ReportChoiceMlpCommands.Choice(ReportChoiceMlp.Action.ABSTAIN,
                null, SCRIPTED_MODEL, 0, now, "REPORT_EXPOSURE_WITHHELD", "NONE");

        List<String> menu = List.of(
            ReportChoiceCommands.key(level, a), ReportChoiceCommands.key(level, b));
        List<ReportConditionedChoice.Report> reports = new ArrayList<>();
        Map<String, String> ids = new HashMap<>();
        for (BlockPos candidate : List.of(a, b)) {
            CompoundTag snapshot = CitizenKnowledgeExchange.decisionReport(
                level, candidate, executor);
            if (snapshot == null) continue;
            String id = snapshot.getString("id");
            if (id.isBlank())
                throw new IllegalArgumentException("Delivered report without a bound identity");
            ReportConditionedChoice.Report decoded =
                ReportChoiceCommands.report(level, executor, candidate);
            if (decoded == null)
                throw new IllegalArgumentException("Report revision changed mid-evaluation");
            reports.add(decoded);
            ids.put(decoded.source(), id);
        }
        ReportConditionedChoice.Decision choice =
            ReportConditionedChoice.choose(executor.getUUID(), menu, reports, exposure, now);
        if (choice.status() == ReportConditionedChoice.Status.ABSTAIN)
            return new ReportChoiceMlpCommands.Choice(ReportChoiceMlp.Action.ABSTAIN,
                null, SCRIPTED_MODEL, choice.admissibleReports(), now, choice.reason(), "NONE");
        int index = menu.indexOf(choice.source());
        if (index < 0 || !ids.containsKey(choice.source()))
            throw new IllegalArgumentException("Chosen report was not bound to candidate menu");
        return new ReportChoiceMlpCommands.Choice(
            index == 0 ? ReportChoiceMlp.Action.SOURCE_A : ReportChoiceMlp.Action.SOURCE_B,
            index == 0 ? a : b, SCRIPTED_MODEL,
            choice.admissibleReports(), now, choice.reason(), ids.get(choice.source()));
    }
}
