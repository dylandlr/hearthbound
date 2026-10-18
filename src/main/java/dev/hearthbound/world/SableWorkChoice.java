package dev.hearthbound.world;

import dev.hearthbound.ai.ColonyPolicy;
import dev.hearthbound.ai.StochasticPriorityPolicy;
import dev.hearthbound.ai.WorkChoicePlanner;
import dev.hearthbound.ai.WorkOfferLifecycle;
import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryPolicyBridge;
import dev.hearthbound.research.LibraryStudyRuntime;
import dev.hearthbound.research.CitizenTechnologyKnowledge;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Explicit, operator-specified two-job experiment. The server does not invent
 * haul endpoints, and the chosen physical executor remains authoritative.
 */
public final class SableWorkChoice {
    private static final String KEY = "hearthbound.haulPriorityV1";
    private static final String TRACE = "hearthbound.lastWorkChoiceV1";
    private SableWorkChoice() {}

    public static void haulPriority(Villager citizen, int priority) {
        if (priority < 0 || priority > 4) throw new IllegalArgumentException("Priority must be 0..4");
        citizen.getPersistentData().putInt(KEY, priority);
    }
    public static int haulPriority(Villager citizen) {
        return citizen.getPersistentData().contains(KEY)
                ? citizen.getPersistentData().getInt(KEY) : 2;
    }

    public static String consider(ServerLevel level, Villager citizen, BlockPos source,
                                  BlockPos destination, BlockPos library) {
        return consider(level, citizen, source, destination, library, true);
    }

    /** Set allowHaul=false after the configured autonomous haul has been issued. */
    public static String consider(ServerLevel level, Villager citizen, BlockPos source,
                                  BlockPos destination, BlockPos library, boolean allowHaul) {
        if (citizen.level() != level) throw new IllegalArgumentException("Wrong dimension");
        if (SableHauling.active(citizen) || AutonomousLibraryStudy.active(citizen)
                || LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING)
            throw new IllegalStateException("Citizen already working");
        int haul = haulPriority(citizen);
        int study = LibraryPolicyBridge.studyPriority(citizen);
        // Loaded endpoints and a valid lesson are minimum evidence of offers.
        // The hauling executor rechecks claims, reservations and inventory.
        boolean canHaul = WorkOfferLifecycle.offerHaul(true, !allowHaul, haul)
                && source != null && !source.equals(destination)
                && level.hasChunkAt(source) && level.hasChunkAt(destination)
                && SableHauling.hasAvailableWheat(level, source);
        boolean canStudy = WorkOfferLifecycle.offerStudy(
                library != null && level.hasChunkAt(library) && LibraryStudyRuntime.hasBook(level, library),
                CitizenTechnologyKnowledge.knows(citizen, LibraryStudyRuntime.RECIPE), study)
                && library != null && citizen.distanceToSqr(library.getX() + .5, library.getY() + .5,
                        library.getZ() + .5) <= 64 * 64;
        var observation = WorkChoicePlanner.observation(citizen.getUUID(), level.getGameTime(),
                0, 0, 0, List.of(
                    new WorkChoicePlanner.Offer("haul", ColonyPolicy.Kind.HAUL, 40, canHaul),
                    new WorkChoicePlanner.Offer("study", ColonyPolicy.Kind.STUDY, 40, canStudy)));
        var policy = new StochasticPriorityPolicy(
                new StochasticPriorityPolicy.Profile(
                        Map.of(ColonyPolicy.Kind.HAUL, haul,
                                ColonyPolicy.Kind.STUDY, study), .5, .5, 0),
                citizen.getUUID().getLeastSignificantBits(), 0);
        var choice = WorkChoicePlanner.choose(observation, policy);
        String outcome = "NO_EXECUTABLE_WORK";
        try {
            if ("haul".equals(choice.actionId())) {
                SableHauling.assign(level, citizen, source, destination);
                outcome = "HAUL_ASSIGNED";
            } else if ("study".equals(choice.actionId())
                    && LibraryPolicyBridge.consider(level, citizen, library)) {
                outcome = "STUDY_ASSIGNED";
            }
        } catch (IllegalArgumentException | IllegalStateException ex) {
            outcome = "DECLINED_" + choice.actionId() + ": " + ex.getMessage();
        }
        CompoundTag trace = new CompoundTag();
        trace.putLong("tick", level.getGameTime());
        trace.putString("choice", choice.actionId());
        trace.putString("outcome", outcome);
        trace.putBoolean("haulAvailable", canHaul);
        trace.putBoolean("studyAvailable", canStudy);
        trace.putInt("haulPriority", haul);
        trace.putInt("studyPriority", study);
        citizen.getPersistentData().put(TRACE, trace);
        return outcome;
    }

    public static String inspect(Villager citizen) {
        CompoundTag trace = citizen.getPersistentData().getCompound(TRACE);
        return "WORK_CHOICE tick=" + trace.getLong("tick")
                + " choice=" + trace.getString("choice")
                + " outcome=" + trace.getString("outcome")
                + " haulPriority=" + haulPriority(citizen)
                + " studyPriority=" + LibraryPolicyBridge.studyPriority(citizen);
    }
}
