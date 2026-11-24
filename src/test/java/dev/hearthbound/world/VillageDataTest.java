package dev.hearthbound.world;

import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.VillageWorkPolicy;
import dev.hearthbound.civilization.VillageWorkPolicy.Kind;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;

/** Real NBT codec contracts. No Minecraft physical behavior is simulated here. */
public final class VillageDataTest {
    static void check(boolean condition){if(!condition)throw new AssertionError();}
    static CompoundTag fixture(){
        var d=new VillageEconomyRuntime.Data();d.world=new UUID(0,101);d.enabled=true;d.draining=true;d.keepTicking=true;
        d.districts.add(VillageEconomyRuntime.District.at(0,new BlockPos(0,101,0)));
        UUID actor=new UUID(0,202);d.citizens.add(actor);var p=new VillageWorkPolicy(actor);
        p.learn(new VillageWorkPolicy.Outcome(new UUID(0,303),actor,Kind.HARVEST_REPLANT,List.of(1.,.25,1.,.5),10,210,.5,true,"native:test"));
        d.policies.put(actor,p);d.totals.put("wheat_harvested",1L);d.leases.put("crop:1",new UUID(0,404));
        return d.save(new CompoundTag());
    }
    public static void main(String[] args){
        var root=fixture();var loaded=VillageEconomyRuntime.Data.load(root);check(loaded.failure.isEmpty());
        check(!loaded.enabled&&!loaded.draining&&loaded.keepTicking);check(loaded.books.isEmpty()&&loaded.sent.isEmpty());
        check(loaded.policies.get(new UUID(0,202)).snapshot().size()==1);check(loaded.leases.size()==1);check(loaded.totals.get("wheat_harvested")==1);
        var again=VillageEconomyRuntime.Data.load(loaded.save(new CompoundTag()));check(again.failure.isEmpty());
        check(again.policies.get(new UUID(0,202)).snapshot().equals(loaded.policies.get(new UUID(0,202)).snapshot()));
        root=fixture();root.putInt("foodTarget",-1);check(!VillageEconomyRuntime.Data.load(root).failure.isEmpty());
        root=fixture();ServiceJsonPayload.write(root,"districts","[{}]");check(!VillageEconomyRuntime.Data.load(root).failure.isEmpty());
        root=fixture();var owners=root.getList("citizens",10);owners.add(owners.getCompound(0).copy());check(!VillageEconomyRuntime.Data.load(root).failure.isEmpty());
        root=fixture();ServiceJsonPayload.write(root,"records","[{\"sequence\":2}]");var bad=VillageEconomyRuntime.Data.load(root);check(!bad.failure.isEmpty());
        var fenced=VillageEconomyRuntime.Data.load(bad.save(new CompoundTag()));check(fenced.failure.equals(bad.failure));check(!fenced.enabled);
        System.out.println("PASS VillageDataTest: native NBT replay, stopped reload, retained leases, private cache reset, corruption fence");
    }
}
