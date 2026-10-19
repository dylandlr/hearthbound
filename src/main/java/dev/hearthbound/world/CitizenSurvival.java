package dev.hearthbound.world;

import dev.hearthbound.ai.SurvivalPolicy;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.Vec3;
import java.util.Comparator;

/** Opt-in physical survival baseline. Hunger is a Hearthbound need (vanilla villagers have no hunger bar).
 * Emergency navigation suspends jobs in place: cargo and job identity are never cleared here.
 */
public final class CitizenSurvival {
    private static final String KEY = "hearthbound.survivalV1";
    private CitizenSurvival() {}
    public static void enable(Villager v, boolean enabled) {
        CompoundTag t = v.getPersistentData().getCompound(KEY);
        if (!t.contains("food")) t.putDouble("food", 20);
        t.putBoolean("enabled", enabled);
        t.putString("action", "WORK");
        t.putLong("lastTick", v.level().getGameTime());
        v.getPersistentData().put(KEY, t);
        v.getNavigation().stop();
    }
    public static boolean paused(Villager v) {
        CompoundTag t = v.getPersistentData().getCompound(KEY);
        return t.getBoolean("enabled") && !"WORK".equals(t.getString("action"));
    }
    private static int nutrition(ItemStack item) {
        if (item.is(Items.BREAD) || item.is(Items.BAKED_POTATO)) return 5;
        if (item.is(Items.CARROT)) return 3;
        if (item.is(Items.APPLE)) return 4;
        return 0;
    }
    private static int foodSlot(Villager v) {
        for (int i=0; i<v.getInventory().getContainerSize(); i++)
            if (!v.getInventory().getItem(i).isEmpty() && nutrition(v.getInventory().getItem(i))>0) return i;
        return -1;
    }
    private static boolean covered(ServerLevel level, BlockPos p) {
        return level.hasChunkAt(p) && level.getBlockState(p).isAir()
            && level.getBlockState(p.above()).isAir()
            && level.getBlockState(p.below()).isSolidRender(level, p.below())
            && !level.canSeeSky(p);
    }
    private static BlockPos shelter(ServerLevel level, Villager v, CompoundTag t) {
        if (t.contains("shelter")) {
            BlockPos p = BlockPos.of(t.getLong("shelter"));
            if (p.distSqr(v.blockPosition()) <= 256 && covered(level,p)) return p;
            t.remove("shelter");
        }
        if (level.getGameTime() < t.getLong("scanAfter")) return null;
        t.putLong("scanAfter", level.getGameTime()+100);
        BlockPos best=null;
        for (BlockPos p : BlockPos.betweenClosed(v.blockPosition().offset(-8,-2,-8), v.blockPosition().offset(8,2,8))) {
            if (covered(level,p) && (best==null || p.distSqr(v.blockPosition())<best.distSqr(v.blockPosition()))) best=p.immutable();
        }
        if (best!=null) t.putLong("shelter",best.asLong());
        return best;
    }
    private static void trace(CompoundTag t, long now, String action, String outcome) {
        ListTag history=t.getList("history",10);
        CompoundTag e=new CompoundTag();
        e.putLong("tick",now); e.putString("action",action); e.putString("outcome",outcome);
        history.add(e); while(history.size()>32) history.remove(0);
        t.put("history",history);
    }
    public static void tick(ServerLevel level, Villager v) {
        CompoundTag t=v.getPersistentData().getCompound(KEY);
        if (!t.getBoolean("enabled") || v.tickCount%20!=0) return;
        long now=level.getGameTime();
        // No offline starvation or extra aging after reload; only bounded live time.
        double seconds=Math.min(20,Math.max(0,now-t.getLong("lastTick")))/20.0;
        t.putLong("lastTick",now);
        t.putDouble("food",SurvivalPolicy.metabolize(t.getDouble("food"),seconds));
        Monster threat=level.getEntitiesOfClass(Monster.class,v.getBoundingBox().inflate(12),
            m -> m.isAlive() && v.hasLineOfSight(m)).stream()
            .min(Comparator.comparingDouble(v::distanceToSqr)).orElse(null);
        int slot=foodSlot(v);
        ItemEntity forage=level.getEntitiesOfClass(ItemEntity.class,v.getBoundingBox().inflate(8),
            e -> e.isAlive() && !e.hasPickUpDelay() && nutrition(e.getItem())>0 && v.hasLineOfSight(e))
            .stream().min(Comparator.comparingDouble(v::distanceToSqr)).orElse(null);
        BlockPos roof=level.isNight()?shelter(level,v,t):null;
        CompoundTag instincts=CitizenInstincts.get(v);
        SurvivalPolicy.Action action=SurvivalPolicy.choose(new SurvivalPolicy.Observation(
            t.getDouble("food"), v.getHealth()/v.getMaxHealth(),slot>=0 || forage!=null,threat!=null,
            level.isNight(),roof!=null,instincts.getInt("food"),instincts.getInt("danger"),
            instincts.getInt("combat"),instincts.getInt("shelter")));
        String previous=t.getString("action");
        t.putString("action",action.name());
        String outcome="OBSERVED";
        switch(action) {
            case EAT -> {
                if (slot<0 && v.distanceToSqr(forage)>2.25) {
                    outcome=v.getNavigation().moveTo(forage,1.0)?"SEEK_VISIBLE_FOOD":"NO_FOOD_PATH";
                    break;
                }
                v.getNavigation().stop();
                ItemStack item=slot>=0?v.getInventory().getItem(slot):forage.getItem();
                int value=nutrition(item);
                ItemStack consumed=slot>=0?v.getInventory().removeItem(slot,1):item.split(1);
                if (slot<0 && item.isEmpty()) forage.discard();
                if (!consumed.isEmpty()) {
                    t.putDouble("food",Math.min(20,t.getDouble("food")+value));
                    t.putInt("meals",t.getInt("meals")+1);
                    outcome="CONSUMED_ONE_"+consumed.getItem().toString();
                }
            }
            case FLEE -> {
                Vec3 away=v.position().subtract(threat.position());
                if (away.lengthSqr()<.01) away=new Vec3(1,0,0);
                away=new Vec3(away.x,0,away.z).normalize().scale(8);
                outcome="NO_ESCAPE_PATH";
                for (int turn=0;turn<8;turn++) {
                    Vec3 offset=away.yRot((float)(turn*Math.PI/4));
                    BlockPos p=BlockPos.containing(v.position().add(offset));
                    if (!level.hasChunkAt(p)) continue;
                    var path=v.getNavigation().createPath(p,0);
                    if (path!=null && path.canReach() && v.getNavigation().moveTo(path,1.25)) {
                        outcome="ESCAPE_PATH"; break;
                    }
                }
                if (outcome.equals("NO_ESCAPE_PATH")) v.getNavigation().stop();
            }
            case DEFEND -> {
                if (v.distanceToSqr(threat)<=4 && v.hasLineOfSight(threat)) {
                    v.getNavigation().stop();
                    boolean hit=threat.hurt(level.damageSources().mobAttack(v),2f);
                    outcome=hit?"DAMAGE_CONFIRMED":"DAMAGE_REJECTED";
                    if(hit) t.putInt("hits",t.getInt("hits")+1);
                } else outcome=v.getNavigation().moveTo(threat,1.0)?"APPROACH_THREAT":"NO_ATTACK_PATH";
            }
            case SHELTER -> {
                if(v.blockPosition().distSqr(roof)<=2) {v.getNavigation().stop(); outcome="UNDER_COVER";}
                else outcome=v.getNavigation().moveTo(roof.getX()+.5,roof.getY(),roof.getZ()+.5,1.0)?"SEEK_COVER":"NO_SHELTER_PATH";
            }
            case WORK -> {if(!previous.equals("WORK")) v.getNavigation().stop(); outcome="WORK_RELEASED";}
        }
        t.putString("outcome",outcome);
        if(!previous.equals(action.name()) || action==SurvivalPolicy.Action.EAT || outcome.equals("DAMAGE_CONFIRMED"))
            trace(t,now,action.name(),outcome);
        if(t.getDouble("food")<=0 && now>=t.getLong("starveAfter")) {
            v.hurt(level.damageSources().starve(),1); t.putLong("starveAfter",now+80);
            trace(t,now,"STARVE","FOOD_EMPTY");
        }
    }
    public static String inspect(Villager v) {
        CompoundTag t=v.getPersistentData().getCompound(KEY);
        return "SURVIVAL policy=scripted-v1 enabled="+t.getBoolean("enabled")+" food="+t.getDouble("food")
            +" action="+t.getString("action")+" outcome="+t.getString("outcome")
            +" meals="+t.getInt("meals")+" hits="+t.getInt("hits")+" history="+t.getList("history",10);
    }
}
