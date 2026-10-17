package dev.hearthbound.world;

import net.minecraft.core.BlockPos;
import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryStudyRuntime;
import java.util.Set;
import java.util.UUID;
import java.util.HashSet;
import java.util.WeakHashMap;
import net.minecraft.server.MinecraftServer;
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
    private static final int QUARANTINED = 4;
    private static final int INSERTING = 5;
    private static final String JOB_ID = "jobId";
    private static final String FAULT = "faultInsertion";

    /**
     * Dedicated test-world fault injection. NEVER expose through normal
     * player commands; admin permission is enforced by SableController.
     */
    public static void injectInsertionFault(Villager citizen, boolean afterInsert) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!active(citizen) || !tag.hasUUID(JOB_ID))
            throw new IllegalStateException("No active hauling job");
        tag.putString(FAULT, afterInsert ? "after" : "before");
    }

    // Runtime-only provenance: intentionally NOT restored after a server restart.
    // A restored cargo-bearing job cannot prove whether destination insertion
    // committed before the last crash, so it must be quarantined for review.
    private static final WeakHashMap<MinecraftServer, Set<UUID>> LIVE_JOBS = new WeakHashMap<>();

    private static synchronized void markLive(MinecraftServer server, UUID job) {
        LIVE_JOBS.computeIfAbsent(server, ignored -> new HashSet<>()).add(job);
    }

    private static synchronized boolean isLive(MinecraftServer server, UUID job) {
        return LIVE_JOBS.containsKey(server) && LIVE_JOBS.get(server).contains(job);
    }

    public static synchronized void serverStopped(MinecraftServer server) {
        LIVE_JOBS.remove(server);
    }

    private static void quarantine(CompoundTag tag, String reason) {
        tag.putInt(PHASE, QUARANTINED);
        tag.putString(ERROR, reason);
    }

    private SableHauling() {}

    public static void assign(ServerLevel level, Villager citizen, BlockPos source, BlockPos destination) {
        CitizenWorkOwnership.assertFree(citizen);
        if (source.equals(destination)) throw new IllegalArgumentException("same endpoint");
        if (AutonomousLibraryStudy.active(citizen)
                || LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING)
            throw new IllegalStateException("Citizen has an active library assignment");
        if (active(citizen)) throw new IllegalStateException("already carrying out a haul");
        UUID job = UUID.randomUUID();
        if (!HaulClaims.claim(level, source, citizen.getUUID()))
            throw new IllegalStateException("source already claimed by another citizen");
        if (!MillReservations.acquireIfMill(level, destination, job, citizen.getUUID())) {
            HaulClaims.release(level, source, citizen.getUUID());
            throw new IllegalStateException("millstone reserved by another Hearthbound job");
        }
        CompoundTag tag = new CompoundTag();
        tag.putLong(SOURCE, source.asLong());
        tag.putLong(DESTINATION, destination.asLong());
        tag.putInt(PHASE, TO_SOURCE);
        tag.putUUID(JOB_ID, job);
        citizen.getPersistentData().put(KEY, tag);
        markLive(level.getServer(), job);
        CitizenWorkOwnership.assigned(citizen, CitizenWorkOwnership.Kind.HAUL);
    }

    /** Only a fully completed delivery can be used for audited mill release. */
    public static boolean completedJob(Villager citizen, UUID expected, BlockPos destination) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        return tag.getInt(PHASE) == COMPLETE && tag.hasUUID(JOB_ID)
            && tag.getUUID(JOB_ID).equals(expected)
            && tag.contains(DESTINATION) && tag.getLong(DESTINATION) == destination.asLong()
            && !tag.contains(CARGO);
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
            case QUARANTINED -> "QUARANTINED (operator review): " + tag.getString(ERROR);
            case INSERTING -> "Inventory insertion in progress";
            default -> "Paused: " + tag.getString(ERROR);
        };
    }

    public static void tick(ServerLevel level, Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!tag.contains(PHASE)) return;
        int phase = tag.getInt(PHASE);
        if (phase == QUARANTINED || phase == COMPLETE) return;
        if (phase == INSERTING) {
            quarantine(tag, "Insertion interrupted or state restored; manual reconciliation required");
            return;
        }
        // Fail closed if cargo is restored from disk or lacks a current job identity.
        // No inference from destination item counts is sufficient for automatic retry.
        if (tag.contains(CARGO)
                && (!tag.hasUUID(JOB_ID)
                    || !isLive(level.getServer(), tag.getUUID(JOB_ID)))) {
            quarantine(tag, "Cargo state restored or unrecognized; manual reconciliation required");
            return;
        }
        // Jobs that have not picked up cargo may safely continue after restart.
        if (!tag.contains(CARGO) && tag.hasUUID(JOB_ID)
                && !isLive(level.getServer(), tag.getUUID(JOB_ID))) {
            markLive(level.getServer(), tag.getUUID(JOB_ID));
        }
        // A mill reservation is mandatory throughout the task, not merely at
        // assignment. Never pick up or deposit wheat after losing ownership.
        BlockPos jobDestination = BlockPos.of(tag.getLong(DESTINATION));
        if (MillReservations.isMill(level, jobDestination) &&
                (!tag.hasUUID(JOB_ID) || !MillReservations.matches(
                    level, jobDestination, tag.getUUID(JOB_ID), citizen.getUUID()))) {
            if (tag.contains(CARGO)) quarantine(tag, "Mill reservation lost with cargo in transit");
            else pause(tag, "Mill reservation not owned by hauling job");
            return;
        }
        BlockPos claimedSource = BlockPos.of(tag.getLong(SOURCE));
        if (phase != COMPLETE && !HaulClaims.claim(level, claimedSource, citizen.getUUID())) {
            pause(tag, "Source claimed by another citizen; manual recovery required");
            return;
        }
        if (phase == PAUSED || phase == COMPLETE || phase == QUARANTINED) return;
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
            // At the pickup boundary, reject unexpected items in an
            // experimentally reserved mill before removing any wheat.
            if (MillReservations.isMill(level, destination)
                    && !MillReservations.preDeliveryClean(level, destination,
                        tag.getUUID(JOB_ID), citizen.getUUID())) {
                pause(tag, "Mill experiment tainted before pickup; operator review required");
                return;
            }
            BlockEntity output = level.getBlockEntity(destination);
            boolean acceptable = output != null && (!MillReservations.isMill(level, destination)
                ? canAccept(output, new ItemStack(Items.WHEAT))
                : MillTransferGate.authorize(level, destination, tag.getUUID(JOB_ID),
                    citizen.getUUID(), true,
                    () -> canAccept(output, new ItemStack(Items.WHEAT))));
            if (!acceptable) {
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
            // Check once more immediately before depositing the carried item.
            // If the environment changed while Sable walked, quarantine the
            // cargo and keep the reservation tainted for operator review.
            if (MillReservations.isMill(level, target)
                    && !MillReservations.preDeliveryClean(level, target,
                        tag.getUUID(JOB_ID), citizen.getUUID())) {
                quarantine(tag, "Mill experiment tainted during delivery; cargo quarantined");
                return;
            }
            // A persistent in-progress marker prevents the next tick from silently
            // trying insertion again if this call fails partway through.
            tag.putInt(PHASE, INSERTING);
            if (tag.hasUUID(JOB_ID)) {
                MillExperimentTrace.beforeDelivery(level, citizen, tag.getUUID(JOB_ID), target, cargo);
            }
            ItemStack remaining;
            try {
                String fault = tag.getString(FAULT);
                tag.remove(FAULT);
                if ("before".equals(fault)) {
                    throw new IllegalStateException("Injected failure before inventory insertion");
                }
                remaining = !MillReservations.isMill(level, target)
                    ? insert(entity, cargo)
                    : MillTransferGate.authorize(level, target, tag.getUUID(JOB_ID),
                        citizen.getUUID(), false, () -> insert(entity, cargo));
                if ("after".equals(fault)) {
                    throw new IllegalStateException("Injected failure after inventory insertion");
                }
            } catch (RuntimeException ex) {
                quarantine(tag, "Inventory insertion raised an exception; review contents");
                entity.setChanged();
                return;
            }
            if (remaining.isEmpty()) {
                if (tag.hasUUID(JOB_ID)) {
                    MillExperimentTrace.deliveryComplete(level, citizen, tag.getUUID(JOB_ID));
                }
                tag.remove(CARGO);
                tag.putInt(PHASE, COMPLETE);
                HaulClaims.release(level, claimedSource, citizen.getUUID());
            } else {
                tag.put(CARGO, remaining.save(new CompoundTag()));
                quarantine(tag, "Incomplete insertion; reconcile remaining cargo and destination");
            }
            entity.setChanged();
        }
    }

    /**
     * Read-only operator snapshot. Inventory counts are observations, never
     * evidence that a particular job caused those items to arrive.
     */
    public static String audit(ServerLevel level, Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!tag.contains(PHASE)) return "AUDIT: no hauling job";
        BlockPos source = BlockPos.of(tag.getLong(SOURCE));
        BlockPos destination = BlockPos.of(tag.getLong(DESTINATION));
        UUID owner = HaulClaims.owner(level, source);
        String claim = owner == null ? "unclaimed"
            : owner.equals(citizen.getUUID()) ? "owned" : "OTHER:" + owner;
        String job = tag.hasUUID(JOB_ID) ? tag.getUUID(JOB_ID).toString() : "legacy/no-id";
        ItemStack carried = tag.contains(CARGO) ? ItemStack.of(tag.getCompound(CARGO)) : ItemStack.EMPTY;
        String sourceCount = observedWheat(level, source);
        String destinationCount = observedWheat(level, destination);
        return "AUDIT job=" + job + " phase=" + tag.getInt(PHASE)
            + " cargo=" + carried.getCount() + "x" + carried.getItem()
            + " source=" + source + " wheat=" + sourceCount
            + " destination=" + destination + " wheat=" + destinationCount
            + " claim=" + claim + " status=" + status(citizen)
            + " [observations only; no reconciliation performed]";
    }

    private static String observedWheat(ServerLevel level, BlockPos pos) {
        if (!level.hasChunkAt(pos)) return "CHUNK_UNLOADED";
        BlockEntity block = level.getBlockEntity(pos);
        if (block == null) return "NO_INVENTORY";
        LazyOptional<IItemHandler> cap = block.getCapability(ForgeCapabilities.ITEM_HANDLER);
        int count = 0;
        if (cap.isPresent()) {
            IItemHandler handler = cap.orElseThrow(IllegalStateException::new);
            for (int i = 0; i < handler.getSlots(); i++) {
                ItemStack stack = handler.getStackInSlot(i);
                if (stack.is(Items.WHEAT)) count += stack.getCount();
            }
            return Integer.toString(count);
        }
        if (block instanceof Container container) {
            for (int i = 0; i < container.getContainerSize(); i++) {
                ItemStack stack = container.getItem(i);
                if (stack.is(Items.WHEAT)) count += stack.getCount();
            }
            return Integer.toString(count);
        }
        return "UNSUPPORTED_INVENTORY";
    }

    /**
     * Operator finalization ONLY after cargo has been separately reconciled.
     * No item movement, replacement, or research reward occurs here.
     * The expected UUID prevents silently closing a different assignment.
     */
    public static void closeReconciled(ServerLevel level, Villager citizen, UUID expectedJob) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (tag.getInt(PHASE) != QUARANTINED || !tag.hasUUID(JOB_ID)
                || !tag.getUUID(JOB_ID).equals(expectedJob)) {
            throw new IllegalStateException("Job is not the expected quarantined job");
        }
        if (tag.contains(CARGO) && !ItemStack.of(tag.getCompound(CARGO)).isEmpty()) {
            throw new IllegalStateException("Cargo still held: reconcile physical items before closing");
        }
        BlockPos source = BlockPos.of(tag.getLong(SOURCE));
        BlockPos destination = BlockPos.of(tag.getLong(DESTINATION));
        if (!level.hasChunkAt(source) || !level.hasChunkAt(destination)) {
            throw new IllegalStateException("Both endpoint chunks must be loaded");
        }
        if (!citizen.getUUID().equals(HaulClaims.owner(level, source))) {
            throw new IllegalStateException("Source claim does not belong to this citizen");
        }
        // The audit is a durable villager record, not a claim of physical
        // delivery or an automated assignment of learning credit.
        CompoundTag record = new CompoundTag();
        record.putUUID("jobId", expectedJob);
        record.putLong("tick", level.getGameTime());
        record.putString("outcome", "operator_closed_no_cargo");
        record.putString("priorReason", tag.getString(ERROR));
        record.putString("sourceWheatObserved", observedWheat(level, source));
        record.putString("destinationWheatObserved", observedWheat(level, destination));
        citizen.getPersistentData().put("hearthbound.lastReconciliation", record);
        tag.putInt(PHASE, COMPLETE);
        tag.remove(ERROR);
        tag.remove(FAULT);
        HaulClaims.release(level, source, citizen.getUUID());
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
        if (!tag.contains(PHASE) || tag.getInt(PHASE) == COMPLETE
            || tag.getInt(PHASE) == QUARANTINED || tag.contains(CARGO))
            return false;
        BlockPos source = BlockPos.of(tag.getLong(SOURCE));
        BlockPos destination = BlockPos.of(tag.getLong(DESTINATION));
        if (MillReservations.isMill(level, destination)) {
            if (!tag.hasUUID(JOB_ID) || !MillReservations.releaseUnpicked(
                    level, destination, tag.getUUID(JOB_ID), citizen.getUUID())) return false;
        }
        tag.putInt(PHASE, COMPLETE);
        tag.remove(ERROR);
        HaulClaims.release(level, source, citizen.getUUID());
        return true;
    }

    public static boolean resume(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (tag.getInt(PHASE) != PAUSED || tag.contains(CARGO)) return false;
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
