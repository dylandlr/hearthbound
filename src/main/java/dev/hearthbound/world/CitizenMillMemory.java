package dev.hearthbound.world;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.entity.npc.Villager;

/**
 * Verified, idempotent per-citizen machine experience. Stored on the real
 * villager's persistent NBT. Observation only: not an RL reward or policy update.
 */
public final class CitizenMillMemory {
    private static final String KEY = "hearthbound.verifiedMillExperience.v1";
    private static final int MAX_RECENT = 128;
    private CitizenMillMemory() {}

    public static boolean record(Villager citizen, UUID job, long machine, long tick) {
        if (citizen == null || job == null || tick < 0)
            throw new IllegalArgumentException("invalid verified experience");
        CompoundTag state = citizen.getPersistentData().getCompound(KEY);
        ListTag jobs = state.getList("recentJobs", Tag.TAG_STRING);
        for (int i = 0; i < jobs.size(); i++) {
            if (job.toString().equals(jobs.getString(i))) return false;
        }
        // No old job is re-awarded: the durable receipt ledger also enforces
        // idempotency by job UUID; recent list is for citizen readback only.
        if (jobs.size() >= MAX_RECENT) jobs.remove(0);
        jobs.add(net.minecraft.nbt.StringTag.valueOf(job.toString()));
        state.put("recentJobs", jobs);
        state.putLong("observedVerifiedProcesses", state.getLong("observedVerifiedProcesses") + 1L);
        state.putLong("lastVerifiedTick", tick);
        state.putLong("lastMachine", machine);
        citizen.getPersistentData().put(KEY, state);
        return true;
    }

    public static long observedProcesses(Villager citizen) {
        return citizen.getPersistentData().getCompound(KEY).getLong("observedVerifiedProcesses");
    }
}
