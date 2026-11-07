package dev.hearthbound.world;

import dev.hearthbound.evidence.CausalEvidenceJournal;
import dev.hearthbound.evidence.VerifiedMillAttribution;
import java.nio.file.Path;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.storage.LevelResource;

/**
 * Explicit OPERATOR audit hook: snapshots existing world-backed witnesses into
 * a durable evidence-only journal. This is NOT a gameplay reward path.
 *
 * A read after a real server restart always revalidates the live SaveData and
 * villager NBT witnesses. Invalidation is terminal; no credit is ever paid.
 */
public final class RealMillCausalJournal {
    private RealMillCausalJournal() {}

    private static CausalEvidenceJournal.Observation live(
            ServerLevel level, Villager citizen, UUID job) {
        MillProcessReceipts.Receipt raw = MillProcessReceipts.observedCallback(level, job);
        if (raw == null || !job.equals(raw.job()) || !citizen.getUUID().equals(raw.citizen()))
            throw new IllegalArgumentException("Create callback missing or owner mismatch");
        BlockPos machine = BlockPos.of(raw.pos());
        if (!level.hasChunkAt(machine))
            throw new IllegalStateException("Create machine unavailable");
        if (raw.tick() > level.getGameTime())
            throw new IllegalArgumentException("future callback after world rollback");
        if (!MillReservations.matches(level, machine, job, citizen.getUUID()))
            throw new IllegalArgumentException("mill reservation absent or tainted");
        SableHauling.Assignment assigned =
            SableHauling.completedAssignment(level, citizen, job, machine);
        if (assigned.assignedTick() > raw.startTick())
            throw new IllegalArgumentException("execution decision occurred after Create started");
        UUID world = HearthboundWorldIdentity.get(level);
        VerifiedMillAttribution.Claim claim = MillProcessReceipts.exportVerified(
            level, world, job, citizen.getUUID(), machine);
        String physical = "hearthbound:create-process:v1:" + world + ":"
            + level.dimension().location() + ":" + machine.asLong() + ":" + job
            + ":" + raw.startTick() + ":" + raw.tick();
        return new CausalEvidenceJournal.Observation(world, claim.eventId(),
            physical, job.toString(), citizen.getUUID().toString(),
            level.dimension().location().toString(), machine.asLong(),
            assigned.assignedTick(), raw.startTick(), raw.tick());
    }

    public static String recordAndRecheck(ServerLevel level, Villager citizen, UUID job) {
        if (level == null || citizen == null || job == null || citizen.level() != level)
            return denied("INVALID_REQUEST");
        UUID world = HearthboundWorldIdentity.get(level);
        String event = "hearthbound:mill:v1:" + world + ":"
            + level.dimension().location() + ":" + job;
        Path file = level.getServer().getWorldPath(LevelResource.ROOT)
            .resolve("data/hearthbound/causal-outcomes-v1.bin");
        try (CausalEvidenceJournal journal = new CausalEvidenceJournal(file, world)) {
            CausalEvidenceJournal.View prior = journal.inspect(event);
            if (prior != null) {
                // An incorrect operator-selected citizen must not revoke the
                // real owner's historical admission as a side effect.
                if (!prior.observation().citizenId().equals(citizen.getUUID().toString()))
                    return denied("FOREIGN_CITIZEN");
                if (!level.hasChunkAt(BlockPos.of(prior.observation().machinePos())))
                    return denied("SOURCE_CHUNK_UNLOADED");
            } else {
                CausalEvidenceJournal.Observation witnessed;
                try {
                    witnessed = live(level, citizen, job);
                } catch (IllegalArgumentException | IllegalStateException invalid) {
                    return denied("UNVERIFIED_MINECRAFT_EVIDENCE");
                }
                journal.observe(witnessed);
            }
            // A recovered ADMITTED record is never accepted on disk alone.
            // This live comparison encompasses current reservation and taint,
            // Create process callback, world ID and villager assignment NBT.
            CausalEvidenceJournal.View result = journal.reconcile(event, expected -> {
                try {
                    return expected.equals(live(level, citizen, job));
                } catch (IllegalArgumentException | IllegalStateException invalid) {
                    return false;
                }
            });
            return "CAUSAL_EVIDENCE_JOURNAL state=" + result.state()
                + " revalidated=" + result.revalidatedThisSession()
                + " event=" + event + " world=" + world
                + " job=" + job + " citizen=" + citizen.getUUID()
                + " physical_evidence=" + result.observation().physicalEvidenceId()
                + " record_count=" + journal.size()
                + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        } catch (Exception unavailable) {
            // A bad disk, mismatched world, unavailable source, or write
            // failure can NEVER fall back to a research reward or inference.
            return denied("JOURNAL_UNAVAILABLE_OR_CORRUPT");
        }
    }

    private static String denied(String reason) {
        return "CAUSAL_EVIDENCE_JOURNAL state=DENIED reason=" + reason
            + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
