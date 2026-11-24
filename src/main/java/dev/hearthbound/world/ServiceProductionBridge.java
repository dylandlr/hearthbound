package dev.hearthbound.world;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import java.util.UUID;
import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.LinkedHashMap;
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
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;

/**
 * Narrow physical adapter for one reserved wheat-to-flour production cycle.
 * The original Sable input job and mill reservation remain intact until all
 * witnessed output reaches a real buffer. Inventory calls run on the server
 * thread. Interrupted calls and restored custody are held by the service owner;
 * this adapter does not pretend SavedData and entity/chest NBT are crash atomic.
 */
final class ServiceProductionBridge {
    private static final ResourceLocation FLOUR = new ResourceLocation("create", "wheat_flour");
    static final String PHASE = "productionPhase", CARGO = "productionCargo";
    record Stock(boolean known, int units, String reason) {}
    record Proof(UUID job, UUID citizen, long machine, long startTick, long processTick, int units,
                 String physicalEvidence) {}
    record Delivery(int before, int after, int units, long tick, Map<String, Integer> items,
                    Map<String, Integer> beforeItems, Map<String, Integer> afterItems) {}
    private ServiceProductionBridge() {}

    static Stock inspectFlour(ServerLevel level, BlockPos position, Villager citizen) {
        if (!level.hasChunkAt(position)) return new Stock(false, 0, "CHUNK_UNLOADED");
        if (distance(citizen, position) > 256) return new Stock(false, 0, "OUT_OF_SENSOR_RANGE");
        BlockEntity entity = level.getBlockEntity(position);
        if (!(entity instanceof Container inventory)) return new Stock(false, 0, "REQUIRES_CONTAINER_BUFFER");
        return new Stock(true, count(inventory), "OBSERVED");
    }

    static void begin(CompoundTag memory, BlockPos machine) {
        memory.putLong("machine", machine.asLong());
        memory.putString(PHASE, "AWAIT_PROCESS");
        memory.remove(CARGO); memory.remove("outputUnits"); memory.remove("outputDeliveredTick");
        memory.remove("outputPickedTick"); memory.remove("physicalEvidence"); memory.remove("releasedMill");
    }

    static Proof verify(ServerLevel level, Villager citizen, CompoundTag memory, Scope scope) {
        if (!memory.hasUUID("job") || !memory.hasUUID("commitment") || !memory.contains("machine"))
            throw new IllegalStateException("Missing production ownership");
        UUID job = memory.getUUID("job"); BlockPos position = BlockPos.of(memory.getLong("machine"));
        if (!scope.world().equals(HearthboundWorldIdentity.get(level))
                || !scope.dimension().equals(level.dimension().location().toString()))
            throw new IllegalStateException("Foreign production scope");
        var assignment = SableHauling.completedAssignment(level, citizen, job, position);
        if (assignment.source() != memory.getLong("source"))
            throw new IllegalStateException("Production input source changed");
        MillProcessReceipts.exportVerified(level, scope.world(), job, citizen.getUUID(), position);
        var callback = MillProcessReceipts.observedCallback(level, job);
        long inputTick = citizen.getPersistentData().getCompound("hearthbound.haul").getLong("physicalDeliveredTick");
        if (callback == null || callback.startTick() < inputTick || callback.tick() > level.getGameTime())
            throw new IllegalStateException("Invalid production chronology");
        int units = callback.flourAfter() - callback.flourBefore();
        if (units < 1 || units > 64) throw new IllegalStateException("Unsupported production batch size");
        String identity = scope.world() + "|" + scope.dimension() + "|create-mill|" + job
            + "|" + position.asLong() + "|" + callback.startTick() + "|" + callback.tick();
        return new Proof(job, citizen.getUUID(), position.asLong(), callback.startTick(), callback.tick(), units, identity);
    }

    static boolean callbackPresent(ServerLevel level, CompoundTag memory) {
        return memory.hasUUID("job") && MillProcessReceipts.recorded(level, memory.getUUID("job"));
    }

    static Proof collect(ServerLevel level, Villager citizen, CompoundTag memory, Scope scope) {
        if (!"AWAIT_PROCESS".equals(memory.getString(PHASE)) || memory.contains(CARGO))
            throw new IllegalStateException("Output pickup is not retryable");
        Proof proof = verify(level, citizen, memory, scope);
        BlockPos position = BlockPos.of(proof.machine());
        if (distance(citizen, position) > 6.25) throw new IllegalStateException("Citizen is too far from mill output");
        MillstoneBlockEntity mill = loadedMill(level, position);
        requireEmptyInput(mill);
        int before = exactFlourOutput(mill);
        List<ItemStack> observedOutput = new ArrayList<>();
        for (int i = 0; i < mill.outputInv.getSlots(); i++) {
            ItemStack stack = mill.outputInv.getStackInSlot(i); if (!stack.isEmpty()) observedOutput.add(stack.copy());
        }
        Map<String, Integer> beforeItems = contents(observedOutput);
        if (before != proof.units()) throw new IllegalStateException("Callback and physical mill output disagree");
        memory.putString(PHASE, "EXTRACTING"); // A thrown/interrupting call must never be retried.
        List<ItemStack> carried = new ArrayList<>();
        for (int slot = 0; slot < mill.outputInv.getSlots(); slot++) {
            ItemStack stack = mill.outputInv.getStackInSlot(slot);
            if (stack.isEmpty()) continue;
            ItemStack taken = mill.outputInv.extractItem(slot, stack.getCount(), false);
            if (!taken.isEmpty()) carried.add(taken.copy());
            // Preserve every returned item before checking or calling another slot.
            saveCargo(memory, carried);
            if (taken.isEmpty() || !allowedOutput(taken))
                throw new IllegalStateException("Unexpected mill output extraction");
        }
        mill.setChanged();
        if (flourCount(carried) != before || !contents(carried).equals(beforeItems)
                || exactFlourOutput(mill) != 0 || !allOutputEmpty(mill))
            throw new IllegalStateException("Mill output extraction did not conserve its batch");
        memory.put("outputCargoSnapshot", cargoTag(carried));
        memory.put("outputBeforeCollection", cargoTag(observedOutput));
        memory.putInt("outputUnits", proof.units()); memory.putLong("outputPickedTick", level.getGameTime());
        memory.putLong("processStartTick", proof.startTick()); memory.putLong("processTick", proof.processTick());
        memory.putString("physicalEvidence", proof.physicalEvidence()); memory.putString(PHASE, "TO_OUTPUT");
        return proof;
    }

    /** Returns null for a full buffer without mutating or discarding cargo. */
    static Delivery deliver(ServerLevel level, Villager citizen, CompoundTag memory, Scope scope) {
        if (!"TO_OUTPUT".equals(memory.getString(PHASE)) || !memory.contains(CARGO))
            throw new IllegalStateException("Output delivery is not retryable");
        Proof proof = verify(level, citizen, memory, scope);
        requireEmptyMachine(level, BlockPos.of(proof.machine()));
        BlockPos destination = BlockPos.of(memory.getLong("goal"));
        if (!level.hasChunkAt(destination) || distance(citizen, destination) > 6.25)
            throw new IllegalStateException("Output buffer is not physically reachable now");
        if (!(level.getBlockEntity(destination) instanceof Container inventory))
            throw new IllegalStateException("Output buffer must be a loaded container");
        List<ItemStack> cargo = readCargo(memory, CARGO);
        List<ItemStack> original = readCargo(memory, "outputCargoSnapshot");
        if (flourCount(cargo) != proof.units() || !sameCargo(cargo, original)
                || memory.getInt("outputUnits") != proof.units()
                || !proof.physicalEvidence().equals(memory.getString("physicalEvidence")))
            throw new IllegalStateException("Output custody differs from verified production");
        // Simulate the complete mixed batch on copied slots, preserving per-item
        // capacities. Checking each stack against the original slots would count
        // the same free slot more than once.
        List<ItemStack> simulated = new ArrayList<>();
        for (int i = 0; i < inventory.getContainerSize(); i++) simulated.add(inventory.getItem(i).copy());
        for (ItemStack stack : cargo) if (!fit(inventory, simulated, stack)) return null;
        int before = count(inventory), units = proof.units();
        Map<String, Integer> beforeItems = contents(inventory), moved = contents(cargo);
        memory.putString(PHASE, "INSERTING");
        for (ItemStack stack : cargo) {
            for (int i = 0; i < inventory.getContainerSize() && !stack.isEmpty(); i++) {
                if (!inventory.canPlaceItem(i, stack)) continue;
                ItemStack present = inventory.getItem(i);
                if (!present.isEmpty() && !ItemStack.isSameItemSameTags(present, stack)) continue;
                int amount = Math.min(stack.getCount(), Math.max(0,
                    Math.min(inventory.getMaxStackSize(), stack.getMaxStackSize()) - present.getCount()));
                if (amount == 0) continue;
                ItemStack inserted = present.isEmpty() ? stack.copy() : present.copy();
                inserted.setCount(present.getCount() + amount); inventory.setItem(i, inserted);
                stack.shrink(amount); saveCargo(memory, cargo);
            }
        }
        inventory.setChanged();
        int after = count(inventory); Map<String, Integer> afterItems = contents(inventory);
        Map<String, Integer> expected = new LinkedHashMap<>(beforeItems);
        moved.forEach((item, amount) -> expected.merge(item, amount, Integer::sum));
        if (cargo.stream().anyMatch(stack -> !stack.isEmpty()) || after - before != units || !expected.equals(afterItems))
            throw new IllegalStateException("Output insertion did not conserve its entire mixed batch");
        memory.putInt("outputBefore", before); memory.putInt("outputAfter", after);
        memory.putLong("outputDeliveredTick", level.getGameTime()); memory.putString(PHASE, "OUTPUT_DELIVERED");
        return new Delivery(before, after, units, level.getGameTime(), moved, beforeItems, afterItems);
    }

    static Proof release(ServerLevel level, Villager citizen, CompoundTag memory, Scope scope) {
        if (!"OUTPUT_DELIVERED".equals(memory.getString(PHASE)) || memory.contains(CARGO)
                || memory.getBoolean("releasedMill")) throw new IllegalStateException("Output cycle is not ready for release");
        Proof proof = verify(level, citizen, memory, scope);
        if (memory.getLong("outputDeliveredTick") < proof.processTick()
                || memory.getLong("outputDeliveredTick") > level.getGameTime()
                || memory.getInt("outputAfter") - memory.getInt("outputBefore") != proof.units())
            throw new IllegalStateException("Output delivery witness mismatch");
        requireEmptyMachine(level, BlockPos.of(proof.machine()));
        MillReservations.releaseCompleted(level, BlockPos.of(proof.machine()), proof.job(), citizen);
        MillExperimentTrace.finalized(citizen, proof.job());
        memory.putBoolean("releasedMill", true); memory.putString(PHASE, "FINALIZED");
        return proof;
    }

    private static MillstoneBlockEntity loadedMill(ServerLevel level, BlockPos position) {
        if (!level.hasChunkAt(position) || !(level.getBlockEntity(position) instanceof MillstoneBlockEntity mill))
            throw new IllegalStateException("Loaded Create millstone required");
        return mill;
    }
    private static void requireEmptyInput(MillstoneBlockEntity mill) {
        for (int i = 0; i < mill.inputInv.getSlots(); i++)
            if (!mill.inputInv.getStackInSlot(i).isEmpty()) throw new IllegalStateException("Unexpected mill input remains");
    }
    private static int exactFlourOutput(MillstoneBlockEntity mill) {
        int total = 0;
        for (int i = 0; i < mill.outputInv.getSlots(); i++) {
            ItemStack stack = mill.outputInv.getStackInSlot(i);
            if (stack.isEmpty()) continue;
            if (!allowedOutput(stack)) throw new IllegalStateException("Unexpected mill output item");
            if (isFlour(stack)) total += stack.getCount();
        }
        return total;
    }
    private static void requireEmptyMachine(ServerLevel level, BlockPos position) {
        MillstoneBlockEntity mill = loadedMill(level, position); requireEmptyInput(mill);
        if (exactFlourOutput(mill) != 0 || !allOutputEmpty(mill)) throw new IllegalStateException("Unexpected output appeared after collection");
    }
    static Map<String, Integer> outputItems(CompoundTag memory) { return contents(readCargo(memory, "outputCargoSnapshot")); }
    private static boolean allowedOutput(ItemStack stack) { return isFlour(stack) || stack.is(Items.WHEAT_SEEDS); }
    private static boolean allOutputEmpty(MillstoneBlockEntity mill) {
        for (int i = 0; i < mill.outputInv.getSlots(); i++) if (!mill.outputInv.getStackInSlot(i).isEmpty()) return false;
        return true;
    }
    private static int flourCount(List<ItemStack> stacks) { return stacks.stream().filter(ServiceProductionBridge::isFlour).mapToInt(ItemStack::getCount).sum(); }
    private static ListTag cargoTag(List<ItemStack> stacks) {
        ListTag tag = new ListTag();
        for (ItemStack stack : stacks) if (!stack.isEmpty()) tag.add(stack.save(new CompoundTag()));
        return tag;
    }
    private static void saveCargo(CompoundTag memory, List<ItemStack> stacks) {
        ListTag tag = cargoTag(stacks); if (tag.isEmpty()) memory.remove(CARGO); else memory.put(CARGO, tag);
    }
    private static List<ItemStack> readCargo(CompoundTag memory, String key) {
        ListTag tag = memory.getList(key, Tag.TAG_COMPOUND); List<ItemStack> stacks = new ArrayList<>();
        if (tag.size() > 16) throw new IllegalStateException("Output custody capacity exhausted");
        for (int i = 0; i < tag.size(); i++) {
            ItemStack stack = ItemStack.of(tag.getCompound(i));
            if (stack.isEmpty() || !allowedOutput(stack)) throw new IllegalStateException("Invalid output cargo");
            stacks.add(stack);
        }
        return stacks;
    }
    private static boolean sameCargo(List<ItemStack> left, List<ItemStack> right) {
        if (left.size() != right.size()) return false;
        for (int i = 0; i < left.size(); i++) if (!ItemStack.isSameItemSameTags(left.get(i), right.get(i))
                || left.get(i).getCount() != right.get(i).getCount()) return false;
        return true;
    }
    private static boolean fit(Container inventory, List<ItemStack> slots, ItemStack original) {
        ItemStack stack = original.copy();
        for (int i = 0; i < slots.size() && !stack.isEmpty(); i++) {
            if (!inventory.canPlaceItem(i, stack)) continue;
            ItemStack present = slots.get(i);
            if (!present.isEmpty() && !ItemStack.isSameItemSameTags(present, stack)) continue;
            int moved = Math.min(stack.getCount(), Math.max(0,
                Math.min(inventory.getMaxStackSize(), stack.getMaxStackSize()) - present.getCount()));
            if (moved == 0) continue;
            ItemStack next = present.isEmpty() ? stack.copy() : present.copy(); next.setCount(present.getCount() + moved);
            slots.set(i, next); stack.shrink(moved);
        }
        return stack.isEmpty();
    }
    private static Map<String, Integer> contents(List<ItemStack> stacks) {
        Map<String, Integer> result = new LinkedHashMap<>();
        for (ItemStack stack : stacks) if (!stack.isEmpty()) result.merge(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString(), stack.getCount(), Integer::sum);
        return result;
    }
    private static Map<String, Integer> contents(Container inventory) {
        List<ItemStack> stacks = new ArrayList<>();
        for (int i = 0; i < inventory.getContainerSize(); i++) stacks.add(inventory.getItem(i));
        return contents(stacks);
    }
    private static boolean isFlour(ItemStack stack) { return FLOUR.equals(BuiltInRegistries.ITEM.getKey(stack.getItem())); }
    private static int count(Container inventory) {
        int total = 0;
        for (int i = 0; i < inventory.getContainerSize(); i++) {
            ItemStack stack = inventory.getItem(i); if (isFlour(stack)) total += stack.getCount();
        }
        return total;
    }
    private static double distance(Villager citizen, BlockPos p) {
        return citizen.distanceToSqr(p.getX() + .5, p.getY() + .5, p.getZ() + .5);
    }
}
