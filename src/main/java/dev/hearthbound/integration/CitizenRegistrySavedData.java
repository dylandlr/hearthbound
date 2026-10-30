package dev.hearthbound.integration;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;

/** First persistent, server-owned citizen registry. Records are not spawned entities. */
public final class CitizenRegistrySavedData extends SavedData {
    private static final String KEY = "hearthbound_citizens_v1";
    private final Map<UUID, Citizen> citizens = new LinkedHashMap<>();
    public record Citizen(UUID id, String name, String dimension, long position, String task, long lastTick) {}
    public static CitizenRegistrySavedData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(
                CitizenRegistrySavedData::load, CitizenRegistrySavedData::new, KEY);
    }
    public static CitizenRegistrySavedData load(CompoundTag data) {
        if (data.getInt("Version") != 1) throw new IllegalArgumentException("Invalid citizen registry version");
        CitizenRegistrySavedData result = new CitizenRegistrySavedData();
        ListTag list = data.getList("Citizens", Tag.TAG_COMPOUND);
        for (int i=0;i<list.size();i++) {
            CompoundTag item = list.getCompound(i);
            if (!item.hasUUID("Id") || item.getString("Name").isBlank())
                throw new IllegalArgumentException("Invalid citizen record");
            Citizen citizen = new Citizen(item.getUUID("Id"), item.getString("Name"),
                    item.getString("Dimension"), item.getLong("Position"),
                    item.getString("Task"), item.getLong("LastTick"));
            if(result.citizens.putIfAbsent(citizen.id(), citizen)!=null)
                throw new IllegalArgumentException("Duplicate citizen ID");
        }
        return result;
    }
    public Citizen register(UUID id,String name,String dimension,long position,long tick) {
        if(id==null || name==null || name.isBlank() || dimension==null || dimension.isBlank() || tick<0)
            throw new IllegalArgumentException("Invalid citizen identity");
        if(citizens.containsKey(id)) throw new IllegalArgumentException("Citizen already exists");
        Citizen record = new Citizen(id,name,dimension,position,"IDLE",tick);
        citizens.put(id,record);
        setDirty();
        return record;
    }
    public Citizen assignMove(UUID id, String dimension, long target, long tick) {
        Citizen current = citizens.get(id);
        if (current == null || !current.dimension().equals(dimension) || tick < current.lastTick())
            throw new IllegalArgumentException("Missing citizen or inconsistent dimension/tick");
        Citizen changed = new Citizen(id, current.name(), dimension, current.position(),
                "MOVE:" + target, tick);
        citizens.put(id, changed);
        setDirty();
        return changed;
    }
    public Citizen assignMillSupply(UUID id,String dimension,long worksite,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.dimension().equals(dimension) || tick<current.lastTick()
                || !"IDLE".equals(current.task()))
            throw new IllegalArgumentException("Citizen must be idle in the assigned dimension");
        Citizen next=new Citizen(id,current.name(),dimension,current.position(),
                "MILL_SUPPLY:"+worksite,tick);
        citizens.put(id,next);
        setDirty();
        return next;
    }
    /** Assign a physical approach to collect real millstone output. */
    public Citizen assignMillCollect(UUID id,String dimension,long worksite,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.dimension().equals(dimension) || tick<current.lastTick()
                || !"IDLE".equals(current.task()))
            throw new IllegalArgumentException("Citizen must be idle in the assigned dimension");
        Citizen next=new Citizen(id,current.name(),dimension,current.position(),
                "MILL_COLLECT:"+worksite,tick);
        citizens.put(id,next);
        setDirty();
        return next;
    }
    public Citizen assignStockpileDelivery(UUID id,String dimension,long destination,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.dimension().equals(dimension) || tick<current.lastTick()
                || !"IDLE".equals(current.task()))
            throw new IllegalArgumentException("Citizen must be idle for stockpile delivery");
        Citizen next=new Citizen(id,current.name(),dimension,current.position(),
                "STOCKPILE_DELIVER:"+destination,tick);
        citizens.put(id,next);
        setDirty();
        return next;
    }
    public void completeStockpileDelivery(UUID id,long position,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.task().startsWith("STOCKPILE_DELIVER:"))
            throw new IllegalStateException("No outstanding stockpile delivery");
        citizens.put(id,new Citizen(id,current.name(),current.dimension(),position,"IDLE",tick));
        setDirty();
    }
    public void completeCollect(UUID id,long position,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.task().startsWith("MILL_COLLECT:"))
            throw new IllegalStateException("Citizen has no outstanding collection task");
        citizens.put(id,new Citizen(id,current.name(),current.dimension(),position,"IDLE",tick));
        setDirty();
    }
    /** Wait for observed Create output; do not assume milling finished on supply. */
    public Citizen awaitMillOutput(UUID id,String dimension,long approach,long position,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.dimension().equals(dimension) || tick<current.lastTick()
                || !"MILL_SUPPLY:".concat(Long.toString(approach)).equals(current.task()))
            throw new IllegalStateException("Only an assigned supplier can await its mill output");
        Citizen next=new Citizen(id,current.name(),dimension,position,
                "MILL_WAIT_OUTPUT:"+approach,tick);
        citizens.put(id,next);
        setDirty();
        return next;
    }
    public Citizen collectReadyMillOutput(UUID id,long approach,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || tick<current.lastTick()
                || !current.task().equals("MILL_WAIT_OUTPUT:"+approach))
            throw new IllegalStateException("Citizen is not awaiting that mill");
        Citizen next=new Citizen(id,current.name(),current.dimension(),current.position(),
                "MILL_COLLECT:"+approach,tick);
        citizens.put(id,next);
        setDirty();
        return next;
    }
    public void completeSupply(UUID id,long position,long tick) {
        Citizen current=citizens.get(id);
        if(current==null || !current.task().startsWith("MILL_SUPPLY:"))
            throw new IllegalStateException("Citizen has no outstanding milling task");
        citizens.put(id,new Citizen(id,current.name(),current.dimension(),position,"IDLE",tick));
        setDirty();
    }
    public void observe(UUID id, long position, long tick, boolean arrived) {
        Citizen current = citizens.get(id);
        if (current == null || tick < current.lastTick()) return;
        String task = arrived && current.task().startsWith("MOVE:") ? "IDLE" : current.task();
        if (current.position() != position || !task.equals(current.task())) {
            citizens.put(id, new Citizen(id,current.name(),current.dimension(),position,task,tick));
            setDirty();
        }
    }
    public int size() {return citizens.size();}
    public java.util.List<Citizen> snapshot() {return java.util.List.copyOf(citizens.values());}
    @Override public CompoundTag save(CompoundTag data) {
        data.putInt("Version",1);
        ListTag list=new ListTag();
        for(Citizen citizen:citizens.values()) {
            CompoundTag item=new CompoundTag();
            item.putUUID("Id",citizen.id());
            item.putString("Name",citizen.name());
            item.putString("Dimension",citizen.dimension());
            item.putLong("Position",citizen.position());
            item.putString("Task",citizen.task());
            item.putLong("LastTick",citizen.lastTick());
            list.add(item);
        }
        data.put("Citizens",list);
        return data;
    }
}
