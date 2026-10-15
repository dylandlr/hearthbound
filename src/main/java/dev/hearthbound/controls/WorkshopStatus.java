package dev.hearthbound.controls;

import java.util.UUID;
import dev.hearthbound.jobs.WorkshopRegistry;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;

/** Bounded, read-only public station information. Inspection never claims or reserves. */
public record WorkshopStatus(String owner, Access access, Station wheat, Station mill, Station flour) {
    public enum Access { NONE, UNAVAILABLE, UNCLAIMED, OWNER, OPERATOR, DENIED }
    public enum State { NONE, UNAVAILABLE, FREE, SELF, OTHER, AWAY }
    public record Station(State state, BlockPos point, String holder, int waiting, boolean queued, boolean paused) {
        public Station {
            if (holder.length() > 64 || waiting < 0 || waiting > 999) throw new IllegalArgumentException("Invalid station status");
        }
        public String description() {
            return switch (state) {
                case NONE -> "Not selected";
                case UNAVAILABLE -> "Unavailable or out of range";
                case FREE -> "Available";
                case SELF -> "Reserved by this worker" + (paused ? " (paused)" : "");
                case OTHER -> "Reserved by " + holder + (paused ? " (paused)" : "");
                case AWAY -> "Reserved by a worker away";
            };
        }
        public String queueDescription() {
            if (state == State.NONE) return "Select a station in setup";
            if (state == State.UNAVAILABLE) return "Move closer to inspect this station";
            return "Waiting: " + waiting + (queued ? " — this worker is queued" : "");
        }
        private void encode(FriendlyByteBuf b) {
            b.writeEnum(state); b.writeBoolean(point != null); if (point != null) b.writeBlockPos(point);
            b.writeUtf(holder, 64); b.writeVarInt(waiting); b.writeBoolean(queued); b.writeBoolean(paused);
        }
        private static Station decode(FriendlyByteBuf b) {
            return new Station(b.readEnum(State.class), b.readBoolean() ? b.readBlockPos() : null, b.readUtf(64), b.readVarInt(), b.readBoolean(), b.readBoolean());
        }
    }
    public WorkshopStatus {
        if (owner.length() > 64) throw new IllegalArgumentException("Owner label too long");
    }
    public String accessDescription() {
        return switch (access) {
            case NONE -> "Choose a mill to see ownership";
            case UNAVAILABLE -> "Load the mill and move closer";
            case UNCLAIMED -> "Starting an order will claim this mill";
            case OWNER -> "Mill access: allowed";
            case OPERATOR -> "Mill access: operator";
            case DENIED -> "Mill access: another supervisor";
        };
    }
    public void encode(FriendlyByteBuf b) {
        b.writeUtf(owner, 64); b.writeEnum(access); wheat.encode(b); mill.encode(b); flour.encode(b);
    }
    public static WorkshopStatus decode(FriendlyByteBuf b) {
        return new WorkshopStatus(b.readUtf(64), b.readEnum(Access.class), Station.decode(b), Station.decode(b), Station.decode(b));
    }
    private static String bounded(String text) { return text.length() <= 64 ? text : text.substring(0, 64); }

    public static WorkshopStatus inspect(Villager worker, UUID viewer, boolean operator,
            BlockPos wheat, BlockPos mill, BlockPos flour) {
        if (!(worker.level() instanceof ServerLevel level)) throw new IllegalArgumentException("Server inspection only");
        var registry = WorkshopRegistry.get(level);
        boolean available = available(level, worker, mill, true);
        String name = mill == null ? "Not selected" : "Unavailable";
        Access access = mill == null ? Access.NONE : Access.UNAVAILABLE;
        if (available) {
            UUID owner = registry.owner(mill);
            if (owner == null) { name = "Unclaimed"; access = Access.UNCLAIMED; }
            else {
                var player = level.getServer().getPlayerList().getPlayer(owner);
                name = owner.equals(viewer) ? "You" : owner.equals(WorkshopRegistry.SERVER_OWNER) ? "Server"
                        : player == null ? "Another supervisor (offline)" : bounded(player.getName().getString());
                access = operator ? Access.OPERATOR : owner.equals(viewer) ? Access.OWNER : Access.DENIED;
            }
        }
        return new WorkshopStatus(name, access, station(level, worker, wheat, false),
                station(level, worker, mill, true), station(level, worker, flour, false));
    }

    private static boolean available(ServerLevel level, Villager worker, BlockPos point, boolean mill) {
        if (point == null || point.getY() < level.getMinBuildHeight() || point.getY() >= level.getMaxBuildHeight()
                || !level.hasChunkAt(point)
                || worker.distanceToSqr(point.getX() + .5, point.getY(), point.getZ() + .5) > 32 * 32) return false;
        return mill ? "create:millstone".equals(BuiltInRegistries.BLOCK.getKey(level.getBlockState(point).getBlock()).toString())
                : level.getBlockEntity(point) instanceof BarrelBlockEntity;
    }

    private static Station station(ServerLevel level, Villager worker, BlockPos point, boolean mill) {
        if (point == null) return new Station(State.NONE, null, "", 0, false, false);
        if (!available(level, worker, point, mill)) return new Station(State.UNAVAILABLE, point, "", 0, false, false);
        var registry = WorkshopRegistry.get(level);
        var lease = registry.holder(point);
        int waiting = registry.waitingAt(point, level.getGameTime());
        boolean queued = registry.isWaiting(worker.getUUID(), point, level.getGameTime());
        if (lease == null) return new Station(State.FREE, point, "", waiting, queued, false);
        var holder = level.getEntity(lease.worker());
        boolean self = lease.worker().equals(worker.getUUID());
        if (!(holder instanceof Villager citizen) || !citizen.isAlive()) return new Station(State.AWAY, point, "", waiting, queued, false);
        return new Station(self ? State.SELF : State.OTHER, point, bounded(citizen.getName().getString()), waiting, queued,
                citizen.getPersistentData().getCompound("HearthboundHaul").getBoolean("Paused"));
    }
}
