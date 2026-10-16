package dev.hearthbound.research;

import dev.hearthbound.ai.ActionGate;
import dev.hearthbound.ai.ColonyPolicy;
import dev.hearthbound.ai.StochasticPriorityPolicy;
import dev.hearthbound.world.SableHauling;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Minecraft-side adapter for one genuine STUDY decision.
 * Only server-derived, executable choices are exposed to ColonyPolicy;
 * the proposal is revalidated with ActionGate before assignment.
 *
 * This is an explicit dispatch hook, NOT an autonomous per-tick scheduler.
 */
public final class LibraryPolicyBridge {
    private static final String KEY = "hearthbound.studyPreferenceV1";
    private LibraryPolicyBridge() {}

    /** 0 disables study; 1-4 express highest to lowest work priority. */
    public static void setStudyPriority(Villager citizen, int priority) {
        if (priority < 0 || priority > 4) throw new IllegalArgumentException("Priority must be 0..4");
        CompoundTag config = citizen.getPersistentData().getCompound(KEY);
        config.putInt("priority", priority);
        citizen.getPersistentData().put(KEY, config);
    }
    public static int studyPriority(Villager citizen) {
        CompoundTag config = citizen.getPersistentData().getCompound(KEY);
        return config.contains("priority") ? config.getInt("priority") : 2;
    }

    public static boolean consider(ServerLevel level, Villager citizen, BlockPos shelf) {
        int priority = studyPriority(citizen);
        // Deliberately refrain from claiming book authenticity: runtime currently
        // uses a placeholder written-book source.
        boolean executable = priority > 0 && citizen.level() == level
                && level.hasChunkAt(shelf)
                && !SableHauling.active(citizen)
                && !"TRAVELING".equals(citizen.getPersistentData()
                    .getCompound("hearthbound.autonomousLibraryV1").getString("state"))
                && LibraryStudyRuntime.state(citizen) != LibraryStudyRuntime.State.STUDYING;
        // The only submitted option is a real STUDY job. Alternative work options
        // belong to the future unified colony job scheduler.
        long version = level.getGameTime();
        ColonyPolicy.Observation observation = new ColonyPolicy.Observation(
                version, citizen.getUUID().toString(), 0, 0, 0,
                List.of(new ColonyPolicy.Action("study:" + shelf.asLong(),
                        ColonyPolicy.Kind.STUDY, 0, executable)));
        var profile = new StochasticPriorityPolicy.Profile(
                Map.of(ColonyPolicy.Kind.STUDY, priority), 0.5, 0.5, 0);
        // Deterministic for a single option; future action sets will use seeded
        // stochastic sampling at decision boundaries, not on each tick.
        var policy = new StochasticPriorityPolicy(profile, citizen.getUUID().getLeastSignificantBits(), 0);
        ColonyPolicy.Decision selected = policy.choose(observation);
        if (!ActionGate.allowed(observation, selected)) return false;
        // World validation must still happen in the executor. No items granted here.
        AutonomousLibraryStudy.assign(level, citizen, shelf);
        return true;
    }
}
