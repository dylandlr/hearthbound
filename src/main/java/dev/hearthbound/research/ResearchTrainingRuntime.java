package dev.hearthbound.research;

import dev.hearthbound.learning.PendingLearningBindingsSavedData;
import dev.hearthbound.learning.VerifiedRewardReplaySavedData;
import dev.hearthbound.learning.VerifiedTrainingTransitions;
import dev.hearthbound.world.SableHauling;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Persistent provenance; no rewards issued by the diagnostic layer. */
public final class ResearchTrainingRuntime {
    private ResearchTrainingRuntime() {}

    public static void afterAssigned(ServerLevel level, Villager citizen,
                                     ExperimentSelectionPolicy.Observation observation) {
        UUID job = SableHauling.jobId(citizen);
        var trace = ResearchDecisionRuntime.latestProposal(citizen.getUUID().toString(), level.getGameTime());
        if (job == null || trace == null || observation == null) return;
        var vector = dev.hearthbound.learning.ResearchObservationVector.from(observation);
        dev.hearthbound.learning.ResearchObservationSnapshotsSavedData.get(level).add(
                new dev.hearthbound.learning.ResearchObservationSnapshotsSavedData.Snapshot(
                        job, citizen.getUUID(), level.getGameTime(), vector.values()));
        PendingLearningBindingsSavedData.get(level).add(
                new VerifiedTrainingTransitions.Binding(job, citizen.getUUID(), trace));
    }

    public static void afterVerifiedAward(ServerLevel level, Villager citizen,
                                          net.minecraft.core.BlockPos machine,
                                          MillResearchRewards.Award award) {
        if (!citizen.getUUID().equals(award.citizen())
                || machine.asLong() != award.machine())
            throw new IllegalArgumentException("successor identity does not match verified award");
        // The same sensor is used after the outcome. Ineligible/unknown context is
        // explicitly UNAVAILABLE, never imputed as an all-zero successor state.
        var site = LocalExperimentDiscovery.nearest(level, citizen);
        ExperimentSelectionPolicy.Observation successor = site == null ? null
            : LocalMillExperimentSensor.observe(level, citizen, site.wheatSource(), site.millstone());
        var state = successor == null
            ? new dev.hearthbound.learning.ResearchSuccessorObservationsSavedData.Successor(
                award.job(), award.citizen(), level.getGameTime(),
                dev.hearthbound.learning.ResearchSuccessorObservationsSavedData.Status.UNAVAILABLE, null)
            : new dev.hearthbound.learning.ResearchSuccessorObservationsSavedData.Successor(
                award.job(), award.citizen(), level.getGameTime(),
                dev.hearthbound.learning.ResearchSuccessorObservationsSavedData.Status.OBSERVED,
                dev.hearthbound.learning.ResearchObservationVector.from(successor).values());
        dev.hearthbound.learning.ResearchSuccessorObservationsSavedData.get(level).record(state);
        var replay = VerifiedRewardReplaySavedData.get(level);
        if (replay.snapshot().containsKey(award.job())) {
            PendingLearningBindingsSavedData.get(level).complete(award.job());
            return;
        }
        var binding = PendingLearningBindingsSavedData.get(level).require(award.job());
        var assembler = new VerifiedTrainingTransitions();
        assembler.bind(binding);
        var completed = assembler.finalizeVerified(award);
        replay.append(completed);
        PendingLearningBindingsSavedData.get(level).complete(award.job());
    }

    public static int completedCount(ServerLevel level) {
        return VerifiedRewardReplaySavedData.get(level).snapshot().size();
    }
    public static int pendingCount(ServerLevel level) {
        return PendingLearningBindingsSavedData.get(level).size();
    }
}
