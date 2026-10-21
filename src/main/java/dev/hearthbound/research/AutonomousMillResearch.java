package dev.hearthbound.research;

import dev.hearthbound.world.SableHauling;
import dev.hearthbound.world.SableAutoWork;
import dev.hearthbound.world.CitizenWorkOwnership;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Opt-in research task hierarchy:
 * SURVEY -> PROPOSE -> CLAIM_AND_HAUL -> trusted Create processing receipt.
 * Never bypasses the hauling executor or machine reservations.
 */
public final class AutonomousMillResearch {
    private static final String ENABLED = "hearthbound.autoResearchV1";
    private static final String LAST = "hearthbound.autoResearchLastV1";
    private AutonomousMillResearch() {}

    public static void enable(Villager citizen, boolean on) {
        citizen.getPersistentData().putBoolean(ENABLED,on);
    }
    public static void tick(ServerLevel level, Villager citizen) {
        CompoundTag root=citizen.getPersistentData();
        if (!root.getBoolean(ENABLED) || SableAutoWork.enabled(citizen)) return;
        try { CitizenWorkOwnership.assertFree(citizen); }
        catch (IllegalStateException occupied) { return; }
        long now=level.getGameTime();
        if (now - root.getLong(LAST) < 200) return;
        root.putLong(LAST,now);
        String agent=citizen.getUUID().toString();
        var store=TechnologyHypothesisSavedData.get(level);
        if (store.has(agent,"create:milling/wheat")) return;
        var site=LocalExperimentDiscovery.nearest(level,citizen);
        if (site==null) return;
        // Sample exactly at a real decision boundary. Diagnostics do not assign work.
        var observation = LocalMillExperimentSensor.observe(level,citizen,
                site.wheatSource(),site.millstone());
        if (observation == null) return;
        ResearchDecisionRuntime.captureObservation(level, citizen, observation);
        var decision = ResearchPolicyBaselines.choose(
                ResearchPolicyBaselines.Mode.PERSONALITY, observation).choice();
        if (decision.action()!=ExperimentSelectionPolicy.Action.PROPOSE) return;
        // Reserve and create the physical haul first. No hypothesis if the
        // physical job cannot be admitted.
        try {
            SableHauling.assign(level,citizen,site.wheatSource(),site.millstone());
            try { ResearchTrainingRuntime.afterAssigned(level, citizen, observation); }
            catch (RuntimeException diagnosticFailure) {
                org.apache.logging.log4j.LogManager.getLogger("HearthboundLearning")
                    .warn("Optional training decision binding failed for {}", agent, diagnosticFailure);
            }
            CitizenWorkOwnership.assigned(citizen, CitizenWorkOwnership.Kind.HAUL);
            var c=decision.candidate();
            store.propose(agent,c.recipeId(),c.inputItem(),c.machine(),c.predictedOutput());
        } catch (IllegalArgumentException | IllegalStateException ignored) {
            // Another citizen may hold a reservation; retry after the cooldown.
        }
    }
}
