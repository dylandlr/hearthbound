package dev.hearthbound.jobs;

import java.util.Comparator;
import java.util.function.Predicate;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;

/** Consistent command targeting when multiple colony workers are nearby. */
public final class SableSelection {
    private SableSelection() {}

    public static boolean idle(Villager worker) {
        var data = worker.getPersistentData();
        return !data.contains("HearthboundHaul", 10)
                && !data.getBoolean("HearthboundTravelActive")
                && !data.contains("HearthboundMillOrder", 10);
    }

    public static Villager nearest(CommandSourceStack source, Predicate<Villager> eligible) {
        return source.getLevel().getEntitiesOfClass(Villager.class,
                new AABB(source.getPosition(), source.getPosition()).inflate(32),
                worker -> worker.isAlive() && worker.getTags().contains("hearthbound.sable")
                        && eligible.test(worker))
                .stream().min(Comparator.comparingDouble((Villager worker) ->
                        worker.distanceToSqr(source.getPosition()))
                        .thenComparing(Villager::getUUID)).orElse(null);
    }
}
