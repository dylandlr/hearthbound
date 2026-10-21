package dev.hearthbound.research;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Server-side, read-only decision telemetry. Never issues a research action.
 * Trace samples reflect actual loaded local observations, not simulated evidence.
 */
public final class ResearchDecisionRuntime {
    private static final ResearchDecisionTraceJournal JOURNAL = new ResearchDecisionTraceJournal(256);
    private ResearchDecisionRuntime() {}

    public static boolean capture(ServerLevel level, Villager citizen, BlockPos source, BlockPos machine) {
        var observation = LocalMillExperimentSensor.observe(level, citizen, source, machine);
        if (observation == null) return false;
        JOURNAL.record(citizen.getUUID().toString(), level.getGameTime(),
                ResearchDecisionComparison.evaluate(observation));
        return true;
    }

    /** Read-only server export; caller must enforce permissions. */
    public static String exportJson() {
        return JOURNAL.exportJson();
    }

    public static ResearchDecisionTraceJournal.Trace latestProposal(String citizenId, long tick) {
        var entries = JOURNAL.snapshot(citizenId);
        if (entries.isEmpty()) return null;
        var item = entries.get(entries.size() - 1);
        return item.gameTick() == tick && "PROPOSE".equals(item.personality().action()) ? item : null;
    }

    public static int count(String citizenId) {
        return JOURNAL.snapshot(citizenId).size();
    }
}
