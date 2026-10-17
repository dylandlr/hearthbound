package dev.hearthbound.research;

import dev.hearthbound.ai.CitizenWorkDispatcher;
import dev.hearthbound.ai.ColonyPolicy;
import dev.hearthbound.ai.StochasticPriorityPolicy;
import dev.hearthbound.world.SableHauling;
import java.util.List;
import java.util.Map;
import java.util.UUID;
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
    private static final String LEASE_KEY = "hearthbound.studyLeaseV1";
    private static final CitizenWorkDispatcher DISPATCH =
            new CitizenWorkDispatcher(new CitizenTaskArbiter());
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

    /** Clear ownership after the executor has conclusively finished or failed. */
    public static void reconcile(Villager citizen) {
        CompoundTag state = citizen.getPersistentData().getCompound(LEASE_KEY);
        if (!state.hasUUID("assignment")) return;
        UUID assignment = state.getUUID("assignment");
        if (AutonomousLibraryStudy.active(citizen)) {
            // Reconstruct in-memory ownership after a server restart.
            // A stale or conflicting lease must never silently steal ownership.
            DISPATCH.restore(citizen.getUUID(), new CitizenTaskArbiter.Lease(
                    assignment, CitizenTaskArbiter.Kind.STUDY,
                    Math.max(0, state.getLong("acquiredTick"))));
            return;
        }
        DISPATCH.complete(citizen.getUUID(), assignment);
        citizen.getPersistentData().remove(LEASE_KEY);
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
        // The shared dispatcher owns the assignment. Never mutate the world
        // before ActionGate and exclusive task lease acceptance.
        var result = DISPATCH.dispatch(citizen.getUUID(), observation,
                ignored -> selected, (action, lease) -> {
                    if (!LibraryStudyRuntime.hasBook(level, shelf)) return false;
                    if (AutonomousLibraryStudy.active(citizen)
                            || SableHauling.active(citizen)) return false;
                    AutonomousLibraryStudy.assign(level, citizen, shelf);
                    return true;
                });
        if (!result.accepted()) return false;
        CompoundTag leaseTag = new CompoundTag();
        leaseTag.putUUID("assignment", result.lease().assignmentId());
        leaseTag.putLong("acquiredTick", result.lease().acquiredTick());
        citizen.getPersistentData().put(LEASE_KEY, leaseTag);
        return true;
    }
}
