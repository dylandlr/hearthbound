package dev.hearthbound.world;

import java.util.UUID;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraftforge.common.capabilities.ForgeCapabilities;
import net.minecraftforge.items.IItemHandler;
import net.minecraftforge.common.util.LazyOptional;

/**
 * Physical, per-citizen mill experiment trace.
 *
 * A matched wheat-to-flour observation is candidate evidence, NOT a Create
 * processing-completion event. No learning rewards or recipe unlocks here.
 * No autonomous transfer attribution under concurrent mill usage.
 */
public final class MillExperimentTrace {
    private static final String KEY = "hearthbound.millExperiment";
    private static final ResourceLocation MILL_ID = new ResourceLocation("create", "millstone");
    private static final ResourceLocation FLOUR_ID = new ResourceLocation("create", "wheat_flour");

    private MillExperimentTrace() {}

    private static int count(ServerLevel level, BlockPos pos, ResourceLocation wanted) {
        if (!level.hasChunkAt(pos)) return -1;
        if (!MILL_ID.equals(BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock())))
            return -1;
        BlockEntity entity = level.getBlockEntity(pos);
        if (entity == null) return -1;
        LazyOptional<IItemHandler> capability = entity.getCapability(ForgeCapabilities.ITEM_HANDLER);
        if (!capability.isPresent()) return -1;
        IItemHandler inventory = capability.orElseThrow(IllegalStateException::new);
        int amount = 0;
        for (int slot = 0; slot < inventory.getSlots(); slot++) {
            ItemStack stack = inventory.getStackInSlot(slot);
            if (wanted.equals(BuiltInRegistries.ITEM.getKey(stack.getItem())))
                amount += stack.getCount();
        }
        return amount;
    }

    public static void beforeDelivery(ServerLevel level, Villager citizen, UUID jobId,
                                      BlockPos machine, ItemStack input) {
        if (!input.is(Items.WHEAT) || input.getCount() != 1) return;
        int baseline = count(level, machine, FLOUR_ID);
        if (baseline < 0) return; // Not a loaded Create millstone with readable inventory.
        CompoundTag trace = new CompoundTag();
        trace.putUUID("jobId", jobId);
        trace.putLong("millstone", machine.asLong());
        trace.putLong("startedTick", level.getGameTime());
        trace.putInt("baselineFlour", baseline);
        trace.putString("input", "minecraft:wheat");
        trace.putString("phase", "INSERTION_PENDING");
        citizen.getPersistentData().put(KEY, trace);
    }

    public static void deliveryComplete(ServerLevel level, Villager citizen, UUID jobId) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (!trace.hasUUID("jobId") || !trace.getUUID("jobId").equals(jobId)
                || !"INSERTION_PENDING".equals(trace.getString("phase"))) return;
        BlockPos machine = BlockPos.of(trace.getLong("millstone"));
        if (!(level.getBlockEntity(machine) instanceof MillstoneBlockEntity mill)) return;
        ItemStack stack = mill.inputInv.getStackInSlot(0);
        // This observation is taken immediately after the real inventory
        // insertion succeeded. Later callback validation uses its exact input.
        if (!stack.is(Items.WHEAT) || stack.getCount() != 1
                || count(level, machine, FLOUR_ID) != trace.getInt("baselineFlour")) {
            MillReservations.taint(level, machine, jobId, citizen.getUUID());
            return;
        }
        trace.putInt("authorizedInputCount", 1);
        trace.putLong("authorizedTick", level.getGameTime());
        trace.putString("phase", "DELIVERED");
    }

    /** Matches only a successfully committed one-wheat Hearthbound insertion. */
    public static boolean matchesAuthorizedProcessing(Villager citizen, BlockPos machine,
            long now, int wheatBefore, int flourBefore) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        return matchesDelivery(citizen, machine, now)
            && trace.getInt("authorizedInputCount") == 1
            && wheatBefore == 1
            && flourBefore == trace.getInt("baselineFlour")
            && trace.contains("authorizedTick")
            && now >= trace.getLong("authorizedTick");
    }

    /**
     * Server-tick Create-state observation for the existing delivered job.
     * It is an observed cycle, not a direct invocation from Create.process().
     */
    public static void sampleCycle(ServerLevel level, Villager citizen) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (!trace.hasUUID("jobId")) return;
        String phase = trace.getString("phase");
        if (!("DELIVERED".equals(phase) || "PROCESSING_OBSERVED".equals(phase))) return;
        BlockPos pos = BlockPos.of(trace.getLong("millstone"));
        if (!level.hasChunkAt(pos)) return;
        BlockEntity block = level.getBlockEntity(pos);
        if (!(block instanceof MillstoneBlockEntity mill)) return;
        // Create's own machine state, not an approximation of the recipe clock.
        ItemStack input = mill.inputInv.getStackInSlot(0);
        int flourNow = 0;
        for (int slot = 0; slot < mill.outputInv.getSlots(); slot++) {
            ItemStack stack = mill.outputInv.getStackInSlot(slot);
            if (FLOUR_ID.equals(BuiltInRegistries.ITEM.getKey(stack.getItem())))
                flourNow += stack.getCount();
        }
        if ("DELIVERED".equals(phase)) {
            if (input.is(Items.WHEAT) && mill.timer > 0 && mill.getSpeed() != 0) {
                trace.putString("phase", "PROCESSING_OBSERVED");
                trace.putLong("processingObservedTick", level.getGameTime());
            }
        } else if (input.isEmpty() && flourNow > trace.getInt("baselineFlour")) {
            trace.putString("phase", "CYCLE_OUTPUT_OBSERVED");
            trace.putLong("outputObservedTick", level.getGameTime());
            trace.putInt("observedFlour", flourNow);
            // The job is linked to the citizen and physical machine, but
            // this observation is NOT the machine's private process() callback.
            MillEvidenceJournal.recordCandidate(level, new MillEvidenceJournal.Entry(
                trace.getUUID("jobId"), citizen.getUUID(), pos.asLong(),
                trace.getLong("processingObservedTick"), level.getGameTime(),
                trace.getInt("baselineFlour"), flourNow));
        }
    }

    public static boolean matchesDelivery(Villager citizen, BlockPos machine, long now) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (!trace.hasUUID("jobId") || trace.getLong("millstone") != machine.asLong())
            return false;
        String phase = trace.getString("phase");
        return ("DELIVERED".equals(phase) || "PROCESSING_OBSERVED".equals(phase)
            || "CYCLE_OUTPUT_OBSERVED".equals(phase))
            && now >= trace.getLong("startedTick")
            && now - trace.getLong("startedTick") <= 2400L;
    }

    public static UUID jobId(Villager citizen) {
        return citizen.getPersistentData().getCompound(KEY).getUUID("jobId");
    }

    public static String observe(ServerLevel level, Villager citizen) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (!trace.hasUUID("jobId")) return "MILL_TRACE NONE NO_RESEARCH_CREDIT";
        BlockPos machine = BlockPos.of(trace.getLong("millstone"));
        int now = count(level, machine, FLOUR_ID);
        int baseline = trace.getInt("baselineFlour");
        String phase = trace.getString("phase");
        String verdict = "CYCLE_OUTPUT_OBSERVED".equals(phase)
            ? "CANDIDATE_WHEAT_TO_FLOUR"
            : now < 0 ? "MACHINE_UNAVAILABLE"
            : "OUTPUT_NOT_VERIFIED";
        return "MILL_TRACE job=" + trace.getUUID("jobId")
            + " machine=" + machine + " input=" + trace.getString("input")
            + " phase=" + phase + " baselineFlour=" + baseline
            + " currentFlour=" + now + " processingTick=" + trace.getLong("processingObservedTick")
            + " outputTick=" + trace.getLong("outputObservedTick") + " verdict=" + verdict
            + " NO_RESEARCH_CREDIT";
    }
}
