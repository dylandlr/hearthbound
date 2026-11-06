package dev.hearthbound.world;

import dev.hearthbound.evidence.OutcomeLedger;
import dev.hearthbound.evidence.VerifiedMillAttribution;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Operator-only, read-only view of a real Create callback joined to Sable's
 * persisted executor assignment and the currently valid mill reservation.
 *
 * This does NOT submit to the research inbox, pay rewards, unlock a recipe or
 * train a policy. The in-memory proposal ledger is discarded after inspection.
 */
public final class RealMillOutcomeProbe {
    private RealMillOutcomeProbe() {}

    public static String inspect(ServerLevel level, Villager citizen, UUID job) {
        if (level == null || citizen == null || job == null || citizen.level() != level)
            return denied("INVALID_REQUEST");
        // A raw callback may later become tainted. Presence alone is not proof.
        MillProcessReceipts.Receipt receipt = MillProcessReceipts.observedCallback(level, job);
        if (receipt == null) return denied("NO_CREATE_CALLBACK");
        if (!job.equals(receipt.job()) || !citizen.getUUID().equals(receipt.citizen()))
            return denied("CITIZEN_OR_JOB_MISMATCH");
        BlockPos machine = BlockPos.of(receipt.pos());
        if (!level.hasChunkAt(machine)) return denied("MACHINE_CHUNK_UNLOADED");
        if (!MillReservations.matches(level, machine, job, citizen.getUUID()))
            return denied("TAINTED_OR_UNHELD_RESERVATION");
        if (receipt.startTick() < 0 || receipt.tick() <= receipt.startTick()
                || receipt.tick() > level.getGameTime())
            return denied("INVALID_CALLBACK_CHRONOLOGY");

        try {
            SableHauling.Assignment assignment =
                SableHauling.completedAssignment(level, citizen, job, machine);
            if (assignment.assignedTick() > receipt.startTick())
                return denied("DECISION_AFTER_PROCESSING_STARTED");
            UUID world = HearthboundWorldIdentity.get(level);
            // exportVerified reads SavedData again and checks the current
            // reservation, taint and exactly one authorized Create transition.
            VerifiedMillAttribution.Claim claim =
                MillProcessReceipts.exportVerified(level, world, job, citizen.getUUID(), machine);
            String decision = "hearthbound:executor-haul:v1:" + world + ":" + job
                + ":" + citizen.getUUID();
            String evidence = "hearthbound:create-process:v1:" + world + ":"
                + level.dimension().location() + ":" + machine.asLong() + ":"
                + job + ":" + receipt.startTick() + ":" + receipt.tick();
            OutcomeLedger proposed = new OutcomeLedger();
            proposed.register(new OutcomeLedger.Decision(
                world, decision, citizen.getUUID().toString(), job.toString(),
                assignment.assignedTick(), "EXECUTOR_ASSIGNED_WHEAT_HAUL"));
            // No registered colony identity, no verified independent research
            // experiment and no other citizen's action receipt: do not invent
            // colony/research rewards or additional contributors.
            OutcomeLedger.Award award = proposed.proposeMill(
                claim, world, evidence, "UNASSIGNED_COLONY",
                List.of(new OutcomeLedger.Contribution(decision, 1, 0)),
                new OutcomeLedger.Budget(500, 0, 0));
            long personal = award.rewards().stream()
                .filter(r -> r.domain().equals("personal")).mapToLong(r -> r.milliPoints()).sum();
            return "MILL_OUTCOME_PROPOSAL status=PROPOSED"
                + " job=" + job
                + " citizen=" + citizen.getUUID()
                + " world=" + world
                + " source=" + BlockPos.of(assignment.source())
                + " machine=" + machine
                + " assigned_tick=" + assignment.assignedTick()
                + " process_start_tick=" + claim.observedStartTick()
                + " process_finish_tick=" + claim.finishTick()
                + " physical_evidence_id=" + evidence
                + " decision_origin=ACTUAL_EXECUTOR_ASSIGNMENT"
                + " personal_milli=" + personal
                + " colony_milli=0 research_milli=0"
                + " reward_authorized=false learning_authorized=false"
                + " NO_RESEARCH_CREDIT";
        } catch (IllegalArgumentException | IllegalStateException ex) {
            return denied("ASSIGNMENT_OR_CREATE_EVIDENCE_INVALID");
        }
    }

    private static String denied(String reason) {
        return "MILL_OUTCOME_PROPOSAL status=DENIED reason=" + reason
            + " reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
    }
}
