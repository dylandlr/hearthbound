package dev.hearthbound.world;

import java.util.UUID;
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

    public static void deliveryComplete(Villager citizen, UUID jobId) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (trace.hasUUID("jobId") && trace.getUUID("jobId").equals(jobId)
                && "INSERTION_PENDING".equals(trace.getString("phase"))) {
            trace.putString("phase", "DELIVERED");
        }
    }

    public static String observe(ServerLevel level, Villager citizen) {
        CompoundTag trace = citizen.getPersistentData().getCompound(KEY);
        if (!trace.hasUUID("jobId")) return "MILL_TRACE NONE NO_RESEARCH_CREDIT";
        BlockPos machine = BlockPos.of(trace.getLong("millstone"));
        int now = count(level, machine, FLOUR_ID);
        int baseline = trace.getInt("baselineFlour");
        String phase = trace.getString("phase");
        String verdict = !"DELIVERED".equals(phase) ? "INCOMPLETE"
            : now < 0 ? "MACHINE_UNAVAILABLE"
            : now > baseline ? "CANDIDATE_WHEAT_TO_FLOUR"
            : "OUTPUT_NOT_OBSERVED";
        return "MILL_TRACE job=" + trace.getUUID("jobId")
            + " machine=" + machine + " input=" + trace.getString("input")
            + " phase=" + phase + " baselineFlour=" + baseline
            + " currentFlour=" + now + " verdict=" + verdict
            + " NO_RESEARCH_CREDIT";
    }
}
