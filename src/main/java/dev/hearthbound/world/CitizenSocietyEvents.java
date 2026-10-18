package dev.hearthbound.world;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;

/**
 * Physical-event-provenanced social memory. No omniscient colony reputation.
 * Each witness interprets only deliveries in physical observation radius.
 * An actor records their own contribution even when no witness is present.
 */
public final class CitizenSocietyEvents {
    private static final String KEY = "hearthbound.socialV1";
    private static final int LIMIT = 32;
    private static final double WITNESS_RADIUS = 12;

    private CitizenSocietyEvents() {}

    private static CompoundTag memory(Villager villager) {
        CompoundTag root = villager.getPersistentData();
        if (!root.contains(KEY)) root.put(KEY, new CompoundTag());
        return root.getCompound(KEY);
    }

    /** Called only after SableHauling has committed and cleared physical cargo. */
    public static void completedHaul(ServerLevel level, Villager actor, UUID job, BlockPos destination) {
        if (job == null) return;
        // Save the objective event against its actor, even when nobody sees it.
        record(actor, actor, job, level.getGameTime(), destination, true);
        AABB bounds = new AABB(destination).inflate(WITNESS_RADIUS);
        for (Villager observer : level.getEntitiesOfClass(Villager.class, bounds,
                villager -> villager != actor
                        && villager.getPersistentData().getBoolean("hearthbound.sable")
                        && villager.hasLineOfSight(actor))) {
            record(observer, actor, job, level.getGameTime(), destination, false);
        }
    }

    private static void record(Villager observer, Villager actor, UUID job,
                               long tick, BlockPos location, boolean self) {
        CompoundTag root = memory(observer);
        ListTag entries = root.getList("events", Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++) {
            if (entries.getCompound(i).hasUUID("job")
                    && job.equals(entries.getCompound(i).getUUID("job"))) return;
        }
        CompoundTag entry = new CompoundTag();
        entry.putUUID("job", job);
        entry.putUUID("actor", actor.getUUID());
        entry.putString("name", actor.getName().getString());
        entry.putLong("tick", tick);
        entry.putLong("location", location.asLong());
        entry.putString("event", "WHEAT_DELIVERY");
        entry.putBoolean("direct", true);
        entry.putBoolean("self", self);
        entries.add(entry);
        while (entries.size() > LIMIT) entries.remove(0);
        root.put("events", entries);
        // Perspective-specific appraisal of verified contribution; no global score.
        if (!self) {
            String key = "reputation_" + actor.getUUID();
            // The cooperation instinct is a primitive norm preference, NOT a fixed moral fact.
            int appreciation = CitizenInstincts.get(observer).getInt("cooperation") >= 50 ? 2 : 1;
            root.putInt(key, Math.min(100, root.getInt(key) + appreciation));
        }
    }

    public static String inspect(Villager observer) {
        CompoundTag root = memory(observer);
        ListTag entries = root.getList("events", Tag.TAG_COMPOUND);
        StringBuilder out = new StringBuilder("SOCIAL_MEMORY events=").append(entries.size());
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag e = entries.getCompound(i);
            out.append(" | ").append(e.getString("event"))
                    .append(" actor=").append(e.getString("name"))
                    .append(" job=").append(e.getUUID("job"))
                    .append(" tick=").append(e.getLong("tick"))
                    .append(" source=").append(e.getBoolean("self") ? "SELF" : "WITNESS")
                    .append(" rep=").append(root.getInt("reputation_" + e.getUUID("actor")));
        }
        return out.toString();
    }

    /** Social-graph view exposes only recorded direct encounters. */
    public static String web(ServerLevel level, Villager viewer) {
        List<Villager> citizens = new ArrayList<>(level.getEntitiesOfClass(Villager.class,
                new AABB(viewer.blockPosition()).inflate(32),
                v -> v.getPersistentData().getBoolean("hearthbound.sable")));
        citizens.sort(Comparator.comparing(Villager::getUUID));
        StringBuilder result = new StringBuilder("SOCIAL_WEB citizens=").append(citizens.size());
        for (Villager v : citizens) {
            result.append(" | citizen=").append(v.getName().getString())
                    .append(" pos=").append(v.blockPosition())
                    .append(" knownEvents=").append(memory(v).getList("events", Tag.TAG_COMPOUND).size());
        }
        return result.toString();
    }
}
