package dev.hearthbound.world;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import dev.hearthbound.civilization.VillageWorkPolicy;
import dev.hearthbound.civilization.VillageWorkPolicy.Kind;
import dev.hearthbound.civilization.VillageWorkPolicy.Offer;
import java.util.*;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.saveddata.SavedData;

/** Renewable food economy: private observations -> contextual choice -> native skill.
 * All citizens have every capability. No role quotas or shared actor stock board.
 * Knowledge exchange is an authored local protocol; cost learning is private RLS.
 */
public final class VillageEconomyRuntime {
    static final String KEY="hearthbound.village_economy.v0_23", STORE="hearthbound_village_economy_v0_23";
    static final String WHEAT="minecraft:wheat", SEED="minecraft:wheat_seeds", FLOUR="create:wheat_flour",
        DOUGH="create:dough", BREAD="minecraft:bread", WATER="minecraft:water_bucket", BUCKET="minecraft:bucket";
    static final Gson GSON=new Gson(); static final int MAX_RECORDS=32768, MAX_CITIZENS=16;
    static final long TTL=600; static final double SENSOR=16, CONTACT=12;
    private static final String[] NAMES={"Aster","Bram","Cora","Dax","Eira","Finn","Gale","Hana","Iris","Jory","Kira","Lio","Mira","Nell","Orin","Pia"};
    private VillageEconomyRuntime(){}
    record District(int index,long origin,long depot,long mill,long flour,long water,long table,long dough,long furnace,long pantry,long well,List<Long> crops){
        static District at(int index,BlockPos p){return new District(index,p.asLong(),p.offset(10,0,5).asLong(),p.offset(18,0,5).asLong(),
            p.offset(25,0,5).asLong(),p.offset(26,0,8).asLong(),p.offset(29,0,5).asLong(),p.offset(32,0,5).asLong(),
            p.offset(36,0,5).asLong(),p.offset(42,0,5).asLong(),p.offset(26,-1,10).asLong(),
            List.of(p.offset(5,0,9).asLong(),p.offset(6,0,9).asLong(),p.offset(5,0,10).asLong(),p.offset(6,0,10).asLong()));}
        List<Long> observed(){var nodes=new ArrayList<>(List.of(depot,flour,water,dough,furnace,pantry,well));nodes.addAll(crops);return nodes;}
    }
    record Fact(UUID id,UUID observer,long tick,long position,Map<String,Integer> items,boolean mature,boolean water){
        Fact {items=Map.copyOf(items);}
    }
    record Known(Fact fact,UUID packet,UUID sender,int hops){}
    static final class Data extends SavedData {
        final List<District> districts=new ArrayList<>(); final Set<UUID> citizens=new LinkedHashSet<>();
        final Map<UUID,VillageWorkPolicy> policies=new LinkedHashMap<>();
        final Map<UUID,Map<Long,Known>> books=new LinkedHashMap<>();
        final Map<UUID,LinkedHashSet<String>> sent=new LinkedHashMap<>();
        final Map<UUID,Map<String,Long>> cooldowns=new LinkedHashMap<>();
        final Map<String,UUID> leases=new LinkedHashMap<>();
        final List<JsonObject> records=new ArrayList<>();final Map<String,Long> totals=new LinkedHashMap<>();
        UUID session=UUID.randomUUID(); UUID world; boolean enabled,draining,keepTicking,adaptive=true; int foodTarget=6;
        String failure="";
        CompoundTag rejectedSnapshot;
        static Data load(CompoundTag root){Data d=new Data();try{
            if(root.getInt("schema")!=1||!root.hasUUID("world"))throw new IllegalStateException("Unknown village save");
            d.world=root.getUUID("world");d.adaptive=root.getBoolean("adaptive");d.keepTicking=root.getBoolean("keepTicking");d.foodTarget=root.getInt("foodTarget");
            if(!root.getString("failure").isEmpty()){d.failure=root.getString("failure");d.rejectedSnapshot=root.copy();return d;}
            if(d.foodTarget<0||d.foodTarget>64)throw new IllegalStateException("Invalid target");
            District[] districts=GSON.fromJson(ServiceJsonPayload.read(root,"districts"),District[].class);
            if(districts==null||districts.length>4)throw new IllegalStateException("Invalid districts");
            Set<Long> nodes=new HashSet<>();for(int i=0;i<districts.length;i++){
                District site=districts[i];if(site==null||!site.equals(District.at(i,BlockPos.of(site.origin)))
                    ||site.observed().stream().anyMatch(p->!nodes.add(p)))throw new IllegalStateException("Invalid/overlapping district geometry");
                d.districts.add(site);
            }
            ListTag owners=root.getList("citizens",Tag.TAG_COMPOUND);if(owners.size()>MAX_CITIZENS)throw new IllegalStateException("Too many citizens");
            for(int i=0;i<owners.size();i++){CompoundTag c=owners.getCompound(i);UUID id=c.getUUID("citizen");if(!d.citizens.add(id))throw new IllegalStateException("Duplicate citizen");
                var outcomes=GSON.fromJson(ServiceJsonPayload.read(c,"outcomes"),VillageWorkPolicy.Outcome[].class);
                d.policies.put(id,VillageWorkPolicy.restore(id,List.of(outcomes)));}
            JsonArray rows=GSON.fromJson(ServiceJsonPayload.read(root,"records"),JsonArray.class);
            if(rows==null||rows.size()>MAX_RECORDS)throw new IllegalStateException("Invalid evidence");for(var row:rows)d.records.add(row.getAsJsonObject());
            for(int i=0;i<d.records.size();i++){JsonObject row=d.records.get(i);
                if(row.get("sequence").getAsInt()!=i+1||!row.get("world").getAsString().equals(d.world.toString())
                    ||row.get("tick").getAsLong()<0||row.get("type").getAsString().isBlank()
                    ||(row.has("citizen")&&!d.citizens.contains(UUID.fromString(row.get("citizen").getAsString()))))throw new IllegalStateException("Evidence identity/gap");
                UUID.fromString(row.get("session").getAsString());
            }
            CompoundTag totals=root.getCompound("totals");for(String k:totals.getAllKeys()){long n=totals.getLong(k);if(n<0)throw new IllegalStateException("Negative total");d.totals.put(k,n);}
            CompoundTag leases=root.getCompound("leases");if(leases.getAllKeys().size()>MAX_CITIZENS*2)throw new IllegalStateException("Lease bound");for(String k:leases.getAllKeys())d.leases.put(k,leases.getUUID(k));
        }catch(RuntimeException bad){d.failure="PERSISTENCE_REQUIRES_REVIEW: "+bad.getMessage();d.rejectedSnapshot=root.copy();}return d;}
        @Override public CompoundTag save(CompoundTag root){
            if(rejectedSnapshot!=null){CompoundTag retained=rejectedSnapshot.copy();retained.putString("failure",failure);return retained;}
            root.putInt("schema",1);root.putUUID("world",world);root.putBoolean("adaptive",adaptive);root.putInt("foodTarget",foodTarget);
            root.putString("failure",failure);root.putBoolean("keepTicking",keepTicking);
            ServiceJsonPayload.write(root,"districts",GSON.toJson(districts));ServiceJsonPayload.write(root,"records",GSON.toJson(records));
            ListTag owners=new ListTag();for(UUID id:citizens){CompoundTag c=new CompoundTag();c.putUUID("citizen",id);ServiceJsonPayload.write(c,"outcomes",GSON.toJson(policies.get(id).snapshot()));owners.add(c);}root.put("citizens",owners);
            CompoundTag totals=new CompoundTag();this.totals.forEach(totals::putLong);root.put("totals",totals);
            CompoundTag leases=new CompoundTag();this.leases.forEach(leases::putUUID);root.put("leases",leases);return root;}
        void count(String k,long n){totals.merge(k,n,Long::sum);setDirty();}
    }
    static Data data(ServerLevel level){Data d=level.getDataStorage().computeIfAbsent(Data::load,Data::new,STORE);UUID world=HearthboundWorldIdentity.get(level);
        if(d.world==null)d.world=world;else if(!d.world.equals(world))d.failure="FOREIGN_WORLD";return d;}
    static Scope scope(Data d,ServerLevel level){return new Scope(d.world,level.dimension().location().toString());}
    static CompoundTag memory(Villager v){return v.getPersistentData().getCompound(KEY);}
    public static boolean controls(Villager v){return v.getPersistentData().getCompound(KEY).getBoolean("enrolled");}
    static void stopMotion(Villager v){v.getNavigation().stop();v.setNoAi(true);}
    static boolean go(Villager v,BlockPos p){if(VillageInventory.distance(v,p)<=2.5){stopMotion(v);return true;}v.setNoAi(false);v.getNavigation().moveTo(p.getX()+.5,p.getY(),p.getZ()+.5,.85);return false;}
    static JsonObject event(Data d,ServerLevel level,String type,Villager v){
        if(d.records.size()>=MAX_RECORDS)throw new IllegalStateException("Village evidence capacity exhausted");
        JsonObject r=new JsonObject();r.addProperty("sequence",d.records.size()+1);r.addProperty("type",type);r.addProperty("tick",level.getGameTime());
        r.addProperty("world",d.world.toString());r.addProperty("session",d.session.toString());r.addProperty("policy",d.adaptive?"PRIVATE_RECIPE_COST_RLS_V1":"AUTHORED_RECIPE_UTILITY_V1");
        if(v!=null){r.addProperty("citizen",v.getUUID().toString());r.addProperty("x",v.getX());r.addProperty("y",v.getY());r.addProperty("z",v.getZ());
            CompoundTag m=memory(v);if(m.hasUUID("optionId"))r.addProperty("job",m.getUUID("optionId").toString());
            if(m.hasUUID("job")&&!m.getUUID("job").equals(m.getUUID("optionId")))r.addProperty("native_job",m.getUUID("job").toString());
            r.addProperty("kind",m.getString("kind"));r.addProperty("phase",m.getString("phase"));}
        d.records.add(r);d.setDirty();return r;
    }
    static void witness(Data d,ServerLevel level,Villager v,String type,Map<String,?> values){JsonObject r=event(d,level,type,v);values.forEach((k,value)->r.add(k,GSON.toJsonTree(value)));}
    static void hold(Data d,ServerLevel level,Villager v,String reason){CompoundTag m=memory(v);if(!"HELD".equals(m.getString("phase"))){event(d,level,"WORK_HELD",v).addProperty("reason",reason);m.putString("phase","HELD");m.putString("reason",reason);}stopMotion(v);d.setDirty();}
    static void track(Villager v){CompoundTag m=memory(v);if(!m.getBoolean("active"))return;double dx=v.getX()-m.getDouble("lastX"),dy=v.getY()-m.getDouble("lastY"),dz=v.getZ()-m.getDouble("lastZ");m.putDouble("travel",m.getDouble("travel")+Math.sqrt(dx*dx+dy*dy+dz*dz));m.putDouble("lastX",v.getX());m.putDouble("lastY",v.getY());m.putDouble("lastZ",v.getZ());}
    static void settle(Data d,ServerLevel level,Villager v,boolean completed,String receipt,String reason){
        CompoundTag m=memory(v);if(!m.getBoolean("active"))throw new IllegalStateException("No active owned work");
        if(m.contains("cargo")||m.contains(ServiceProductionBridge.CARGO)||SableHauling.active(v))throw new IllegalStateException("Unresolved custody cannot settle");
        Offer offer=GSON.fromJson(m.getString("offer"),Offer.class);long now=level.getGameTime();
        double cost=.01*m.getDouble("travel")+.02*m.getInt("packets");var xs=Arrays.stream(offer.features()).boxed().toList();
        var outcome=new VillageWorkPolicy.Outcome(m.getUUID("optionId"),v.getUUID(),offer.kind(),xs,m.getLong("started"),now,cost,completed,receipt);
        d.policies.get(v.getUUID()).learn(outcome);JsonObject row=event(d,level,"WORK_SETTLED",v);row.add("outcome",GSON.toJsonTree(outcome));row.addProperty("reason",reason);
        row.addProperty("private_samples",d.policies.get(v.getUUID()).snapshot().size());row.addProperty("travel",m.getDouble("travel"));row.addProperty("packets",m.getInt("packets"));
        UUID job=m.getUUID("optionId");d.leases.entrySet().removeIf(e->e.getValue().equals(job));m.putBoolean("active",false);m.putString("phase","IDLE");m.putLong("until",now+(completed?20:60));
        if(!completed)d.cooldowns.computeIfAbsent(v.getUUID(),x->new HashMap<>()).put(offer.id(),now+100);
        m.remove("reason");v.setCustomName(Component.literal(m.getString("name")+" · idle"));stopMotion(v);d.setDirty();
    }
    static Map<Long,Known> book(Data d,UUID id){return d.books.computeIfAbsent(id,x->new LinkedHashMap<>());}
    static Known known(Data d,UUID id,long p,long now){Known k=book(d,id).get(p);return k!=null&&now>=k.fact.tick&&now-k.fact.tick<=TTL?k:null;}
    static int amount(Known k,String item){return k==null?-1:k.fact.items.getOrDefault(item,0);}
    static String evidence(Known... facts){return Arrays.stream(facts).filter(Objects::nonNull).map(k->k.fact.id.toString()).distinct().sorted().reduce((a,b)->a+","+b).orElse("");}
    static void sense(Data d,ServerLevel level,Villager v){long now=level.getGameTime();var own=book(d,v.getUUID());
        for(District district:d.districts)for(long node:district.observed()){
            BlockPos p=BlockPos.of(node);if(!level.hasChunkAt(p)||VillageInventory.distance(v,p)>SENSOR)continue;
            Map<String,Integer> items=Map.of();boolean mature=false,water=false;
            if(district.crops.contains(node)){var state=level.getBlockState(p);mature=state.is(Blocks.WHEAT)&&((CropBlock)state.getBlock()).isMaxAge(state);}
            else if(node==district.well){var fluid=level.getFluidState(p);water=fluid.isSource()&&fluid.is(net.minecraft.tags.FluidTags.WATER);}
            else if(level.getBlockEntity(p) instanceof net.minecraft.world.Container c)items=VillageInventory.contents(c);else continue;
            Known before=own.get(node);if(before!=null&&before.packet==null&&before.fact.items.equals(items)&&before.fact.mature==mature&&before.fact.water==water&&now-before.fact.tick<100)continue;
            Fact fact=new Fact(UUID.randomUUID(),v.getUUID(),now,node,items,mature,water);own.put(node,new Known(fact,null,v.getUUID(),0));event(d,level,"LOCAL_OBSERVATION",v).add("fact",GSON.toJsonTree(fact));
        }
    }
    static void exchange(Data d,ServerLevel level,Villager v){CompoundTag m=memory(v);long now=level.getGameTime();if(now<m.getLong("nextExchange"))return;m.putLong("nextExchange",now+100);
        var peers=level.getEntitiesOfClass(Villager.class,v.getBoundingBox().inflate(CONTACT),p->!p.getUUID().equals(v.getUUID())&&d.citizens.contains(p.getUUID())&&controls(p)&&p.isAlive()&&v.distanceToSqr(p)<=CONTACT*CONTACT);
        peers.sort(Comparator.comparing(p->p.getUUID().toString()));int sent=0;
        var journal=d.sent.computeIfAbsent(v.getUUID(),x->new LinkedHashSet<>());
        for(Villager peer:peers){if(sent>=2)break;List<Known> bundle=book(d,v.getUUID()).values().stream().filter(k->now-k.fact.tick<=TTL&&k.hops<2&&!journal.contains(peer.getUUID()+"|"+k.fact.id))
                .sorted(Comparator.comparingLong((Known k)->-k.fact.tick).thenComparing(k->k.fact.id.toString())).limit(8).toList();if(bundle.isEmpty())continue;
            UUID packet=UUID.randomUUID();JsonObject send=event(d,level,"FACTS_SENT",v);send.addProperty("packet",packet.toString());send.addProperty("recipient",peer.getUUID().toString());send.addProperty("distance",Math.sqrt(v.distanceToSqr(peer)));send.add("facts",GSON.toJsonTree(bundle));
            JsonArray accepted=new JsonArray(),rejected=new JsonArray();var target=book(d,peer.getUUID());
            for(Known k:bundle){journal.add(peer.getUUID()+"|"+k.fact.id);Known prior=target.get(k.fact.position);if(prior==null||prior.fact.tick<k.fact.tick){target.put(k.fact.position,new Known(k.fact,packet,v.getUUID(),k.hops+1));accepted.add(k.fact.id.toString());}else rejected.add(k.fact.id.toString());}
            JsonObject receive=event(d,level,"FACTS_RECEIVED",peer);receive.addProperty("packet",packet.toString());receive.addProperty("sender",v.getUUID().toString());receive.add("accepted",accepted);receive.add("rejected",rejected);
            while(journal.size()>2048)journal.remove(journal.iterator().next());if(m.getBoolean("active"))m.putInt("packets",m.getInt("packets")+1);d.count("packets",1);sent++;
        }
    }
    private static void add(List<Offer> out,Villager v,Kind k,District d,long auxiliary,double distance,double deficit,Known...facts){
        double age=Arrays.stream(facts).filter(Objects::nonNull).mapToDouble(f->Math.max(0,v.level().getGameTime()-f.fact.tick)/(double)TTL).max().orElse(0);
        out.add(new Offer(k+":"+d.index+":"+auxiliary,v.getUUID(),k,distance,Math.max(0,Math.min(1,deficit)),Math.min(1,age),
            (100-memory(v).getDouble("satiety"))/100,evidence(facts),d.index,auxiliary));
    }
    static List<Offer> menu(Data d,ServerLevel level,Villager v){long now=level.getGameTime();var out=new ArrayList<Offer>();
        if(d.foodTarget>0)for(District district:d.districts){
            Known depot=known(d,v.getUUID(),district.depot,now),flour=known(d,v.getUUID(),district.flour,now),water=known(d,v.getUUID(),district.water,now),
                dough=known(d,v.getUUID(),district.dough,now),pantry=known(d,v.getUUID(),district.pantry,now),well=known(d,v.getUUID(),district.well,now);
            if(depot!=null&&amount(depot,WHEAT)<4&&amount(depot,SEED)>0)for(long plot:district.crops){Known crop=known(d,v.getUUID(),plot,now);if(crop!=null&&crop.fact.mature)
                add(out,v,Kind.HARVEST_REPLANT,district,plot,route(v,district.depot,plot,district.depot),(4-amount(depot,WHEAT))/4.,depot,crop);}
            if(amount(depot,WHEAT)>0&&flour!=null&&amount(flour,FLOUR)<4)add(out,v,Kind.MILL_FLOUR,district,0,route(v,district.depot,district.mill,district.flour),(4-amount(flour,FLOUR))/4.,depot,flour);
            if(amount(flour,FLOUR)>0&&amount(water,WATER)>0&&dough!=null&&amount(dough,DOUGH)<4)add(out,v,Kind.PREPARE_DOUGH,district,0,route(v,district.flour,district.water,district.table,district.water,district.dough),(4-amount(dough,DOUGH))/4.,flour,water,dough);
            if(amount(dough,DOUGH)>0&&pantry!=null&&amount(pantry,BREAD)<d.foodTarget)add(out,v,Kind.BAKE_BREAD,district,0,route(v,district.dough,district.furnace,district.pantry),(d.foodTarget-amount(pantry,BREAD))/(double)d.foodTarget,dough,pantry);
            if(water!=null&&amount(water,WATER)<4&&amount(water,BUCKET)>0&&well!=null&&well.fact.water)add(out,v,Kind.REFILL_WATER,district,0,route(v,district.water,district.well,district.water),(4-amount(water,WATER))/4.,water,well);
            if(amount(pantry,BREAD)>0&&memory(v).getDouble("satiety")<40)add(out,v,Kind.EAT_BREAD,district,0,route(v,district.pantry),1,pantry);
            for(long node:district.observed()){Known k=known(d,v.getUUID(),node,now);if(k==null)add(out,v,Kind.OBSERVE,district,node,Math.max(0,VillageInventory.distance(v,BlockPos.of(node))-14),1);}
        }
        out.removeIf(o->d.cooldowns.getOrDefault(v.getUUID(),Map.of()).getOrDefault(o.id(),0L)>now);
        out.add(new Offer("WAIT",v.getUUID(),Kind.WAIT,0,0,0,(100-memory(v).getDouble("satiety"))/100,"",0,0));out.sort(Comparator.comparing(Offer::id));return out;
    }
    static double route(Villager v,long...nodes){double distance=0;double x=v.getX(),y=v.getY(),z=v.getZ();for(long n:nodes){BlockPos p=BlockPos.of(n);distance+=Math.sqrt((p.getX()+.5-x)*(p.getX()+.5-x)+(p.getY()+.5-y)*(p.getY()+.5-y)+(p.getZ()+.5-z)*(p.getZ()+.5-z));x=p.getX()+.5;y=p.getY()+.5;z=p.getZ()+.5;}return distance;}
    static District district(Data d,CompoundTag m){int index=m.getInt("district");return d.districts.stream().filter(x->x.index==index).findFirst().orElseThrow();}
    static List<String> locks(Offer o,District s){return switch(o.kind()){
        case HARVEST_REPLANT->List.of("crop:"+o.auxiliary(),"wheat:"+s.depot);
        case MILL_FLOUR->List.of("flour:"+s.flour);
        case PREPARE_DOUGH->List.of("table:"+s.table,"dough:"+s.dough);
        case BAKE_BREAD->List.of("furnace:"+s.furnace,"bread:"+s.pantry);
        case REFILL_WATER->List.of("water:"+s.water);
        default->List.of();};}
    static void choose(Data d,ServerLevel level,Villager v){var menu=menu(d,level,v);var model=d.policies.get(v.getUUID());Offer chosen=model.choose(menu,d.adaptive);
        JsonObject decision=event(d,level,"WORK_DECISION",v);decision.add("offers",GSON.toJsonTree(menu));decision.add("scores",GSON.toJsonTree(menu.stream().map(o->model.score(o,d.adaptive)).toList()));decision.addProperty("selected",chosen.id());
        CompoundTag m=memory(v);UUID id=UUID.randomUUID();m.putBoolean("active",true);m.putUUID("optionId",id);m.putUUID("job",id);m.putUUID("commitment",id);m.putUUID("session",d.session);
        m.putString("kind",chosen.kind().name());m.putString("phase","START");m.putLong("started",level.getGameTime());m.putLong("until",level.getGameTime()+40);m.putLong("auxiliary",chosen.auxiliary());m.putInt("district",(int)chosen.site());
        m.putString("offer",GSON.toJson(chosen));m.putDouble("lastX",v.getX());m.putDouble("lastY",v.getY());m.putDouble("lastZ",v.getZ());m.putDouble("travel",0);m.putInt("packets",0);m.remove("reason");
        m.remove(ServiceProductionBridge.PHASE);m.remove(ServiceProductionBridge.CARGO);m.remove("cargo");
        event(d,level,"WORK_STARTED",v).add("offer",GSON.toJsonTree(chosen));v.setCustomName(Component.literal(m.getString("name")+" · "+chosen.kind().name().toLowerCase(Locale.ROOT).replace('_',' ')));
        if(chosen.kind()==Kind.WAIT||chosen.kind()==Kind.OBSERVE)return;
        var locks=locks(chosen,district(d,m));if(locks.stream().anyMatch(d.leases::containsKey)){settle(d,level,v,false,"","RESOURCE_RESERVED");return;}locks.forEach(k->d.leases.put(k,id));d.setDirty();
    }
    static boolean tick(ServerLevel level,Villager v){if(!controls(v))return false;Data d=data(level);CompoundTag m=memory(v);
        if(!d.failure.isEmpty()||!d.citizens.contains(v.getUUID())){stopMotion(v);return true;}
        if(m.getBoolean("active")&&(!m.hasUUID("session")||!m.getUUID("session").equals(d.session))){hold(d,level,v,"RESTORED_WORK_REQUIRES_REVIEW");return true;}
        if("HELD".equals(m.getString("phase"))){stopMotion(v);return true;}
        if(!d.enabled&&!d.draining){stopMotion(v);return true;}
        MillExperimentTrace.monitorAuthorizedInput(level,v);MillExperimentTrace.sampleCycle(level,v);
        if(v.tickCount%20!=0)return true;
        try{
            track(v);long now=level.getGameTime();long previous=m.getLong("metabolismTick");if(previous==0)previous=now;
            m.putDouble("satiety",Math.max(0,m.getDouble("satiety")-(now-previous)/100.));m.putLong("metabolismTick",now);
            if(d.records.size()>MAX_RECORDS-128){d.enabled=false;d.draining=false;hold(d,level,v,"EVIDENCE_CAPACITY_EXHAUSTED");return true;}
            if(d.enabled){sense(d,level,v);exchange(d,level,v);}
            if(m.getBoolean("active")){VillageWorkActions.tick(d,level,v);return true;}
            if(SableHauling.active(v)||m.contains("cargo")||m.contains(ServiceProductionBridge.CARGO)){hold(d,level,v,"ORPHANED_CUSTODY");return true;}
            if(d.draining){stopMotion(v);return true;}
            if(now>=m.getLong("until"))choose(d,level,v);
        }catch(RuntimeException invalid){hold(d,level,v,"WORK_BOUNDARY: "+invalid.getClass().getSimpleName()+": "+invalid.getMessage());}return true;
    }
    public static void register(CommandDispatcher<CommandSourceStack> dispatcher){dispatcher.register(Commands.literal("hearthbound-village").requires(s->s.hasPermission(2))
        .then(Commands.literal("district").then(Commands.argument("origin",BlockPosArgument.blockPos()).executes(c->configure(c.getSource(),BlockPosArgument.getBlockPos(c,"origin")))))
        .then(Commands.literal("enroll").then(Commands.argument("citizen",EntityArgument.entity()).executes(c->{var e=EntityArgument.getEntity(c,"citizen");return e instanceof Villager v?enroll(c.getSource(),v):fail(c.getSource(),"Requires a Sable citizen");})))
        .then(Commands.literal("policy").then(Commands.literal("adaptive").executes(c->policy(c.getSource(),true))).then(Commands.literal("authored").executes(c->policy(c.getSource(),false))))
        .then(Commands.literal("keep-ticking").then(Commands.literal("on").executes(c->keepTicking(c.getSource(),true))).then(Commands.literal("off").executes(c->keepTicking(c.getSource(),false))))
        .then(Commands.literal("target").then(Commands.argument("bread",IntegerArgumentType.integer(0,64)).executes(c->{Data d=data(c.getSource().getLevel());d.foodTarget=IntegerArgumentType.getInteger(c,"bread");event(d,c.getSource().getLevel(),"FOOD_TARGET_SET",null).addProperty("target",d.foodTarget);return okay(c.getSource(),"Bread target="+d.foodTarget);})))
        .then(Commands.literal("start").executes(c->start(c.getSource())))
        .then(Commands.literal("drain").executes(c->{Data d=data(c.getSource().getLevel());d.enabled=false;d.draining=true;event(d,c.getSource().getLevel(),"VILLAGE_DRAIN",null);return okay(c.getSource(),"New work stopped; current owned services drain");}))
        .then(Commands.literal("stop").executes(c->stop(c.getSource())))
        .then(Commands.literal("status").executes(c->status(c.getSource())))
        .then(Commands.literal("records").then(Commands.argument("offset",IntegerArgumentType.integer(0)).executes(c->records(c.getSource(),IntegerArgumentType.getInteger(c,"offset"))))));}
    static int fail(CommandSourceStack s,String reason){s.sendFailure(Component.literal("VILLAGE_DENIED "+reason));return 0;}
    static int okay(CommandSourceStack s,String message){s.sendSuccess(()->Component.literal("VILLAGE_OK "+message),false);return 1;}
    private static boolean unresolved(Data d,ServerLevel level){
        if(!d.failure.isEmpty()||!d.leases.isEmpty())return true;
        for(UUID id:d.citizens){if(!(level.getEntity(id)instanceof Villager v))return true;CompoundTag m=memory(v);
            if(m.getBoolean("active")||"HELD".equals(m.getString("phase"))||m.contains("cargo")||m.contains(ServiceProductionBridge.CARGO)||SableHauling.active(v))return true;
        }return false;
    }
    private static int configure(CommandSourceStack s,BlockPos origin){Data d=data(s.getLevel());if(d.enabled||d.draining||unresolved(d,s.getLevel())||d.districts.size()>=4)return fail(s,"Stop and reconcile before configuring at most four districts");
        District district=District.at(d.districts.size(),origin);for(var old:d.districts)if(old.observed().stream().anyMatch(district.observed()::contains))return fail(s,"District overlap");
        for(long p:List.of(district.depot,district.flour,district.water,district.dough,district.furnace,district.pantry))VillageInventory.container(s.getLevel(),BlockPos.of(p));
        if(!MillReservations.isMill(s.getLevel(),BlockPos.of(district.mill))||!s.getLevel().getBlockState(BlockPos.of(district.table)).is(Blocks.CRAFTING_TABLE))return fail(s,"Loaded mill and crafting table required");
        d.districts.add(district);if(d.keepTicking)tickTickets(s.getLevel(),district,true);event(d,s.getLevel(),"DISTRICT_CONFIGURED",null).add("district",GSON.toJsonTree(district));return okay(s,"Public district geometry configured; stock remains private");}
    private static void tickTickets(ServerLevel level,District site,boolean add){
        BlockPos origin=BlockPos.of(site.origin);
        // Bounded public geometry: at most 4 x 2 chunks per district. Forge's
        // forceTicks flag runs native random/block/entity ticks without players.
        for(int x=origin.getX()>>4;x<=((origin.getX()+43)>>4);x++)for(int z=origin.getZ()>>4;z<=((origin.getZ()+12)>>4);z++)
            net.minecraftforge.common.world.ForgeChunkManager.forceChunk(level,"hearthbound",origin,x,z,add,true);
    }
    private static int keepTicking(CommandSourceStack s,boolean enabled){Data d=data(s.getLevel());
        if(d.enabled||d.draining||unresolved(d,s.getLevel()))return fail(s,"Stop and resolve work before changing tick ownership");
        for(District site:d.districts)tickTickets(s.getLevel(),site,enabled);d.keepTicking=enabled;
        event(d,s.getLevel(),"DISTRICT_TICKING_CONFIGURED",null).addProperty("enabled",enabled);return okay(s,"Native district ticking="+enabled);
    }
    private static int enroll(CommandSourceStack s,Villager v){Data d=data(s.getLevel());if(d.enabled||d.draining||d.citizens.size()>=MAX_CITIZENS||v.level()!=s.getLevel())return fail(s,"Stop before enrollment; capacity sixteen");
        if(!d.failure.isEmpty()||!v.isAlive()||v.getPersistentData().contains(KEY)||!v.getPersistentData().getBoolean("hearthbound.sable")||NeedServiceRuntime.controls(v)||PrivateCommunicationTrial.controls(v)||SableHauling.active(v)||v.getPersistentData().contains("hearthbound.civilization.v1"))return fail(s,"Citizen has existing ownership or native work");
        if(!d.citizens.add(v.getUUID()))return fail(s,"Citizen already enrolled");d.policies.put(v.getUUID(),new VillageWorkPolicy(v.getUUID()));CompoundTag m=new CompoundTag();m.putBoolean("enrolled",true);m.putString("name",NAMES[d.citizens.size()-1]);m.putDouble("satiety",70);m.putString("phase","IDLE");v.getPersistentData().put(KEY,m);v.setCustomName(Component.literal(m.getString("name")));v.setCustomNameVisible(true);v.setPersistenceRequired();stopMotion(v);event(d,s.getLevel(),"VILLAGER_ENROLLED",v);return okay(s,"Citizen enrolled with every village capability");}
    private static int policy(CommandSourceStack s,boolean adaptive){Data d=data(s.getLevel());if(d.enabled||d.draining||unresolved(d,s.getLevel()))return fail(s,"Stop and resolve work before policy change");d.adaptive=adaptive;event(d,s.getLevel(),"POLICY_CONFIGURED",null);return okay(s,"Selector="+(adaptive?"private contextual cost learning":"authored utility control"));}
    private static int start(CommandSourceStack s){Data d=data(s.getLevel());if(!d.failure.isEmpty()||d.enabled||d.draining||!d.leases.isEmpty()||d.districts.isEmpty()||d.citizens.isEmpty()||CivilizationRuntime.enabled(s.getLevel()))return fail(s,"Village cannot start with unresolved work, missing setup or competing dispatch: "+d.failure);
        for(UUID id:d.citizens){if(!(s.getLevel().getEntity(id)instanceof Villager v)||!v.isAlive()||memory(v).getBoolean("active")||SableHauling.active(v)||memory(v).contains("cargo"))return fail(s,"Every citizen must be loaded and free of unresolved custody");}
        d.session=UUID.randomUUID();d.books.clear();d.sent.clear();d.cooldowns.clear();d.enabled=true;
        for(UUID id:d.citizens){Villager v=(Villager)s.getLevel().getEntity(id);CompoundTag m=memory(v);m.putLong("metabolismTick",s.getLevel().getGameTime());m.putLong("nextExchange",0);m.putString("phase","IDLE");}
        event(d,s.getLevel(),"VILLAGE_STARTED",null);return okay(s,"Private village work enabled");}
    private static int stop(CommandSourceStack s){Data d=data(s.getLevel());d.enabled=false;d.draining=false;for(UUID id:d.citizens)if(s.getLevel().getEntity(id)instanceof Villager v){
        CompoundTag m=memory(v);if(m.getBoolean("active")){
            if((m.getString("kind").equals("WAIT")||m.getString("kind").equals("OBSERVE"))&&!m.contains("cargo")&&!m.contains(ServiceProductionBridge.CARGO)&&!SableHauling.active(v))settle(d,s.getLevel(),v,false,"","OPERATOR_CANCELLED_NONMATERIAL_OPTION");
            else hold(d,s.getLevel(),v,"OPERATOR_STOP_WITH_OWNED_WORK");
        }else stopMotion(v);
    }event(d,s.getLevel(),"VILLAGE_STOPPED",null);return okay(s,"Stopped; unfinished ownership retained");}
    private static String digest(VillageWorkPolicy model){try{return HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(GSON.toJson(model.snapshot()).getBytes(java.nio.charset.StandardCharsets.UTF_8)));}catch(java.security.NoSuchAlgorithmException e){throw new IllegalStateException(e);}}
    private static int status(CommandSourceStack s){Data d=data(s.getLevel());JsonObject r=new JsonObject();r.addProperty("schema",VillageWorkPolicy.SCHEMA);r.addProperty("enabled",d.enabled);r.addProperty("draining",d.draining);r.addProperty("keep_ticking",d.keepTicking);r.addProperty("failure",d.failure);r.addProperty("adaptive",d.adaptive);r.addProperty("food_target",d.foodTarget);r.addProperty("records_total",d.records.size());r.add("totals",GSON.toJsonTree(d.totals));r.add("leases",GSON.toJsonTree(d.leases));r.add("districts",GSON.toJsonTree(d.districts));JsonArray citizens=new JsonArray();int active=0,held=0;
        for(UUID id:d.citizens){JsonObject c=new JsonObject();c.addProperty("citizen",id.toString());c.addProperty("samples",d.policies.get(id).snapshot().size());c.addProperty("learning_digest",digest(d.policies.get(id)));
            if(s.getLevel().getEntity(id)instanceof Villager v){CompoundTag m=memory(v);c.addProperty("loaded",true);c.addProperty("alive",v.isAlive());c.addProperty("name",m.getString("name"));c.addProperty("phase",m.getString("phase"));c.addProperty("kind",m.getString("kind"));c.addProperty("satiety",m.getDouble("satiety"));c.addProperty("active",m.getBoolean("active"));c.addProperty("reason",m.getString("reason"));c.add("cargo",GSON.toJsonTree(VillageInventory.cargoContents(m)));if(m.getBoolean("active"))active++;if("HELD".equals(m.getString("phase")))held++;}else c.addProperty("loaded",false);citizens.add(c);}
        r.addProperty("active",active);r.addProperty("held",held);r.add("citizens",citizens);s.sendSuccess(()->Component.literal("VILLAGE_STATUS "+GSON.toJson(r)),false);return d.failure.isEmpty()?1:0;}
    private static int records(CommandSourceStack s,int offset){Data d=data(s.getLevel());JsonObject r=new JsonObject();JsonArray rows=new JsonArray();for(int i=offset;i<Math.min(d.records.size(),offset+16);i++)rows.add(d.records.get(i));r.addProperty("offset",offset);r.addProperty("total",d.records.size());r.add("records",rows);s.sendSuccess(()->Component.literal("VILLAGE_RECORDS "+GSON.toJson(r)),false);return 1;}
}
