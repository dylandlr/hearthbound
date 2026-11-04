package dev.hearthbound.world;

import java.util.HashMap;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.Set;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Operator-registered, per-citizen read-only sampling subscriptions.
 * Does not discover sources, move citizens, load chunks, authorize tasks,
 * or expose observations between citizens.
 */
public final class CitizenWatchRegistry {
    public static final String SCHEMA = "hearthbound.citizen-watch.v1";
    public static final int MAX_WATCHES_PER_LEVEL = 24;
    public static final int MAX_WATCHES_PER_CITIZEN = 4;
    public static final long SAMPLE_INTERVAL_TICKS = 5;
    public static final int MAX_INSPECTIONS_PER_CITIZEN_PER_INTERVAL = 1;
    private static final Map<ServerLevel, Registry> REGISTRIES = new java.util.WeakHashMap<>();

    private record Key(UUID citizen, BlockPos source) {}
    private static final class Watch {
        private SourceWheatObservation.State previousState;
        private int previousWheat;
        private long revision;
        private long lastAttemptTick = Long.MIN_VALUE;
        private String latest = "";
    }
    private static final class Registry {
        private final Map<Key, Watch> watches = new HashMap<>();
        private long lastTick = Long.MIN_VALUE;
    }

    private CitizenWatchRegistry() {}

    private static Registry registry(ServerLevel level) {
        return REGISTRIES.computeIfAbsent(level, ignored -> new Registry());
    }

    public static String watch(ServerLevel level, BlockPos source, Villager citizen) {
        if (level == null || source == null || citizen == null)
            throw new IllegalArgumentException("missing watch arguments");
        if (citizen.level() != level || !CitizenSourceKnowledge.isCitizen(citizen))
            return "CITIZEN_WATCH status=ABSTAIN reason=INVALID_CITIZEN action_authorized=false";
        if (!level.hasChunkAt(source))
            return "CITIZEN_WATCH status=ABSTAIN reason=CHUNK_UNLOADED action_authorized=false";
        if (citizen.distanceToSqr(source.getX()+0.5,source.getY()+0.5,source.getZ()+0.5)>256.0)
            return "CITIZEN_WATCH status=ABSTAIN reason=OUT_OF_RANGE action_authorized=false";
        Registry r=registry(level);
        Key key=new Key(citizen.getUUID(),source.immutable());
        if (!r.watches.containsKey(key)) {
            if (r.watches.size()>=MAX_WATCHES_PER_LEVEL)
                return "CITIZEN_WATCH status=ABSTAIN reason=LEVEL_CAP action_authorized=false";
            long existing=r.watches.keySet().stream().filter(k -> k.citizen().equals(citizen.getUUID())).count();
            if (existing>=MAX_WATCHES_PER_CITIZEN)
                return "CITIZEN_WATCH status=ABSTAIN reason=CITIZEN_CAP action_authorized=false";
            r.watches.put(key,new Watch());
        }
        return "CITIZEN_WATCH status=REGISTERED citizen="+citizen.getUUID()
            +" source="+source.getX()+","+source.getY()+","+source.getZ()
            +" action_authorized=false";
    }

    public static String unwatch(ServerLevel level, BlockPos source, Villager citizen) {
        if(level==null || source==null || citizen==null)
            throw new IllegalArgumentException("missing watch arguments");
        boolean removed=registry(level).watches.remove(new Key(citizen.getUUID(),source))!=null;
        return "CITIZEN_UNWATCH removed="+removed+" action_authorized=false";
    }

    public static String latest(ServerLevel level, BlockPos source, Villager citizen) {
        if(level==null || source==null || citizen==null)
            throw new IllegalArgumentException("missing query arguments");
        if(!CitizenSourceKnowledge.isCitizen(citizen) || citizen.level()!=level)
            return "CITIZEN_WATCH_LATEST status=ABSTAIN reason=INVALID_CITIZEN action_authorized=false";
        Watch watch=registry(level).watches.get(new Key(citizen.getUUID(),source));
        if(watch==null || watch.latest.isEmpty())
            return "CITIZEN_WATCH_LATEST status=UNKNOWN action_authorized=false";
        return watch.latest;
    }

    /** Operator-only diagnostic: subscriptions are not observation permission for other citizens. */
    public static String attention(ServerLevel level, Villager citizen) {
        if(level==null || citizen==null) throw new IllegalArgumentException("missing query arguments");
        if(citizen.level()!=level || !CitizenSourceKnowledge.isCitizen(citizen))
            return "CITIZEN_ATTENTION status=ABSTAIN reason=INVALID_CITIZEN action_authorized=false";
        Registry r=registry(level);
        long count=r.watches.keySet().stream().filter(k -> k.citizen().equals(citizen.getUUID())).count();
        return "CITIZEN_ATTENTION schema=hearthbound.citizen-attention.v1 citizen="+citizen.getUUID()
            +" subscriptions="+count
            +" budget="+MAX_INSPECTIONS_PER_CITIZEN_PER_INTERVAL
            +" interval_ticks="+SAMPLE_INTERVAL_TICKS
            +" policy=LEAST_RECENTLY_SAMPLED action_authorized=false";
    }

    /** Called only on Forge main-thread level tick. Does not force source chunk loads. */
    public static void sample(ServerLevel level) {
        if (level==null) return;
        Registry r=REGISTRIES.get(level);
        if(r==null || r.watches.isEmpty()) return;
        long tick=level.getGameTime();
        if(tick==r.lastTick || tick%SAMPLE_INTERVAL_TICKS!=0) return;
        r.lastTick=tick;
        // The baseline scripted attention policy spends only one source inspection
        // per citizen per sampling interval. Ordering is deterministic and fair:
        // least recently attempted first, then coordinates to break ties.
        var ordered=new ArrayList<>(r.watches.entrySet());
        ordered.sort(Comparator
            .comparing((Map.Entry<Key,Watch> e) -> e.getKey().citizen().toString())
            .thenComparingLong(e -> e.getValue().lastAttemptTick)
            .thenComparingInt(e -> e.getKey().source().getX())
            .thenComparingInt(e -> e.getKey().source().getY())
            .thenComparingInt(e -> e.getKey().source().getZ()));
        Set<UUID> spent=new HashSet<>();
        for(var entry:ordered) {
            Key key=entry.getKey();
            Watch watch=entry.getValue();
            if(!spent.add(key.citizen())) continue;
            watch.lastAttemptTick=tick;
            if(!level.hasChunkAt(key.source())) continue;
            Key key=entry.getKey();
            Watch watch=entry.getValue();
            if(!level.hasChunkAt(key.source())) continue;
            var entity=level.getEntity(key.citizen());
            if(!(entity instanceof Villager citizen) || !citizen.isAlive()
                || !CitizenSourceKnowledge.isCitizen(citizen)) continue;
            var snapshot=SourceWheatObservation.inspect(level,key.source(),citizen);
            if(snapshot.state()==SourceWheatObservation.State.UNKNOWN) continue;
            boolean changed=watch.previousState==null
                || watch.previousState!=snapshot.state()
                || watch.previousWheat!=snapshot.wheat();
            CitizenSourceKnowledge.remember(level,key.source(),citizen,snapshot);
            if(changed) {
                watch.revision++;
                watch.latest="CITIZEN_WATCH_RECEIPT schema="+SCHEMA
                    +" observer="+citizen.getUUID()
                    +" dimension="+level.dimension().location()
                    +" source="+key.source().getX()+","+key.source().getY()+","+key.source().getZ()
                    +" revision="+watch.revision
                    +" tick="+snapshot.tick()
                    +" state="+snapshot.state()
                    +" wheat="+snapshot.wheat()
                    +" origin=DIRECT_FORGE_OBSERVATION action_authorized=false";
            }
            watch.previousState=snapshot.state();
            watch.previousWheat=snapshot.wheat();
        }
    }
}
