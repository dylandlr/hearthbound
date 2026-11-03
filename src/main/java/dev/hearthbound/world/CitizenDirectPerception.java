package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Deliberately triggered, citizen-scoped physical source observation.
 * This is a read-only operator experiment, not autonomous sensory scanning.
 */
public final class CitizenDirectPerception {
    private CitizenDirectPerception() {}

    public static String observe(ServerLevel level, BlockPos source, Villager observer) {
        if (level == null || source == null || observer == null)
            throw new IllegalArgumentException("missing perception arguments");
        String prefix = "CITIZEN_DIRECT_OBSERVATION citizen=" + observer.getUUID()
            + " dimension=" + level.dimension().location()
            + " source=" + source.getX() + "," + source.getY() + "," + source.getZ();
        if (!CitizenSourceKnowledge.isCitizen(observer) || observer.level() != level)
            return prefix + " status=ABSTAIN reason=INVALID_CITIZEN action_authorized=false";
        var snapshot = SourceWheatObservation.inspect(level, source, observer);
        if (snapshot.state() == SourceWheatObservation.State.UNKNOWN)
            return prefix + " status=ABSTAIN reason=" + snapshot.reason()
                + " tick=" + snapshot.tick() + " action_authorized=false";
        CitizenSourceKnowledge.remember(level, source, observer, snapshot);
        return prefix + " status=OBSERVED state=" + snapshot.state()
            + " wheat=" + snapshot.wheat() + " tick=" + snapshot.tick()
            + " provenance=DIRECT_FORGE_OBSERVATION action_authorized=false";
    }
}
