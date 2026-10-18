package dev.hearthbound.world;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.npc.Villager;

/**
 * Persistent, individually varied starting instinct priors.
 * Deterministic from immutable citizen identity; these are NOT trained weights
 * or a complete genetic inheritance model. Explicit learning is a later phase.
 */
public final class CitizenInstincts {
    private static final String KEY = "hearthbound.instinctV1";
    private static final String[] NAMES = {
        "food", "shelter", "danger", "combat", "exploration", "cooperation"
    };

    private CitizenInstincts() {}

    public static CompoundTag get(Villager citizen) {
        CompoundTag root = citizen.getPersistentData();
        if (!root.contains(KEY)) {
            CompoundTag values = new CompoundTag();
            UUID id = citizen.getUUID();
            long seed = id.getMostSignificantBits() ^ Long.rotateLeft(id.getLeastSignificantBits(), 19);
            for (int i = 0; i < NAMES.length; i++) {
                // Stable, bounded profile. Avoids one-size-fits-all instincts.
                seed ^= (seed >>> 12);
                seed ^= (seed << 25);
                seed ^= (seed >>> 27);
                long mixed = seed * 2685821657736338717L;
                values.putInt(NAMES[i], 25 + (int) Long.remainderUnsigned(mixed, 51));
            }
            root.put(KEY, values);
        }
        return root.getCompound(KEY);
    }

    public static String inspect(Villager citizen) {
        CompoundTag tag = get(citizen);
        StringBuilder output = new StringBuilder("INSTINCT ageStage=ADULT");
        for (String key : NAMES) output.append(' ').append(key).append('=').append(tag.getInt(key));
        output.append(" [starting priors only; not a trained policy]");
        return output.toString();
    }
}
