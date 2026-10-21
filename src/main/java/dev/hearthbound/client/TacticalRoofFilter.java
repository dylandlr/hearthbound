package dev.hearthbound.client;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.client.Minecraft;
import dev.hearthbound.world.mixin.TacticalChunkRebuildAccessor;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.npc.Villager;

/**
 * Immutable snapshot read by chunk mesh worker threads. Never look up world
 * state from the mesh hook. Experimental: intentionally disabled by default.
 */
public final class TacticalRoofFilter {
    private static volatile Set<Long> hidden = Set.of();
    private static volatile boolean enabled;
    private static final AtomicLong suppressedRenders = new AtomicLong();
    public static long suppressedRenderCount() { return suppressedRenders.get(); }
    private TacticalRoofFilter() {}

    public static boolean suppress(BlockPos pos) {
        boolean suppress = enabled && hidden.contains(pos.asLong());
        if (suppress) suppressedRenders.incrementAndGet();
        return suppress;
    }

    public static void update(boolean requested, Villager citizen, int floor) {
        Minecraft mc = Minecraft.getInstance();
        Set<Long> next = Set.of();
        if (requested && citizen != null && mc.level != null
                && citizen.level() == mc.level && citizen.isAlive()) {
            Set<Long> calculated = new HashSet<>();
            for (BlockPos pos : RoofCutawayMask.sample(mc.level,
                    citizen.blockPosition(), floor, 5, 16)) {
                calculated.add(pos.asLong());
            }
            next = Set.copyOf(calculated);
        }
        if (enabled == requested && next.equals(hidden)) return;
        Set<Long> previous = hidden;
        hidden = next;
        enabled = requested;
        if (mc.levelRenderer == null || mc.level == null) return;
        Set<Long> dirty = new HashSet<>(previous);
        dirty.addAll(next);
        for (long packed : dirty) {
            BlockPos pos = BlockPos.of(packed);
            ((TacticalChunkRebuildAccessor) mc.levelRenderer).hearthbound$markBlockDirty(pos, true);
        }
    }

    public static void clear() {
        update(false, null, 64);
    }
}
