package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;
import net.minecraftforge.common.util.LazyOptional;

/**
 * Server-only proof-of-concept hauling of a single wheat item between inventories.
 * Stores job/cargo in villager persistent NBT. Does not guarantee atomic survival
 * of crashes between saving a chest and the villager: do not use on valuable items.
 */
public final class SableHauling {
    private static final String KEY = "hearthbound.haul";
    private static final String SOURCE = "source";
    private static final String DESTINATION = "destination";
    private static final String CARGO = "cargo";
    private static final String PHASE = "phase";
    private static final String ERROR = "error";
    private static final int TO_SOURCE = 0;
    private static final int TO_DEST = 1;
    private static final int COMPLETE = 2;
    private static final int PAUSED = 3;

    private SableHauling() {}

    public static void assign(ServerLevel level, Villager citizen, BlockPos source, BlockPos destination) {
        if (source.equals(destination)) throw new IllegalArgumentException("same endpoint");
        if (active(citizen)) throw new IllegalStateException("already carrying out a haul");
        if (!HaulClaims.claim(level, source, citizen.getUUID()))
            throw new IllegalStateException("source already claimed by another citizen");
        CompoundTag tag = new CompoundTag();
        tag.putLong(SOURCE, source.asLong());
        tag.putLong(DESTINATION, destination.asLong());
        tag.putInt(PHASE, TO_SOURCE);
        citizen.getPersistentData().put(KEY, tag);
    }

    public static boolean active(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        return tag.contains(PHASE) && tag.getInt(PHASE) != COMPLETE;
    }

    public static String status(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!tag.contains(PHASE)) return "No hauling job";
        return switch (tag.getInt(PHASE)) {
            case TO_SOURCE -> "Walking to source";
            case TO_DEST -> "Carrying wheat to destination";
            case COMPLETE -> "Haul complete";
            default -> "Paused: " + tag.getString(ERROR);
        };
    }

    public static void tick(ServerLevel level, Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!tag.contains(PHASE)) return;
        int phase = tag.getInt(PHASE);
        BlockPos claimedSource = BlockPos.of(tag.getLong(SOURCE));
        if (phase != COMPLETE && !HaulClaims.claim(level, claimedSource, citizen.getUUID())) {
            pause(tag, "Source claimed by another citizen; manual recovery required");
            return;
        }
        if (phase == PAUSED || phase == COMPLETE) return;
        BlockPos target = BlockPos.of(tag.getLong(phase == TO_SOURCE ? SOURCE : DESTINATION));
        if (!level.hasChunkAt(target)) return; // Never force distant chunk loads.
        if (citizen.distanceToSqr(target.getX() + .5, target.getY() + .5, target.getZ() + .5) > 6.25) {
            citizen.getNavigation().moveTo(target.getX() + .5, target.getY(), target.getZ() + .5, .85);
            return;
        }

        BlockEntity entity = level.getBlockEntity(target);
        if (entity == null) {
            pause(tag, "Missing block inventory");
            return;
        }
        if (phase == TO_SOURCE) {
            // Preflight is not an atomic reservation, but avoids removing wheat
            // when the destination is already known to reject it.
            BlockPos destination = BlockPos.of(tag.getLong(DESTINATION));
            if (!level.hasChunkAt(destination)) return;
            BlockEntity output = level.getBlockEntity(destination);
            if (output == null || !canAccept(output, new ItemStack(Items.WHEAT))) {
                pause(tag, "Destination unavailable or full before pickup");
                return;
            }
            ItemStack taken = extractWheat(entity);
            if (taken.isEmpty()) {
                pause(tag, "No wheat available");
                return;
            }
            // Save cargo in citizen data; never issue a second extraction until delivered.
            tag.put(CARGO, taken.save(new CompoundTag()));
            tag.putInt(PHASE, TO_DEST);
            entity.setChanged();
        } else {
            ItemStack cargo = ItemStack.of(tag.getCompound(CARGO));
            if (cargo.isEmpty()) {
                pause(tag, "Cargo missing");
                return;
            }
            ItemStack remaining = insert(entity, cargo);
            if (remaining.isEmpty()) {
                tag.remove(CARGO);
                tag.putInt(PHASE, COMPLETE);
                HaulClaims.release(level, claimedSource, citizen.getUUID());
            } else {
                tag.put(CARGO, remaining.save(new CompoundTag()));
                pause(tag, "Destination full or incompatible");
            }
            entity.setChanged();
        }
    }

    private static void pause(CompoundTag tag, String message) {
        tag.putInt(PHASE, PAUSED);
        tag.putString(ERROR, message);
    }

    /**
     * Safe operator cancellation only before pickup: no cargo can be orphaned.
     * Cargo-bearing jobs must be delivered or reconciled, never silently cancelled.
     */
    public static boolean cancelBeforePickup(ServerLevel level, Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!tag.contains(PHASE) || tag.getInt(PHASE) == COMPLETE || tag.contains(CARGO))
            return false;
        BlockPos source = BlockPos.of(tag.getLong(SOURCE));
        tag.putInt(PHASE, COMPLETE);
        tag.remove(ERROR);
        HaulClaims.release(level, source, citizen.getUUID());
        return true;
    }

    public static boolean resume(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (tag.getInt(PHASE) != PAUSED) return false;
        tag.putInt(PHASE, tag.contains(CARGO) ? TO_DEST : TO_SOURCE);
        tag.remove(ERROR);
        return true;
    }

    private static boolean canAccept(BlockEntity block, ItemStack input) {
        LazyOptional<IItemHandler> capability =
            block.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (capability.isPresent()) {
            IItemHandler handler = capability.orElseThrow(IllegalStateException::new);
            for (int i = 0; i < handler.getSlots(); i++) {
                ItemStack remainder = handler.insertItem(i, input.copy(), true);
                if (remainder.getCount() < input.getCount()) return true;
            }
            return false;
        }
        if (block instanceof Container container) {
            for (int i = 0; i < container.getContainerSize(); i++) {
                if (!container.canPlaceItem(i, input)) continue;
                ItemStack existing = container.getItem(i);
                if (existing.isEmpty()) return true;
                if (ItemStack.isSameItemSameTags(existing, input)
                    && existing.getCount() < Math.min(
                        container.getMaxStackSize(), existing.getMaxStackSize())) return true;
            }
        }
        return false;
    }

    private static ItemStack extractWheat(BlockEntity block) {
        LazyOptional<IItemHandler> capability = block.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (capability.isPresent()) {
            IItemHandler handler = capability.orElseThrow(IllegalStateException::new);
            for (int i = 0; i < handler.getSlots(); i++) {
                ItemStack stack = handler.getStackInSlot(i);
                if (stack.is(Items.WHEAT)) return handler.extractItem(i, 1, false);
            }
            return ItemStack.EMPTY;
        }
        if (block instanceof Container container) {
            for (int i = 0; i < container.getContainerSize(); i++) {
                ItemStack stack = container.getItem(i);
                if (stack.is(Items.WHEAT)) return container.removeItem(i, 1);
            }
        }
        return ItemStack.EMPTY;
    }

    private static ItemStack insert(BlockEntity block, ItemStack cargo) {
        LazyOptional<IItemHandler> capability = block.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (capability.isPresent()) {
            IItemHandler handler = capability.orElseThrow(IllegalStateException::new);
            ItemStack remaining = cargo.copy();
            for (int i = 0; i < handler.getSlots() && !remaining.isEmpty(); i++) {
                remaining = handler.insertItem(i, remaining, false);
            }
            return remaining;
        }
        if (block instanceof Container container) {
            ItemStack remaining = cargo.copy();
            for (int i = 0; i < container.getContainerSize() && !remaining.isEmpty(); i++) {
                ItemStack existing = container.getItem(i);
                if (existing.isEmpty() && container.canPlaceItem(i, remaining)) {
                    container.setItem(i, remaining.copy());
                    return ItemStack.EMPTY;
                }
                if (ItemStack.isSameItemSameTags(existing, remaining)
                    && container.canPlaceItem(i, remaining)) {
                    int space = Math.min(container.getMaxStackSize(), existing.getMaxStackSize()) - existing.getCount();
                    int moved = Math.min(space, remaining.getCount());
                    if (moved > 0) {
                        existing.grow(moved);
                        remaining.shrink(moved);
                    }
                }
            }
            return remaining;
        }
        return cargo;
    }
}
