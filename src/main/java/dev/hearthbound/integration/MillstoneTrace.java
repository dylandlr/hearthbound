package dev.hearthbound.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.registries.ForgeRegistries;

/** Operator-initiated, bounded server-side telemetry. Not authoritative consumption proof. */
public final class MillstoneTrace {
    public record Sample(long logicalTick, String inventories) {}
    private static Session session;
    private static String lastReport;
    private record Session(UUID id, String dimension, BlockPos position, int maxSamples, List<Sample> samples) {}
    private MillstoneTrace() {}

    public static synchronized UUID begin(ServerLevel level, BlockPos position, int maxSamples) {
        if (session != null) throw new IllegalStateException("Trace already active");
        if (maxSamples < 1 || maxSamples > 1200) throw new IllegalArgumentException("Trace limit must be 1..1200");
        requireMillstone(level, position);
        lastReport = null;
        session = new Session(UUID.randomUUID(), level.dimension().location().toString(),
                position.immutable(), maxSamples, new ArrayList<>());
        return session.id();
    }
    private static String report(Session s) {
        StringBuilder out = new StringBuilder("Trace ").append(s.id()).append(" samples=").append(s.samples().size());
        for (Sample sample : s.samples().subList(Math.max(0, s.samples().size()-20), s.samples().size()))
            out.append("\\n").append(sample.logicalTick()).append(" ").append(sample.inventories());
        if (s.samples().size() > 20) out.append("\\n(only last 20 samples shown)");
        return out.toString();
    }
    public static synchronized String status() {
        if (session != null) return "Trace active id=" + session.id() + " samples=" + session.samples().size() + "/" + session.maxSamples();
        return lastReport == null ? "No active or completed trace" : "Trace completed; use trace stop to inspect the last report";
    }
    public static synchronized String stop() {
        if (session != null) {
            String result = report(session);
            session = null;
            lastReport = null;
            return result;
        }
        if (lastReport != null) {
            String result = lastReport;
            lastReport = null;
            return result;
        }
        return "No active or completed trace";
    }
    public static synchronized void sample(ServerLevel level, long tick) {
        Session s = session;
        if (s == null || !level.dimension().location().toString().equals(s.dimension())) return;
        if (s.samples().size() >= s.maxSamples()) return;
        if (!level.hasChunkAt(s.position())) return;
        try {
            requireMillstone(level, s.position());
            BlockEntity be = level.getBlockEntity(s.position());
            if (!(be instanceof MillstoneBlockEntity millstone)) throw new IllegalArgumentException("Expected millstone entity");
            StringBuilder inventory = new StringBuilder()
                    .append("rpm=").append(millstone.getSpeed())
                    .append(" timer=").append(millstone.timer)
                    .append(" speed=").append(millstone.getProcessingSpeed())
                    .append(" input=").append(millstone.inputInv.getStackInSlot(0))
                    .append(" outputs=");
            for (int i=0; i<millstone.outputInv.getSlots(); i++) {
                ItemStack item=millstone.outputInv.getStackInSlot(i);
                if (!item.isEmpty()) inventory.append(i).append(":").append(ForgeRegistries.ITEMS.getKey(item.getItem())).append("x").append(item.getCount()).append(" ");
            }
            inventory.append(" capability=");
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
        if (s.samples().size() >= s.maxSamples()) {
            lastReport = report(s);
            session = null;
        }
    }
    private static void requireMillstone(ServerLevel level, BlockPos pos) {
        var id=ForgeRegistries.BLOCKS.getKey(level.getBlockState(pos).getBlock());
        if (id == null || !"create".equals(id.getNamespace()) || !"millstone".equals(id.getPath())
                || level.getBlockEntity(pos) == null) throw new IllegalArgumentException("No Create millstone at position");
    }
}
