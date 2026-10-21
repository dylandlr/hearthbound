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

    public static void afterAssigned(ServerLevel level, Villager citizen) {
        UUID job = SableHauling.jobId(citizen);
        var trace = ResearchDecisionRuntime.latestProposal(citizen.getUUID().toString(), level.getGameTime());
        if (job == null || trace == null) return;
        PendingLearningBindingsSavedData.get(level).add(
                new VerifiedTrainingTransitions.Binding(job, citizen.getUUID(), trace));
    }

    public static void afterVerifiedAward(ServerLevel level, MillResearchRewards.Award award) {
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
