package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import java.util.Map;
import java.util.HashMap;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * First real-world transfer probe. Travels to a source barrel, extracts wheat into
 * persisted citizen cargo, then travels to a destination barrel and inserts it.
 * Not a Create mill adapter; not crash-atomic across world and entity saves.
 */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class BarrelHaulController {
    private static final String ROOT = "HearthboundHaul";
    private static final String SABLE_TAG = "hearthbound.sable";
    private static final Map<UUID, TravelProgress> TRAVEL = new HashMap<>();
    private BarrelHaulController() {}

    public static int assign(CommandSourceStack source, BlockPos from, BlockPos to, int count) {
        ServerLevel level = source.getLevel();
        if (count < 1 || count > 64 || from.equals(to) || !level.hasChunkAt(from) || !level.hasChunkAt(to)
                || !(level.getBlockEntity(from) instanceof BarrelBlockEntity)
                || !(level.getBlockEntity(to) instanceof BarrelBlockEntity)
                    && !isMillstone(level, to)) {
            source.sendFailure(Component.literal("Use two loaded, distinct barrels and 1-64 wheat."));
            return 0;
        }
        Villager sable = SableSelection.nearest(source, SableSelection::idle);
        if (sable == null) {
            source.sendFailure(Component.literal("No idle Sable within 32 blocks."));
            return 0;
        }
        if (!assignCitizen(sable, from, to, count)) {
            source.sendFailure(Component.literal("Could not assign hauling job."));
            return 0;
        }
        source.sendSuccess(() -> Component.literal("Sable assigned to haul " + count + " wheat."), false);
        return 1;
    }

    /** Same server-side job assignment used by commands and world integration probes. */
    public static boolean assignCitizen(Villager sable, BlockPos from, BlockPos to, int count) {
        if (count < 1 || count > 64 || from.equals(to) || sable.getPersistentData().contains(ROOT)
                || sable.getPersistentData().getBoolean("HearthboundTravelActive")) return false;
        if (!(sable.level() instanceof ServerLevel level)) return false;
        CompoundTag job = new CompoundTag();
        job.putString("Phase", "PICKUP");
        job.putLong("From", from.asLong());
        job.putLong("To", to.asLong());
        job.putInt("Requested", count);
        job.putInt("Cargo", 0);
        job.putString("Result", "IN_PROGRESS");
        job.putString("JobId", java.util.UUID.randomUUID().toString());
        job.putString("Item", "minecraft:wheat");
        job.putString("Dimension", level.dimension().location().toString());
        if (!WorkshopRegistry.get(level).reserveNew(sable, job)) return false;
        TRAVEL.remove(sable.getUUID());
        sable.getPersistentData().put(ROOT, job);
        return true;
    }

    public static boolean assignFlourCitizen(Villager sable, BlockPos mill, BlockPos storage, int count) {
        if (!assignCitizen(sable, mill, storage, count)) return false;
        sable.getPersistentData().getCompound(ROOT).putString("Item", "create:wheat_flour");
        return true;
    }

    public static int status(CommandSourceStack source) {
        Villager worker = SableSelection.nearest(source, v -> true);
        if (worker == null) {
            source.sendFailure(Component.literal("No tagged Sable nearby."));
            return 0;
        }
        CompoundTag data = worker.getPersistentData();
        if (!data.contains(ROOT, 10)) {
            source.sendSuccess(() -> Component.literal("No active haul. Last result: " +
                    data.getString("HearthboundLastHaulResult")), false);
            return 1;
        }
        CompoundTag job = data.getCompound(ROOT);
        source.sendSuccess(() -> Component.literal("Haul phase=" + job.getString("Phase")
                + ", cargo=" + job.getInt("Cargo") + ", status=" + job.getString("Result")), false);
        return 1;
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager sable) || sable.level().isClientSide()
                || !sable.getTags().contains(SABLE_TAG) || sable.tickCount % 5 != 0) return;
        CompoundTag persisted = sable.getPersistentData();
        if (!persisted.contains(ROOT, 10)) return;
        CompoundTag job = persisted.getCompound(ROOT);
        if (!(sable.level() instanceof ServerLevel level)) return;
        if (!job.contains("Dimension")) job.putString("Dimension", level.dimension().location().toString());
        if (!job.getString("Dimension").equals(level.dimension().location().toString())) {
            sable.getNavigation().stop(); job.putString("Result", "WRONG_DIMENSION"); return;
        }
        if (job.getString("JobId").isEmpty()) job.putString("JobId", UUID.randomUUID().toString());
        if (!WorkshopRegistry.get(level).reserve(sable, job)) {
            if (!job.getBoolean("Paused")) {
                clearInteraction(job); sable.getNavigation().stop();
                job.putString("Result", "WAITING_FOR_STATION");
            }
            return;
        }
        String phase = job.getString("Phase");
        BlockPos target = BlockPos.of(job.getLong(phase.equals("PICKUP") ? "From" : "To"));
        if (job.getBoolean("Paused")) return;
        if (!level.hasChunkAt(target)) {
            clearInteraction(job);
            sable.getNavigation().stop();
            job.putString("Result", "WAITING_FOR_CHUNK");
            return;
        }
        double distanceSq = sable.distanceToSqr(target.getX() + .5, target.getY() + .5, target.getZ() + .5);
        if (!StationApproach.inReach(sable, target)) {
            clearInteraction(job);
            // Interaction updates are frequent; navigation/watchdog samples stay at one second.
            if (sable.tickCount % 20 != 0) return;
            long gameTick = level.getGameTime();
            // A worker on top of a station is physically close but has not
            // reached an interaction position; the watchdog must still run.
            double travelDistanceSq = Math.max(distanceSq, StationApproach.REACH_SQUARED + 1.0);
            TravelProgress watch = TRAVEL.computeIfAbsent(sable.getUUID(),
                    id -> new TravelProgress(gameTick, travelDistanceSq));
            TravelProgress.Outcome outcome = watch.sample(gameTick, travelDistanceSq);
            if (outcome == TravelProgress.Outcome.STALLED || outcome == TravelProgress.Outcome.TIMED_OUT) {
                job.putBoolean("Paused", true);
                job.putString("Result", outcome.name() + "_CARGO_" + job.getInt("Cargo"));
                sable.getNavigation().stop();
                TRAVEL.remove(sable.getUUID());
                return;
            }
            if (!StationApproach.moveTo(level, sable, target))
                job.putString("Result", "NO_ACCESSIBLE_STATION");
            else job.putString("Result", phase.equals("PICKUP") ? "IN_PROGRESS" : "CARRYING");
            return;
        }
        TRAVEL.remove(sable.getUUID());
        sable.getNavigation().stop();
        sable.getLookControl().setLookAt(target.getX() + .5, target.getY() + .5, target.getZ() + .5);
        BlockEntity destinationEntity = level.getBlockEntity(target);
        if (destinationEntity == null) {
            clearInteraction(job);
            job.putString("Result", "MISSING_INVENTORY");
            return;
        }
        if ("PICKUP".equals(phase)) {
            boolean flourJob = "create:wheat_flour".equals(job.getString("Item"));
            if (!flourJob && !(destinationEntity instanceof BarrelBlockEntity)) {
                clearInteraction(job);
                job.putString("Result", "MISSING_SOURCE_BARREL");
                return;
            }
            net.minecraft.world.item.Item item = flourJob ? BuiltInRegistries.ITEM.get(
                    new ResourceLocation("create", "wheat_flour")) : Items.WHEAT;
            int quantity = Math.min(job.getInt("Requested"), flourJob
                    ? extractableFlour(level, target) : countWheat((BarrelBlockEntity) destinationEntity));
            if (quantity == 0) {
                clearInteraction(job);
                job.putString("Result", "NO_WHEAT");
                return;
            }
            // Prevent over-extraction into a destination with no space.
            BlockPos destination = BlockPos.of(job.getLong("To"));
            if (!level.hasChunkAt(destination) || (flourJob
                    ? flourBarrelCapacity(level, destination, item) : destinationCapacity(level, destination, quantity)) < quantity) {
                clearInteraction(job);
                job.putString("Result", "OUTPUT_FULL");
                return;
            }
            if (!readyToTransfer(job, phase)) return;
            int withdrawn = flourJob ? takeFlour(level, target, quantity)
                    : removeWheat((BarrelBlockEntity) destinationEntity, quantity);
            if (withdrawn <= 0) return;
            job.putInt("Cargo", withdrawn);
            clearInteraction(job);
            job.putString("Phase", "DELIVER");
            TRAVEL.remove(sable.getUUID());
            job.putString("Result", "CARRYING");
        } else if ("DELIVER".equals(phase)) {
            int cargo = job.getInt("Cargo");
            boolean flourJob = "create:wheat_flour".equals(job.getString("Item"));
            int space = flourJob ? flourBarrelCapacity(level, target, BuiltInRegistries.ITEM.get(
                    new ResourceLocation("create", "wheat_flour"))) : destinationCapacity(level, target, cargo);
            if (space <= 0) {
                clearInteraction(job);
                job.putString("Result", "OUTPUT_FULL_CARRYING");
                return;
            }
            if (!readyToTransfer(job, phase)) return;
            int delivered = "create:wheat_flour".equals(job.getString("Item"))
                    ? insertFlour(level, target, cargo)
                    : destinationEntity instanceof BarrelBlockEntity barrel
                    ? insertWheat(barrel, cargo) : insertMillWheat(level, target, cargo);
            int left = cargo - delivered;
            job.putInt("Cargo", left);
            clearInteraction(job);
            if (left == 0) {
                persisted.remove(ROOT);
                WorkshopRegistry.get(level).release(sable, job.getString("JobId"));
                persisted.putString("HearthboundLastHaulResult", "DELIVERED_" + delivered);
            } else job.putString("Result", "OUTPUT_FULL_CARRYING");
        }
    }

    /** Persisted dwell; no item leaves either inventory until all 15 valid ticks elapse. */
    private static boolean readyToTransfer(CompoundTag job, String phase) {
        if (!phase.equals(job.getString("InteractionPhase"))) {
            job.putString("InteractionPhase", phase);
            job.putInt("InteractionTicks", 15);
        } else job.putInt("InteractionTicks", Math.max(0, job.getInt("InteractionTicks") - 5));
        job.putString("Result", phase.equals("PICKUP") ? "PICKING_UP" : "PUTTING_DOWN");
        return job.getInt("InteractionTicks") == 0;
    }

    private static void clearInteraction(CompoundTag job) {
        job.remove("InteractionPhase");
        job.remove("InteractionTicks");
    }

    private static IItemHandler millOutput(ServerLevel level, BlockPos pos) {
        if (!isMillstone(level, pos)) return null;
        BlockEntity entity = level.getBlockEntity(pos);
        return entity == null ? null : entity.getCapability(ForgeCapabilities.ITEM_HANDLER, Direction.EAST).orElse(null);
    }

    private static int extractableFlour(ServerLevel level, BlockPos pos) {
        IItemHandler output = millOutput(level, pos);
        if (output == null) return 0;
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        int count = 0;
        for (int i = 0; i < output.getSlots(); i++)
            if (output.getStackInSlot(i).is(flour))
                count += output.extractItem(i, 64, true).getCount();
        return count;
    }

    private static int takeFlour(ServerLevel level, BlockPos pos, int amount) {
        IItemHandler output = millOutput(level, pos);
        if (output == null) return 0;
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        int taken = 0;
        for (int i = 0; i < output.getSlots() && taken < amount; i++)
            if (output.getStackInSlot(i).is(flour))
                taken += output.extractItem(i, amount - taken, false).getCount();
        return taken;
    }

    private static int flourBarrelCapacity(ServerLevel level, BlockPos pos, net.minecraft.world.item.Item flour) {
        if (!(level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel)) return 0;
        int space = 0;
        for (int i = 0; i < barrel.getContainerSize(); i++) {
            ItemStack stack = barrel.getItem(i);
            if (stack.isEmpty()) space += barrel.getMaxStackSize();
            else if (stack.is(flour)) space += Math.max(0, Math.min(stack.getMaxStackSize(),
                    barrel.getMaxStackSize()) - stack.getCount());
        }
        return space;
    }

    private static int insertFlour(ServerLevel level, BlockPos pos, int amount) {
        if (!(level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel)) return 0;
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        int left = amount;
        for (int i = 0; i < barrel.getContainerSize() && left > 0; i++) {
            ItemStack stack = barrel.getItem(i);
            if (!stack.is(flour)) continue;
            int n = Math.min(left, Math.max(0, Math.min(stack.getMaxStackSize(), barrel.getMaxStackSize()) - stack.getCount()));
            if (n > 0) { stack.grow(n); barrel.setItem(i, stack); left -= n; }
        }
        for (int i = 0; i < barrel.getContainerSize() && left > 0; i++) {
            if (!barrel.getItem(i).isEmpty()) continue;
            int n = Math.min(left, Math.min(64, barrel.getMaxStackSize()));
            barrel.setItem(i, new ItemStack(flour, n)); left -= n;
        }
        return amount - left;
    }

    private static boolean isMillstone(ServerLevel level, BlockPos pos) {
        return BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock())
                .equals(new ResourceLocation("create", "millstone"));
    }

    private static IItemHandler millInput(ServerLevel level, BlockPos pos) {
        if (!isMillstone(level, pos)) return null;
        BlockEntity entity = level.getBlockEntity(pos);
        if (entity == null) return null;
        return entity.getCapability(ForgeCapabilities.ITEM_HANDLER, Direction.UP).orElse(null);
    }

    private static int destinationCapacity(ServerLevel level, BlockPos pos, int amount) {
        BlockEntity entity = level.getBlockEntity(pos);
        if (entity instanceof BarrelBlockEntity barrel) return wheatCapacity(barrel);
        IItemHandler input = millInput(level, pos);
        if (input == null) return 0;
        ItemStack remainder = new ItemStack(Items.WHEAT, amount);
        for (int i = 0; i < input.getSlots() && !remainder.isEmpty(); i++)
            remainder = input.insertItem(i, remainder, true);
        return amount - remainder.getCount();
    }

    private static int insertMillWheat(ServerLevel level, BlockPos pos, int amount) {
        IItemHandler input = millInput(level, pos);
        if (input == null) return 0;
        ItemStack remainder = new ItemStack(Items.WHEAT, amount);
        for (int i = 0; i < input.getSlots() && !remainder.isEmpty(); i++)
            remainder = input.insertItem(i, remainder, false);
        return amount - remainder.getCount();
    }

    private static int countWheat(Container inventory) {
        int n = 0;
        for (int i = 0; i < inventory.getContainerSize(); i++)
            if (inventory.getItem(i).is(Items.WHEAT)) n += inventory.getItem(i).getCount();
        return n;
    }

    private static int wheatCapacity(Container inventory) {
        int space = 0;
        for (int i = 0; i < inventory.getContainerSize(); i++) {
            ItemStack item = inventory.getItem(i);
            if (item.isEmpty()) space += Math.min(64, inventory.getMaxStackSize());
            else if (item.is(Items.WHEAT)) space += Math.max(0, Math.min(item.getMaxStackSize(),
                    inventory.getMaxStackSize()) - item.getCount());
        }
        return space;
    }

    private static int removeWheat(Container inventory, int amount) {
        int left = amount;
        for (int i = 0; i < inventory.getContainerSize() && left > 0; i++) {
            ItemStack item = inventory.getItem(i);
            if (!item.is(Items.WHEAT)) continue;
            int take = Math.min(item.getCount(), left);
            inventory.removeItem(i, take);
            left -= take;
        }
        inventory.setChanged();
        return amount - left;
    }

    private static int insertWheat(Container inventory, int amount) {
        int left = amount;
        for (int i = 0; i < inventory.getContainerSize() && left > 0; i++) {
            ItemStack item = inventory.getItem(i);
            if (!item.is(Items.WHEAT)) continue;
            int room = Math.max(0, Math.min(item.getMaxStackSize(), inventory.getMaxStackSize()) - item.getCount());
            int added = Math.min(left, room);
            if (added > 0) { item.grow(added); inventory.setItem(i, item); left -= added; }
        }
        for (int i = 0; i < inventory.getContainerSize() && left > 0; i++) {
            if (!inventory.getItem(i).isEmpty()) continue;
            int added = Math.min(left, Math.min(64, inventory.getMaxStackSize()));
            inventory.setItem(i, new ItemStack(Items.WHEAT, added));
            left -= added;
        }
        inventory.setChanged();
        return amount - left;
    }
}
