package dev.hearthbound.world;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;

/** Server-thread custody helpers. Intent phases fence interruption; no crash-atomic claim. */
final class VillageInventory {
    static String id(ItemStack s){return BuiltInRegistries.ITEM.getKey(s.getItem()).toString();}
    static ItemStack stack(String item,int n){return new ItemStack(BuiltInRegistries.ITEM.get(new ResourceLocation(item)),n);}
    static Container container(ServerLevel level,BlockPos p){
        if(!level.hasChunkAt(p)||!(level.getBlockEntity(p) instanceof Container c))throw new IllegalStateException("Loaded container required: "+p);return c;
    }
    static Map<String,Integer> contents(Container c){var m=new LinkedHashMap<String,Integer>();for(int i=0;i<c.getContainerSize();i++){var s=c.getItem(i);if(!s.isEmpty())m.merge(id(s),s.getCount(),Integer::sum);}return m;}
    static int count(Container c,String item){return contents(c).getOrDefault(item,0);}
    static double distance(Villager v,BlockPos p){return Math.sqrt(v.distanceToSqr(p.getX()+.5,p.getY()+.5,p.getZ()+.5));}
    static List<ItemStack> cargo(CompoundTag m){var out=new ArrayList<ItemStack>();var tags=m.getList("cargo",Tag.TAG_COMPOUND);if(tags.size()>16)throw new IllegalStateException("Cargo bound");for(int i=0;i<tags.size();i++)out.add(ItemStack.of(tags.getCompound(i)));return out;}
    static void cargo(CompoundTag m,List<ItemStack> stacks){var tags=new ListTag();for(var s:stacks)if(!s.isEmpty())tags.add(s.save(new CompoundTag()));if(tags.isEmpty())m.remove("cargo");else m.put("cargo",tags);}
    static Map<String,Integer> cargoContents(CompoundTag m){var out=new LinkedHashMap<String,Integer>();for(var s:cargo(m))if(!s.isEmpty())out.merge(id(s),s.getCount(),Integer::sum);return out;}
    static void add(CompoundTag m,ItemStack stack){var list=cargo(m);list.add(stack.copy());cargo(m,list);}
    static void consume(CompoundTag m,String item,int count){var list=cargo(m);int available=list.stream().filter(s->id(s).equals(item)).mapToInt(ItemStack::getCount).sum();if(available<count)throw new IllegalStateException("Missing owned cargo "+item);for(var s:list)if(id(s).equals(item)){int n=Math.min(count,s.getCount());s.shrink(n);count-=n;}cargo(m,list);}
    static Map<String,Object> take(ServerLevel level,Villager actor,CompoundTag m,BlockPos source,String item){
        if(distance(actor,source)>2.5)throw new IllegalStateException("Remote pickup denied");
        Container c=container(level,source);var before=contents(c);if(before.getOrDefault(item,0)<1)return null;
        String previous=m.getString("phase");m.putString("phase","EXTRACTING");
        ItemStack taken=ItemStack.EMPTY;
        for(int i=0;i<c.getContainerSize();i++)if(!c.getItem(i).isEmpty()&&id(c.getItem(i)).equals(item)){taken=c.removeItem(i,1);add(m,taken);break;}
        c.setChanged();var after=contents(c);var expected=new LinkedHashMap<>(before);expected.compute(item,(k,v)->v==1?null:v-1);
        if(taken.getCount()!=1||!id(taken).equals(item)||!after.equals(expected))throw new IllegalStateException("Native pickup conservation failed");
        m.putString("phase",previous);return Map.of("site",source.asLong(),"item",item,"before",before,"after",after,"units",1);
    }
    static Map<String,Object> put(ServerLevel level,Villager actor,CompoundTag m,BlockPos destination,String only){
        if(distance(actor,destination)>2.5)throw new IllegalStateException("Remote delivery denied");
        Container c=container(level,destination);var all=cargo(m);var moved=new LinkedHashMap<String,Integer>();
        var copies=new ArrayList<ItemStack>();for(int i=0;i<c.getContainerSize();i++)copies.add(c.getItem(i).copy());
        for(var s:all)if(only==null||id(s).equals(only)){
            if(!fit(c,copies,s.copy()))return null;moved.merge(id(s),s.getCount(),Integer::sum);
        }
        if(moved.isEmpty())throw new IllegalStateException("No owned delivery cargo");
        var before=contents(c);String previous=m.getString("phase");m.putString("phase","INSERTING");
        for(var s:all)if(only==null||id(s).equals(only))for(int i=0;i<c.getContainerSize()&&!s.isEmpty();i++){
            ItemStack present=c.getItem(i);if(!c.canPlaceItem(i,s)||(!present.isEmpty()&&!ItemStack.isSameItemSameTags(present,s)))continue;
            int n=Math.min(s.getCount(),Math.min(c.getMaxStackSize(),s.getMaxStackSize())-present.getCount());if(n<=0)continue;
            ItemStack inserted=present.isEmpty()?s.copy():present.copy();inserted.setCount(present.getCount()+n);c.setItem(i,inserted);s.shrink(n);cargo(m,all);
        }
        c.setChanged();var after=contents(c);var expected=new LinkedHashMap<>(before);moved.forEach((k,n)->expected.merge(k,n,Integer::sum));
        if(!after.equals(expected))throw new IllegalStateException("Native delivery conservation failed");m.putString("phase",previous);
        return Map.of("site",destination.asLong(),"items",moved,"before",before,"after",after);
    }
    private static boolean fit(Container c,List<ItemStack> copies,ItemStack s){for(int i=0;i<copies.size()&&!s.isEmpty();i++){
        ItemStack p=copies.get(i);if(!c.canPlaceItem(i,s)||(!p.isEmpty()&&!ItemStack.isSameItemSameTags(p,s)))continue;
        int n=Math.min(s.getCount(),Math.min(c.getMaxStackSize(),s.getMaxStackSize())-p.getCount());if(n<=0)continue;
        ItemStack inserted=p.isEmpty()?s.copy():p.copy();inserted.setCount(p.getCount()+n);copies.set(i,inserted);s.shrink(n);
    }return s.isEmpty();}
}
