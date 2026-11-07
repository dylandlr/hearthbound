package dev.hearthbound.world;

import dev.hearthbound.evidence.DirectSourceWitnessContract;
import dev.hearthbound.evidence.VerifiedMillAttribution;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;

/**
 * Operator-only experimentation with two distinct, physically embodied roles.
 * The source witness must have personally inspected the source before a task
 * may be assigned to a different executor. This is a real assignment
 * dependency, but NOT proof of autonomous discovery or a payout entitlement.
 */
public final class DirectSourceWitnessBridge {
    private static final String HAUL = "hearthbound.haul";
    private static final String LINK = "directSourceWitness.v1";
    private DirectSourceWitnessBridge() {}

    private static DirectSourceWitnessContract.DirectSource direct(
            ServerLevel level, Villager observer, BlockPos source) {
        if (level == null || observer == null || source == null
                || observer.level() != level || !CitizenSourceKnowledge.isCitizen(observer)
                || !level.hasChunkAt(source)
                || observer.distanceToSqr(source.getX() + 0.5, source.getY() + 0.5,
                    source.getZ() + 0.5) > 16.0 * 16.0)
            throw new IllegalArgumentException("observer cannot attest to this loaded source");
        CompoundTag memory = CitizenSourceKnowledge.directEvidence(level, source, observer);
        if (memory == null || !"DIRECT_FORGE_OBSERVATION".equals(memory.getString("origin"))
                || !"AVAILABLE".equals(memory.getString("state"))
                || memory.getInt("wheat") <= 0)
            throw new IllegalArgumentException("no direct available-wheat observation");
        return new DirectSourceWitnessContract.DirectSource(
            HearthboundWorldIdentity.get(level), observer.getUUID(),
            level.dimension().location().toString(), source.asLong(),
            memory.getLong("observed_tick"), memory.getInt("revision"),
            memory.getInt("wheat"), memory.getString("origin"));
    }

    public static String assign(ServerLevel level, Villager executor, Villager witness,
                                BlockPos source, BlockPos destination) {
        if (level == null || executor == null || witness == null
                || executor.level() != level || executor.getUUID().equals(witness.getUUID()))
            return denied("INVALID_PARTICIPANTS");
        DirectSourceWitnessContract.DirectSource direct;
        try {
            direct = direct(level, witness, source);
            // Preflight ALL witness validation before creating an actual job.
            // bind is repeated with the actual minted job UUID immediately
            // after assignment, on the same authoritative server thread.
            DirectSourceWitnessContract.bind(direct, new UUID(0L, 1L),
                executor.getUUID(), level.dimension().location().toString(),
                source.asLong(), level.getGameTime());
        } catch (IllegalArgumentException | IllegalStateException invalid) {
            return denied("NO_FRESH_DIRECT_SOURCE_WITNESS");
        }
        try {
            SableHauling.assign(level, executor, source, destination);
            CompoundTag haul = executor.getPersistentData().getCompound(HAUL);
            if (!haul.hasUUID("jobId") || !haul.contains("assignedTick"))
                throw new IllegalStateException("assigned haul missing job identity");
            UUID job = haul.getUUID("jobId");
            long assigned = haul.getLong("assignedTick");
            DirectSourceWitnessContract.WitnessLink linked =
                DirectSourceWitnessContract.bind(direct, job, executor.getUUID(),
                    level.dimension().location().toString(), source.asLong(), assigned);
            CompoundTag saved = new CompoundTag();
            saved.putUUID("world", linked.world());
            saved.putUUID("job", linked.job());
            saved.putUUID("executor", linked.executor());
            saved.putUUID("observer", linked.observer());
            saved.putString("dimension", linked.dimension());
            saved.putLong("source", linked.position());
            saved.putLong("observedTick", linked.observedTick());
            saved.putLong("assignedTick", linked.assignedTick());
            saved.putInt("sourceRevision", linked.sourceRevision());
            saved.putInt("wheat", linked.wheat());
            saved.putString("origin", linked.origin());
            saved.putString("evidenceId", linked.evidenceId());
            haul.put(LINK, saved);
            executor.getPersistentData().put(HAUL, haul);
            return "WITNESSED_HAUL_ASSIGNED job=" + job + " executor=" + executor.getUUID()
                + " source_witness=" + witness.getUUID()
                + " observed_tick=" + linked.observedTick()
                + " assigned_tick=" + linked.assignedTick()
                + " witness_evidence_id=" + linked.evidenceId()
                + " dependency=PRE_TASK_DIRECT_SOURCE_OBSERVATION"
                + " decision_origin=OPERATOR_ASSISTED"
                + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        } catch (IllegalArgumentException | IllegalStateException ex) {
            // An allocation error after SableHauling.assign must NEVER be
            // reported as evidence of successful research; the existing
            // hauling/reconciliation system remains authoritative.
            return denied("HAUL_ASSIGNMENT_REJECTED_OR_INCOMPLETE");
        }
    }

    private static DirectSourceWitnessContract.WitnessLink fromTag(CompoundTag tag) {
        if (tag == null || !tag.hasUUID("world") || !tag.hasUUID("job")
                || !tag.hasUUID("executor") || !tag.hasUUID("observer")
                || !tag.contains("source") || !tag.contains("observedTick")
                || !tag.contains("assignedTick") || !tag.contains("sourceRevision")
                || !tag.contains("wheat") || !tag.contains("dimension")
                || !tag.contains("origin") || !tag.contains("evidenceId"))
            throw new IllegalArgumentException("missing pre-assignment witness proof");
        return new DirectSourceWitnessContract.WitnessLink(
            tag.getUUID("world"), tag.getUUID("job"), tag.getUUID("executor"),
            tag.getUUID("observer"), tag.getString("dimension"), tag.getLong("source"),
            tag.getLong("observedTick"), tag.getLong("assignedTick"),
            tag.getInt("sourceRevision"), tag.getInt("wheat"),
            tag.getString("origin"), tag.getString("evidenceId"));
    }

    /** Read-only post-process join with the *actual* Create callback. */
    public static String inspect(ServerLevel level, Villager executor, UUID job) {
        if (level == null || executor == null || job == null || executor.level() != level)
            return denied("INVALID_REQUEST");
        MillProcessReceipts.Receipt process = MillProcessReceipts.observedCallback(level, job);
        if (process == null) return denied("NO_CREATE_CALLBACK");
        if (!job.equals(process.job()) || !executor.getUUID().equals(process.citizen()))
            return denied("NOT_PHYSICAL_EXECUTOR");
        BlockPos machine = BlockPos.of(process.pos());
        if (!level.hasChunkAt(machine)) return denied("MACHINE_UNAVAILABLE");
        if (!MillReservations.matches(level, machine, job, executor.getUUID()))
            return denied("TAINTED_OR_RELEASED_PROCESS");
        try {
            UUID world = HearthboundWorldIdentity.get(level);
            SableHauling.Assignment assignment =
                SableHauling.completedAssignment(level, executor, job, machine);
            VerifiedMillAttribution.Claim physical =
                MillProcessReceipts.exportVerified(level, world, job, executor.getUUID(), machine);
            CompoundTag haul = executor.getPersistentData().getCompound(HAUL);
            if (!haul.contains(LINK)) return denied("NO_WITNESSED_ASSIGNMENT");
            DirectSourceWitnessContract.WitnessLink link = fromTag(haul.getCompound(LINK));
            Entity entity = level.getEntity(link.observer());
            if (!(entity instanceof Villager observer) || !CitizenSourceKnowledge.isCitizen(observer))
                return denied("WITNESS_NOT_LOADED");
            DirectSourceWitnessContract.DirectSource currentlyRecorded =
                direct(level, observer, BlockPos.of(assignment.source()));
            if (!DirectSourceWitnessContract.matchesProcess(link, currentlyRecorded,
                    world, job, executor.getUUID(), level.dimension().location().toString(),
                    assignment.source(), assignment.assignedTick(), physical.observedStartTick()))
                return denied("WITNESS_EVIDENCE_CHANGED_OR_WRONG_JOB");
            return "MILL_WITNESS_EVIDENCE status=VERIFIED"
                + " job=" + job + " world=" + world
                + " executor=" + executor.getUUID() + " source_witness=" + observer.getUUID()
                + " source=" + BlockPos.of(assignment.source())
                + " machine=" + machine
                + " observed_tick=" + link.observedTick()
                + " assigned_tick=" + link.assignedTick()
                + " process_start_tick=" + physical.observedStartTick()
                + " process_finish_tick=" + physical.finishTick()
                + " witness_evidence_id=" + link.evidenceId()
                + " roles=PHYSICAL_EXECUTOR,PRE_TASK_DIRECT_SOURCE_WITNESS"
                + " witness_gated_assignment=true independent_policy_choice=false"
                + " personal_milli=0 colony_milli=0 research_milli=0"
                + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        } catch (IllegalArgumentException | IllegalStateException ex) {
            return denied("WITNESS_OR_PROCESS_EVIDENCE_INVALID");
        }
    }

    private static String denied(String why) {
        return "MILL_WITNESS_EVIDENCE status=DENIED reason=" + why
            + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
