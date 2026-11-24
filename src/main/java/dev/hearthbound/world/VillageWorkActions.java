package dev.hearthbound.world;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import dev.hearthbound.civilization.VillageWorkPolicy.Kind;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.BucketPickup;
import net.minecraft.world.level.block.CropBlock;
import net.minecraft.world.level.block.entity.FurnaceBlockEntity;
import static dev.hearthbound.world.VillageEconomyRuntime.*;

/** Native capability library. Recipe knowledge/skills are authored; actors select work. */
final class VillageWorkActions {
    private VillageWorkActions(){}
    static void tick(Data d,ServerLevel level,Villager actor){CompoundTag m=memory(actor);Kind kind=Kind.valueOf(m.getString("kind"));long now=level.getGameTime();
        if(now-m.getLong("started")>2400){hold(d,level,actor,"OWNED_SERVICE_TIMEOUT");return;}
        if(kind==Kind.WAIT){stopMotion(actor);if(now>=m.getLong("until"))settle(d,level,actor,true,"","WAIT_COMPLETED");return;}
        if(kind==Kind.OBSERVE){Known k=known(d,actor.getUUID(),m.getLong("auxiliary"),now);if(k!=null&&k.fact().tick()>=m.getLong("started")){settle(d,level,actor,true,"observation:"+k.fact().id(),"LOCAL_OBSERVATION_COMPLETED");return;}
            go(actor,BlockPos.of(m.getLong("auxiliary")));if(now-m.getLong("started")>600)settle(d,level,actor,false,"","OBSERVATION_UNAVAILABLE");return;}
        District s=district(d,m);if("START".equals(m.getString("phase"))){
            String item=switch(kind){case HARVEST_REPLANT->WHEAT;case MILL_FLOUR->FLOUR;case PREPARE_DOUGH->DOUGH;case BAKE_BREAD->BREAD;case REFILL_WATER->WATER;default->"";};
            long destination=switch(kind){case HARVEST_REPLANT->s.depot();case MILL_FLOUR->s.flour();case PREPARE_DOUGH->s.dough();case BAKE_BREAD->s.pantry();case REFILL_WATER->s.water();default->s.pantry();};
            int target=kind==Kind.BAKE_BREAD?d.foodTarget:4;
            // Execution arbitration on a privately proposed destination; no candidate discovery.
            if(!item.isEmpty()&&VillageInventory.count(VillageInventory.container(level,BlockPos.of(destination)),item)>=target){settle(d,level,actor,false,"","CURRENT_TARGET_FILLED");return;}
            m.putString("phase",switch(kind){case HARVEST_REPLANT->"FARM_SEED";case MILL_FLOUR->"MILL_ASSIGN";case PREPARE_DOUGH->"CRAFT_FLOUR";case BAKE_BREAD->"BAKE_DOUGH";case REFILL_WATER->"WATER_BUCKET";case EAT_BREAD->"EAT_PICKUP";default->throw new IllegalStateException();});
        }
        switch(kind){case HARVEST_REPLANT->farm(d,level,actor,s);case MILL_FLOUR->mill(d,level,actor,s);case PREPARE_DOUGH->craft(d,level,actor,s);case BAKE_BREAD->bake(d,level,actor,s);case REFILL_WATER->water(d,level,actor,s);case EAT_BREAD->eat(d,level,actor,s);default->throw new IllegalStateException("Unknown native work");}
    }
    private static boolean pickup(Data d,ServerLevel level,Villager v,long position,String item,String next){
        BlockPos p=BlockPos.of(position);if(!go(v,p))return false;CompoundTag m=memory(v);var proof=VillageInventory.take(level,v,m,p,item);
        if(proof==null){if(!m.contains("cargo"))settle(d,level,v,false,"","INPUT_NOT_AVAILABLE");else hold(d,level,v,"INPUT_CHANGED_WITH_OWNED_CARGO");return false;}
        witness(d,level,v,"ITEM_PICKED_UP",proof);m.putString("phase",next);return true;
    }
    private static boolean deliver(Data d,ServerLevel level,Villager v,long position,String only,String next){
        BlockPos p=BlockPos.of(position);if(!go(v,p))return false;CompoundTag m=memory(v);var proof=VillageInventory.put(level,v,m,p,only);
        if(proof==null){hold(d,level,v,"DESTINATION_FULL_CARGO_RETAINED");return false;}witness(d,level,v,"ITEMS_DELIVERED",proof);m.putString("phase",next);return true;
    }
    private static String receipt(Data d,Villager v,String process){return d.world+"|"+process+"|"+memory(v).getUUID("optionId");}
    private static void farm(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);BlockPos crop=BlockPos.of(m.getLong("auxiliary"));
        switch(m.getString("phase")){
            case "FARM_SEED"->{var state=level.getBlockState(crop);if(!state.is(Blocks.WHEAT)||!((CropBlock)state.getBlock()).isMaxAge(state)){settle(d,level,v,false,"","CROP_NO_LONGER_MATURE");return;}pickup(d,level,v,s.depot(),SEED,"FARM_CROP");}
            case "FARM_CROP"->{if(!go(v,crop))return;var state=level.getBlockState(crop);
                if(!state.is(Blocks.WHEAT)||!((CropBlock)state.getBlock()).isMaxAge(state)||!level.getBlockState(crop.below()).is(Blocks.FARMLAND)){m.putString("phase","FARM_RETURN_SEED");return;}
                if(VillageInventory.cargoContents(m).getOrDefault(SEED,0)!=1)throw new IllegalStateException("Replant seed custody mismatch");
                var drops=Block.getDrops(state,level,crop,null,v,ItemStack.EMPTY);var counts=new LinkedHashMap<String,Integer>();
                for(ItemStack drop:drops){if(!drop.is(Items.WHEAT)&&!drop.is(Items.WHEAT_SEEDS))throw new IllegalStateException("Unexpected crop loot");counts.merge(VillageInventory.id(drop),drop.getCount(),Integer::sum);}
                if(counts.getOrDefault(WHEAT,0)!=1)throw new IllegalStateException("Unsupported native crop yield");
                m.putString("phase","HARVESTING");
                if(!level.setBlockAndUpdate(crop,Blocks.AIR.defaultBlockState()))throw new IllegalStateException("Crop removal refused");
                for(ItemStack drop:drops)VillageInventory.add(m,drop);
                VillageInventory.consume(m,SEED,1);
                if(!level.setBlockAndUpdate(crop,Blocks.WHEAT.defaultBlockState().setValue(CropBlock.AGE,0)))throw new IllegalStateException("Native replant failed");
                witness(d,level,v,"HARVEST_REPLANT_VERIFIED",Map.of("crop",crop.asLong(),"before_age",7,"after_age",level.getBlockState(crop).getValue(CropBlock.AGE),"native_drops",counts,"seed_consumed",1,"cargo",VillageInventory.cargoContents(m),"receipt",receipt(d,v,"harvest")));
                d.count("wheat_harvested",1);d.count("crops_replanted",1);d.count("crop_seeds_generated",counts.getOrDefault(SEED,0));m.putString("phase","FARM_DELIVER");}
            case "FARM_DELIVER"->{if(deliver(d,level,v,s.depot(),null,"FARM_DONE"))settle(d,level,v,true,receipt(d,v,"harvest"),"WHEAT_AND_SEEDS_STORED");}
            case "FARM_RETURN_SEED"->{if(deliver(d,level,v,s.depot(),null,"FARM_CANCELLED"))settle(d,level,v,false,"","CROP_CHANGED_UNUSED_SEED_RETURNED");}
            default->throw new IllegalStateException("Uncertain harvest phase");
        }
    }
    private static void mill(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);
        switch(m.getString("phase")){
            case "MILL_ASSIGN"->{try{SableHauling.assign(level,v,BlockPos.of(s.depot()),BlockPos.of(s.mill()));}
                catch(RuntimeException refused){if(SableHauling.active(v))throw refused;settle(d,level,v,false,"","NATIVE_MILL_ASSIGNMENT_REFUSED");return;}
                var nativeTag=v.getPersistentData().getCompound("hearthbound.haul");m.putUUID("job",nativeTag.getUUID("jobId"));m.putLong("source",s.depot());m.putLong("goal",s.flour());m.putString("phase","MILL_INPUT");
                witness(d,level,v,"NATIVE_MILL_ASSIGNED",Map.of("source",s.depot(),"machine",s.mill(),"destination",s.flour(),"assigned_tick",nativeTag.getLong("assignedTick")));}
            case "MILL_INPUT"->{var nativeTag=v.getPersistentData().getCompound("hearthbound.haul");int phase=nativeTag.getInt("phase");
                if(phase==3||phase==4||phase==5){if(!nativeTag.contains("cargo")&&SableHauling.cancelBeforePickup(level,v)){settle(d,level,v,false,"","NATIVE_INPUT_UNAVAILABLE_SAFE_CANCEL");return;}hold(d,level,v,"NATIVE_MOTOR_UNCERTAIN");return;}
                v.setNoAi(false);SableHauling.tick(level,v);
                if(SableHauling.completedJob(v,m.getUUID("job"),BlockPos.of(s.mill()))){var assignment=SableHauling.completedAssignment(level,v,m.getUUID("job"),BlockPos.of(s.mill()));
                    if(assignment.source()!=s.depot())throw new IllegalStateException("Mill source changed");witness(d,level,v,"MILL_INPUT_DELIVERED",Map.of("assignment",assignment,"delivered_tick",nativeTag.getLong("physicalDeliveredTick"),"production_credit",false));
                    ServiceProductionBridge.begin(m,BlockPos.of(s.mill()));m.putString("phase","MILL_PROCESS");stopMotion(v);}}
            case "MILL_PROCESS"->{if(!go(v,BlockPos.of(s.mill())))return;if(!ServiceProductionBridge.callbackPresent(level,m))return;
                var proof=ServiceProductionBridge.collect(level,v,m,scope(d,level));var callback=MillProcessReceipts.observedCallback(level,proof.job());
                witness(d,level,v,"MILL_PROCESS_VERIFIED",Map.of("proof",proof,"items",ServiceProductionBridge.outputItems(m),"wheat_before",callback.wheatBefore(),"wheat_after",callback.wheatAfter(),"flour_before",callback.flourBefore(),"flour_after",callback.flourAfter()));
                d.count("wheat_milled",1);d.count("flour_produced",proof.units());d.count("mill_seeds_generated",ServiceProductionBridge.outputItems(m).getOrDefault(SEED,0));m.putString("phase","MILL_DELIVER");}
            case "MILL_DELIVER"->{if(!go(v,BlockPos.of(s.flour())))return;var delivered=ServiceProductionBridge.deliver(level,v,m,scope(d,level));if(delivered==null){hold(d,level,v,"FLOUR_DESTINATION_FULL");return;}
                witness(d,level,v,"MILL_OUTPUT_DELIVERED",Map.of("delivery",delivered,"destination",s.flour()));var proof=ServiceProductionBridge.release(level,v,m,scope(d,level));
                settle(d,level,v,true,proof.physicalEvidence(),"CREATE_OUTPUT_STORED_AND_RESERVATION_RELEASED");}
            default->throw new IllegalStateException("Uncertain mill phase");
        }
    }
    private static void craft(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);
        switch(m.getString("phase")){
            case "CRAFT_FLOUR"->{if(VillageInventory.count(VillageInventory.container(level,BlockPos.of(s.water())),WATER)<1){settle(d,level,v,false,"","WATER_INPUT_CHANGED_BEFORE_CUSTODY");return;}pickup(d,level,v,s.flour(),FLOUR,"CRAFT_WATER");}
            case "CRAFT_WATER"->pickup(d,level,v,s.water(),WATER,"CRAFT_TABLE");
            case "CRAFT_TABLE"->{if(!go(v,BlockPos.of(s.table())))return;if(!level.getBlockState(BlockPos.of(s.table())).is(Blocks.CRAFTING_TABLE))throw new IllegalStateException("Crafting table removed with owned inputs");
                var menu=new AbstractContainerMenu(MenuType.CRAFTING,-1){@Override public ItemStack quickMoveStack(Player p,int slot){return ItemStack.EMPTY;}@Override public boolean stillValid(Player p){return false;}};
                var grid=new TransientCraftingContainer(menu,3,3);grid.setItem(0,VillageInventory.stack(FLOUR,1));grid.setItem(1,new ItemStack(Items.WATER_BUCKET));
                var recipe=level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING,grid,level).orElseThrow(()->new IllegalStateException("No native dough crafting recipe"));
                ItemStack result=recipe.assemble(grid,level.registryAccess());var remaining=recipe.getRemainingItems(grid);
                var remainders=new LinkedHashMap<String,Integer>();for(var item:remaining)if(!item.isEmpty())remainders.merge(VillageInventory.id(item),item.getCount(),Integer::sum);
                if(!VillageInventory.id(result).equals(DOUGH)||result.getCount()!=1||!remainders.equals(Map.of(BUCKET,1))||!VillageInventory.cargoContents(m).equals(Map.of(FLOUR,1,WATER,1)))throw new IllegalStateException("Native dough recipe/custody contract changed");
                m.putString("phase","CRAFTING");VillageInventory.consume(m,FLOUR,1);VillageInventory.consume(m,WATER,1);VillageInventory.add(m,result);for(var item:remaining)if(!item.isEmpty())VillageInventory.add(m,item);
                witness(d,level,v,"NATIVE_CRAFT_VERIFIED",Map.of("recipe",recipe.getId().toString(),"table",s.table(),"inputs",Map.of(FLOUR,1,WATER,1),"result",Map.of(DOUGH,1),"remaining",remainders,"receipt",receipt(d,v,"craft")));
                d.count("flour_crafted",1);d.count("dough_prepared",1);m.putString("phase","CRAFT_BUCKET_RETURN");}
            case "CRAFT_BUCKET_RETURN"->deliver(d,level,v,s.water(),BUCKET,"CRAFT_DOUGH_DELIVER");
            case "CRAFT_DOUGH_DELIVER"->{if(deliver(d,level,v,s.dough(),null,"CRAFT_DONE"))settle(d,level,v,true,receipt(d,v,"craft"),"DOUGH_STORED_BUCKET_RETURNED");}
            default->throw new IllegalStateException("Uncertain craft phase");
        }
    }
    private static void bake(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);BlockPos furnacePos=BlockPos.of(s.furnace());
        switch(m.getString("phase")){
            case "BAKE_DOUGH"->{if(!(level.getBlockEntity(furnacePos)instanceof FurnaceBlockEntity f)||!f.getItem(0).isEmpty()||!f.getItem(2).isEmpty()||(f.getItem(1).isEmpty()&&f.saveWithoutMetadata().getInt("BurnTime")<=0)){settle(d,level,v,false,"","FURNACE_NOT_READY");return;}pickup(d,level,v,s.dough(),DOUGH,"BAKE_INSERT");}
            case "BAKE_INSERT"->{if(!go(v,furnacePos))return;if(!(level.getBlockEntity(furnacePos)instanceof FurnaceBlockEntity f)||!f.getItem(0).isEmpty()||!f.getItem(2).isEmpty())throw new IllegalStateException("Furnace changed with owned dough");
                var input=VillageInventory.stack(DOUGH,1);var recipe=level.getRecipeManager().getRecipeFor(RecipeType.SMELTING,new SimpleContainer(input),level).orElseThrow(()->new IllegalStateException("No native bread smelting recipe"));
                var output=recipe.assemble(new SimpleContainer(input),level.registryAccess());if(!output.is(Items.BREAD)||output.getCount()!=1)throw new IllegalStateException("Unexpected furnace recipe output");
                CompoundTag before=f.saveWithoutMetadata();m.putString("phase","INSERTING_FURNACE");m.putString("bakeRecipe",recipe.getId().toString());m.putInt("bakeCookTime",recipe.getCookingTime());m.putInt("recipeCountBefore",before.getCompound("RecipesUsed").getInt(recipe.getId().toString()));m.putLong("bakeInputTick",level.getGameTime());m.putInt("maxCookProgress",0);
                f.setItem(0,input);f.setChanged();VillageInventory.consume(m,DOUGH,1);
                witness(d,level,v,"FURNACE_INPUT_INSERTED",Map.of("furnace",s.furnace(),"recipe",recipe.getId().toString(),"cook_time",recipe.getCookingTime(),"input_before",0,"input_after",f.getItem(0).getCount(),"native_before",before.toString()));m.putString("phase","BAKE_PROCESS");}
            case "BAKE_PROCESS"->{stopMotion(v);if(!(level.getBlockEntity(furnacePos)instanceof FurnaceBlockEntity f))throw new IllegalStateException("Owned furnace removed");CompoundTag nbt=f.saveWithoutMetadata();
                int progress=nbt.getInt("CookTime");if(progress>m.getInt("maxCookProgress")){m.putInt("maxCookProgress",progress);witness(d,level,v,"FURNACE_PROGRESS",Map.of("furnace",s.furnace(),"progress",progress,"native",nbt.toString()));}
                if(f.getItem(2).isEmpty())return;
                if(!f.getItem(0).isEmpty()||!f.getItem(2).is(Items.BREAD)||f.getItem(2).getCount()!=1||m.getInt("maxCookProgress")<=0||level.getGameTime()-m.getLong("bakeInputTick")<m.getInt("bakeCookTime")-1||nbt.getCompound("RecipesUsed").getInt(m.getString("bakeRecipe"))!=m.getInt("recipeCountBefore")+1)throw new IllegalStateException("Native furnace process evidence disagrees");
                if(!go(v,furnacePos))return;m.putString("phase","EXTRACTING_FURNACE");ItemStack bread=f.removeItem(2,1);VillageInventory.add(m,bread);f.setChanged();if(!f.getItem(2).isEmpty()||!bread.is(Items.BREAD))throw new IllegalStateException("Furnace extraction failed");
                witness(d,level,v,"NATIVE_BAKE_VERIFIED",Map.of("furnace",s.furnace(),"recipe",m.getString("bakeRecipe"),"input_tick",m.getLong("bakeInputTick"),"input_consumed",1,"bread_produced",1,"native_recipe_count_before",m.getInt("recipeCountBefore"),"native_recipe_count_after",nbt.getCompound("RecipesUsed").getInt(m.getString("bakeRecipe")),"native_before_collection",nbt.toString(),"receipt",receipt(d,v,"bake")));
                d.count("dough_baked",1);d.count("bread_baked",1);m.putString("phase","BAKE_DELIVER");}
            case "BAKE_DELIVER"->{if(deliver(d,level,v,s.pantry(),null,"BAKE_DONE")){d.count("bread_delivered",1);settle(d,level,v,true,receipt(d,v,"bake"),"REAL_FURNACE_BREAD_STORED");}}
            default->throw new IllegalStateException("Uncertain furnace phase");
        }
    }
    private static void water(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);BlockPos well=BlockPos.of(s.well());
        switch(m.getString("phase")){
            case "WATER_BUCKET"->pickup(d,level,v,s.water(),BUCKET,"WATER_FILL");
            case "WATER_FILL"->{if(!go(v,well.above()))return;var state=level.getBlockState(well);if(!(state.getBlock()instanceof BucketPickup pickup)||!level.getFluidState(well).isSource()){m.putString("phase","WATER_RETURN_EMPTY");return;}
                if(!VillageInventory.cargoContents(m).equals(Map.of(BUCKET,1)))throw new IllegalStateException("Water bucket custody differs");m.putString("phase","FILLING_BUCKET");ItemStack filled=pickup.pickupBlock(level,well,state);
                if(!filled.is(Items.WATER_BUCKET)||filled.getCount()!=1)throw new IllegalStateException("Native water pickup failed");VillageInventory.consume(m,BUCKET,1);VillageInventory.add(m,filled);v.playSound(SoundEvents.BUCKET_FILL,1,1);
                witness(d,level,v,"WATER_BUCKET_FILLED",Map.of("well",s.well(),"source_before",true,"source_after",level.getFluidState(well).isSource(),"bucket_consumed",1,"water_bucket_produced",1,"receipt",receipt(d,v,"water")));d.count("water_filled",1);m.putString("phase","WATER_DELIVER");}
            case "WATER_DELIVER"->{if(deliver(d,level,v,s.water(),null,"WATER_DONE"))settle(d,level,v,true,receipt(d,v,"water"),"FILLED_BUCKET_STORED");}
            case "WATER_RETURN_EMPTY"->{if(deliver(d,level,v,s.water(),null,"WATER_CANCELLED"))settle(d,level,v,false,"","WELL_CHANGED_EMPTY_BUCKET_RETURNED");}
            default->throw new IllegalStateException("Uncertain water phase");
        }
    }
    private static void eat(Data d,ServerLevel level,Villager v,District s){CompoundTag m=memory(v);
        if("EAT_PICKUP".equals(m.getString("phase"))){pickup(d,level,v,s.pantry(),BREAD,"EAT_CONSUME");return;}
        if(!"EAT_CONSUME".equals(m.getString("phase")))throw new IllegalStateException("Uncertain meal phase");
        if(!VillageInventory.cargoContents(m).equals(Map.of(BREAD,1)))throw new IllegalStateException("Meal lacks real bread custody");double before=m.getDouble("satiety");
        m.putString("phase","CONSUMING");VillageInventory.consume(m,BREAD,1);double after=Math.min(100,before+40);m.putDouble("satiety",after);v.playSound(SoundEvents.GENERIC_EAT,.7f,1);
        witness(d,level,v,"BREAD_EATEN",Map.of("bread_consumed",1,"satiety_before",before,"satiety_after",after,"need_model","AUTHORED_COLONY_SATIETY_V1","receipt",receipt(d,v,"meal")));d.count("meals",1);settle(d,level,v,true,receipt(d,v,"meal"),"BREAD_CONSUMED_FOR_OWN_NEED");
    }
}
