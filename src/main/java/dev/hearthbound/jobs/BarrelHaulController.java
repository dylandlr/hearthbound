package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import java.util.List;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.phys.AABB;
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
    private BarrelHaulController() {}

    public static int assign(CommandSourceStack source, BlockPos from, BlockPos to, int count) {
        ServerLevel level = source.getLevel();
        if (count < 1 || count > 64 || from.equals(to) || !level.hasChunkAt(from) || !level.hasChunkAt(to)
                || !(level.getBlockEntity(from) instanceof BarrelBlockEntity)
                || !(level.getBlockEntity(to) instanceof BarrelBlockEntity)) {
            source.sendFailure(Component.literal("Use two loaded, distinct barrels and 1-64 wheat."));
            return 0;
        }
        List<Villager> citizens = level.getEntitiesOfClass(Villager.class,
                new AABB(source.getPosition(), source.getPosition()).inflate(32),
                v -> v.getTags().contains(SABLE_TAG));
        if (citizens.isEmpty()) {
            source.sendFailure(Component.literal("No tagged Sable nearby."));
            return 0;
        }
        Villager sable = citizens.get(0);
        if (sable.getPersistentData().contains(ROOT)
                || sable.getPersistentData().getBoolean("HearthboundTravelActive")) {
            source.sendFailure(Component.literal("Sable already has a job; finish or recover it first."));
            return 0;
        }
        CompoundTag job = new CompoundTag();
        job.putString("Phase", "PICKUP");
        job.putLong("From", from.asLong());
        job.putLong("To", to.asLong());
        job.putInt("Requested", count);
        job.putInt("Cargo", 0);
        job.putString("Result", "IN_PROGRESS");
        sable.getPersistentData().put(ROOT, job);
        source.sendSuccess(() -> Component.literal("Assigned Sable: carry up to " + count
                + " wheat between two real barrels."), false);
        return 1;
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager sable) || sable.level().isClientSide()
                || !sable.getTags().contains(SABLE_TAG) || sable.tickCount % 20 != 0) return;
        CompoundTag persisted = sable.getPersistentData();
        if (!persisted.contains(ROOT, 10)) return;
        CompoundTag job = persisted.getCompound(ROOT);
        if (!(sable.level() instanceof ServerLevel level)) return;
        String phase = job.getString("Phase");
        BlockPos target = BlockPos.of(job.getLong(phase.equals("PICKUP") ? "From" : "To"));
        if (!level.hasChunkAt(target)) {
            sable.getNavigation().stop();
            job.putString("Result", "WAITING_FOR_CHUNK");
            return;
        }
        if (sable.distanceToSqr(target.getX() + .5, target.getY() + .5, target.getZ() + .5) > 6.25) {
            sable.getNavigation().moveTo(target.getX() + .5, target.getY(), target.getZ() + .5, 1.0);
            return;
        }
        sable.getNavigation().stop();
        if (!(level.getBlockEntity(target) instanceof BarrelBlockEntity barrel)) {
            job.putString("Result", "MISSING_BARREL");
            return;
        }
        if ("PICKUP".equals(phase)) {
            int quantity = Math.min(job.getInt("Requested"), countWheat(barrel));
            if (quantity == 0) {
                job.putString("Result", "NO_WHEAT");
                return;
            }
            // Prevent over-extraction into a destination with no space.
            BlockPos destination = BlockPos.of(job.getLong("To"));
            if (!level.hasChunkAt(destination) ||
                    !(level.getBlockEntity(destination) instanceof BarrelBlockEntity receiver)
                    || wheatCapacity(receiver) < quantity) {
                job.putString("Result", "OUTPUT_FULL");
                return;
            }
            int withdrawn = removeWheat(barrel, quantity);
            if (withdrawn <= 0) return;
            job.putInt("Cargo", withdrawn);
            job.putString("Phase", "DELIVER");
            job.putString("Result", "CARRYING");
        } else if ("DELIVER".equals(phase)) {
            int cargo = job.getInt("Cargo");
            int delivered = insertWheat(barrel, cargo);
            int left = cargo - delivered;
            job.putInt("Cargo", left);
            if (left == 0) {
                persisted.remove(ROOT);
                persisted.putString("HearthboundLastHaulResult", "DELIVERED_" + delivered);
            } else job.putString("Result", "OUTPUT_FULL_CARRYING");
        }
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
