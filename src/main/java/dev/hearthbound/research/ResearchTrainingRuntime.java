package dev.hearthbound.research;

import dev.hearthbound.learning.VerifiedTrainingTransitions;
import dev.hearthbound.world.SableHauling;
import java.util.UUID;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Optional diagnostics; errors cannot revoke a successfully assigned job or earned reward. */
public final class ResearchTrainingRuntime {
    private static final VerifiedTrainingTransitions TRANSITIONS = new VerifiedTrainingTransitions();
    private ResearchTrainingRuntime() {}

    public static void afterAssigned(ServerLevel level, Villager citizen) {
        UUID job = SableHauling.jobId(citizen);
        var trace = ResearchDecisionRuntime.latestProposal(citizen.getUUID().toString(), level.getGameTime());
        if (job == null || trace == null) return;
        TRANSITIONS.bind(new VerifiedTrainingTransitions.Binding(job, citizen.getUUID(), trace));
    }

    public static void afterVerifiedAward(MillResearchRewards.Award award) {
        // Fail-closed on missing or mismatched decision bindings; no synthetic transitions.
        TRANSITIONS.finalizeVerified(award);
    }

    public static int completedCount() { return TRANSITIONS.snapshot().size(); }
    public static int pendingCount() { return TRANSITIONS.pendingCount(); }
}
