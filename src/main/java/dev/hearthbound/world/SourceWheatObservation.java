package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.common.capabilities.ForgeCapabilities;

/**
 * Read-only, partially observable wheat-source sensor.
 * No chunk loading, no inventory mutation and no neural input redefinition.
 */
public final class SourceWheatObservation {
    public enum State { UNKNOWN, EMPTY, AVAILABLE }
    public record Snapshot(State state, int wheat, long tick, String reason) {
        public Snapshot {
            if (state == null || reason == null || wheat < 0)
                throw new IllegalArgumentException("invalid source observation");
            if (state == State.UNKNOWN && wheat != 0)
                throw new IllegalArgumentException("unknown source cannot assert quantity");
            if (state == State.EMPTY && wheat != 0)
                throw new IllegalArgumentException("empty source cannot contain wheat");
            if (state == State.AVAILABLE && wheat == 0)
                throw new IllegalArgumentException("available source must contain wheat");
        }
    }
    private SourceWheatObservation() {}

    private static Snapshot unknown(ServerLevel level, String reason) {
        return new Snapshot(State.UNKNOWN, 0, level.getGameTime(), reason);
    }

    public static Snapshot inspect(ServerLevel level, BlockPos source, Villager citizen) {
        if (level == null || source == null || citizen == null)
            throw new IllegalArgumentException("missing observation argument");
        if (!level.hasChunkAt(source))
            return unknown(level, "CHUNK_UNLOADED");
        // A citizen does not receive free global inventory knowledge.
        if (citizen.distanceToSqr(source.getX()+0.5, source.getY()+0.5, source.getZ()+0.5)
                > 16.0 * 16.0)
            return unknown(level, "OUT_OF_SENSOR_RANGE");
        BlockEntity entity = level.getBlockEntity(source);
        if (entity == null)
            return unknown(level, "NO_BLOCK_ENTITY");
        int wheat = 0;
        var capability = entity.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (capability.isPresent()) {
            var inv = capability.orElseThrow(IllegalStateException::new);
            for (int i=0;i<inv.getSlots();i++) {
                var stack=inv.getStackInSlot(i);
                if (stack.is(Items.WHEAT)) wheat += stack.getCount();
            }
        } else if (entity instanceof Container inv) {
            for (int i=0;i<inv.getContainerSize();i++) {
                var stack=inv.getItem(i);
                if (stack.is(Items.WHEAT)) wheat += stack.getCount();
            }
        } else {
            return unknown(level, "UNSUPPORTED_INVENTORY");
        }
        return new Snapshot(wheat > 0 ? State.AVAILABLE : State.EMPTY,
                            wheat, level.getGameTime(), "OBSERVED");
    }

    /** Admin/read-only probe: one real Sable within 16 blocks of the source. */
    public static String inspectNearbySable(ServerLevel level, BlockPos source) {
        if (!level.hasChunkAt(source))
            return "SOURCE_OBSERVATION state=UNKNOWN wheat=0 reason=CHUNK_UNLOADED"
                + " tick=" + level.getGameTime() + " EXECUTION_DISABLED";
        var citizens = level.getEntitiesOfClass(Villager.class, new AABB(source).inflate(16),
            citizen -> "Sable".equals(citizen.getName().getString())
                && citizen.getPersistentData().getBoolean("hearthbound.sable"));
        if (citizens.size()!=1)
            return "SOURCE_OBSERVATION state=UNKNOWN wheat=0 reason=REQUIRES_ONE_MARKED_SABLE"
                + " tick=" + level.getGameTime() + " EXECUTION_DISABLED";
        var snapshot=inspect(level, source, citizens.get(0));
        return "SOURCE_OBSERVATION state=" + snapshot.state() + " wheat=" + snapshot.wheat()
            + " reason=" + snapshot.reason() + " tick=" + snapshot.tick()
            + " citizen=" + citizens.get(0).getUUID() + " EXECUTION_DISABLED";
    }
}
