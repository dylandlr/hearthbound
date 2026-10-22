package dev.hearthbound.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.registries.ForgeRegistries;

/** Operator-initiated, bounded server-side telemetry. Not authoritative consumption proof. */
public final class MillstoneTrace {
    public record Sample(long logicalTick, String inventories) {}
    private static Session session;
    private record Session(UUID id, String dimension, BlockPos position, int maxSamples, List<Sample> samples) {}
    private MillstoneTrace() {}

    public static synchronized UUID begin(ServerLevel level, BlockPos position, int maxSamples) {
        if (session != null) throw new IllegalStateException("Trace already active");
        if (maxSamples < 1 || maxSamples > 1200) throw new IllegalArgumentException("Trace limit must be 1..1200");
        requireMillstone(level, position);
        session = new Session(UUID.randomUUID(), level.dimension().location().toString(),
                position.immutable(), maxSamples, new ArrayList<>());
        return session.id();
    }
    public static synchronized String stop() {
        if (session == null) return "No active trace";
        StringBuilder out = new StringBuilder("Trace ").append(session.id()).append(" samples=").append(session.samples().size());
        for (Sample sample : session.samples().subList(Math.max(0, session.samples().size()-20), session.samples().size())) out.append("\n").append(sample.logicalTick()).append(" ").append(sample.inventories());
        if (session.samples().size() > 20) out.append("\n(only last 20 samples shown)");
        session = null;
        return out.toString();
    }
    public static synchronized void sample(ServerLevel level, long tick) {
        Session s = session;
        if (s == null || !level.dimension().location().toString().equals(s.dimension())) return;
        if (s.samples().size() >= s.maxSamples()) return;
        if (!level.hasChunkAt(s.position())) return;
        try {
            requireMillstone(level, s.position());
            BlockEntity be = level.getBlockEntity(s.position());
            StringBuilder inventory = new StringBuilder();
            be.getCapability(ForgeCapabilities.ITEM_HANDLER).ifPresent(handler -> {
                for (int i=0; i<handler.getSlots(); i++) {
                    ItemStack stack=handler.getStackInSlot(i);
                    if (!stack.isEmpty()) inventory.append(i).append(":")
                            .append(ForgeRegistries.ITEMS.getKey(stack.getItem())).append("x")
                            .append(stack.getCount()).append(" ");
                }
            });
            s.samples().add(new Sample(tick, inventory.length() == 0 ? "(no exposed items)" : inventory.toString()));
        } catch (IllegalArgumentException ex) {
            s.samples().add(new Sample(tick, "MILLSTONE_REMOVED"));
        }
    }
    private static void requireMillstone(ServerLevel level, BlockPos pos) {
        var id=ForgeRegistries.BLOCKS.getKey(level.getBlockState(pos).getBlock());
        if (id == null || !"create".equals(id.getNamespace()) || !"millstone".equals(id.getPath())
                || level.getBlockEntity(pos) == null) throw new IllegalArgumentException("No Create millstone at position");
    }
}
