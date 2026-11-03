package dev.hearthbound.world;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.phys.AABB;

/**
 * Experimental read-only Forge server-tick receipt source.
 *
 * Watches are configured explicitly by an operator, limited to a small bounded
 * number, and sampled only when chunks are loaded and a marked Sable can
 * legitimately observe the inventory. Does not issue game tasks, infer neural
 * policy decisions, force chunks, or grant citizens new observations.
 *
 * Revisions are session-local monitor revisions, NOT inventory transaction
 * revisions and must NEVER authorize resource transfers.
 */
public final class LivePerceptionReceipts {
    public static final String SCHEMA = "hearthbound.live-perception-receipt.v1";
    public static final int MAX_WATCHES_PER_LEVEL = 12;
    public static final int MAX_RECEIPTS_PER_LEVEL = 96;
    public static final long SAMPLE_EVERY_TICKS = 5L;

    private static final Map<ServerLevel,Monitor> MONITORS = new WeakHashMap<>();

    private static final class Watch {
        private SourceWheatObservation.Snapshot previous;
        private long revision;
    }
    private static final class Monitor {
        private final Map<BlockPos,Watch> watches = new HashMap<>();
        private final Deque<String> receipts = new ArrayDeque<>();
        private long lastSampleTick = Long.MIN_VALUE;
    }

    private LivePerceptionReceipts() {}

    private static Monitor monitor(ServerLevel level) {
        return MONITORS.computeIfAbsent(level,k -> new Monitor());
    }

    public static String watch(ServerLevel level,BlockPos source) {
        if(level == null || source == null) throw new IllegalArgumentException("Missing watch arguments");
        if(!level.hasChunkAt(source)) return "PERCEPTION_WATCH ABSTAIN reason=CHUNK_UNLOADED";
        Monitor m=monitor(level);
        BlockPos immutable=source.immutable();
        if(!m.watches.containsKey(immutable) && m.watches.size()>=MAX_WATCHES_PER_LEVEL)
            return "PERCEPTION_WATCH ABSTAIN reason=WATCH_CAP";
        m.watches.computeIfAbsent(immutable,ignored -> new Watch());
        return "PERCEPTION_WATCH status=REGISTERED source="+immutable.toShortString()
            +" schema="+SCHEMA+" mode=READ_ONLY";
    }

    public static String unwatch(ServerLevel level,BlockPos source) {
        if(level==null || source==null) throw new IllegalArgumentException("Missing unwatch arguments");
        return "PERCEPTION_UNWATCH removed="+(monitor(level).watches.remove(source)!=null)
            +" mode=READ_ONLY";
    }

    public static List<String> receipts(ServerLevel level) {
        if(level==null) throw new IllegalArgumentException("Missing level");
        return List.copyOf(monitor(level).receipts);
    }

    /** Called from Forge server LevelTickEvent.END on the main server thread. */
    public static void sample(ServerLevel level) {
        if(level==null) return;
        Monitor m=MONITORS.get(level);
        if(m==null || m.watches.isEmpty()) return;
        long tick=level.getGameTime();
        if(m.lastSampleTick==tick || tick%SAMPLE_EVERY_TICKS!=0L) return;
        m.lastSampleTick=tick;
        for(var entry:m.watches.entrySet()) {
            BlockPos source=entry.getKey();
            Watch watch=entry.getValue();
            // Never force chunk load, and do not leak remote information to
            // a worker or observer through an unbounded global scan.
            if(!level.hasChunkAt(source)) continue;
            var citizens=level.getEntitiesOfClass(Villager.class,
                new AABB(source).inflate(16),
                citizen -> "Sable".equals(citizen.getName().getString())
                    && citizen.getPersistentData().getBoolean("hearthbound.sable"));
            if(citizens.size()!=1) continue;
            var sampled=SourceWheatObservation.inspect(level,source,citizens.get(0));
            if(sampled.state()==SourceWheatObservation.State.UNKNOWN) continue;
            boolean changed=watch.previous==null
                || sampled.state()!=watch.previous.state()
                || sampled.wheat()!=watch.previous.wheat();
            if(changed) {
                watch.revision++;
                String receipt="PERCEPTION_RECEIPT schema="+SCHEMA
                    +" dimension="+level.dimension().location()
                    +" source="+source.toShortString()
                    +" revision="+watch.revision
                    +" tick="+sampled.tick()
                    +" state="+sampled.state()
                    +" wheat="+sampled.wheat()
                    +" observer="+citizens.get(0).getUUID()
                    +" evidence=REAL_FORGE_SOURCE_OBSERVATION"
                    +" action_authorized=false";
                if(m.receipts.size()>=MAX_RECEIPTS_PER_LEVEL) m.receipts.removeFirst();
                m.receipts.addLast(receipt);
            }
            watch.previous=sampled;
        }
    }

    public static String status(ServerLevel level) {
        Monitor m=monitor(level);
        return "PERCEPTION_STATUS schema="+SCHEMA
            +" watches="+m.watches.size()
            +" receipts="+m.receipts.size()
            +" sample_interval_ticks="+SAMPLE_EVERY_TICKS
            +" mode=READ_ONLY action_authorized=false";
    }
}
