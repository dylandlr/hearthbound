package dev.hearthbound.world;

import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.LongArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import dev.hearthbound.civilization.BoundedSourceDiscovery;
import dev.hearthbound.civilization.CommunicationNetworkPolicy;
import dev.hearthbound.civilization.CommunicationNetworkPolicy.Arm;
import dev.hearthbound.civilization.PrivateCommunicationPolicy;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Knowledge;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.KnowledgeBook;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Origin;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.Point;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.RoundBudget;
import dev.hearthbound.civilization.PrivateCommunicationPolicy.State;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/**
 * Explicit disposable-world experiment. Actors have private candidate menus;
 * the production colony task board is never read or written. Both treatments
 * use the same scripted policy, sensing schedule and native hauling executor.
 * Records are observational, session-local, bounded and exported by the runner.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class PrivateCommunicationTrial {
    public static final String SCHEMA = "hearthbound.private-communication-trial.v1";
    public static final String NETWORK_SCHEMA = "hearthbound.communication-network-trial.v2";
    private static final String MARKER = "hearthbound.private_communication_trial.v1";
    private static final String PREFIX = "COMMUNICATION_TRIAL_V1 ";
    private static final String NETWORK_PREFIX = "COMMUNICATION_NETWORK_TRIAL_V2 ";
    private static final int MAX_RECORDS = 4096;
    private static final Map<ServerLevel, Trial> TRIALS = new WeakHashMap<>();
    private static final List<String> COUNTERS = List.of("idle_opportunities", "motor_ticks",
        "near_probes", "near_inspections", "outer_probes", "outer_inspections", "rechecks",
        "assignment_attempts", "assignments", "completed_jobs", "send_attempts", "report_reads",
        "motor_elapsed_ns", "discovery_elapsed_ns", "communication_elapsed_ns", "decision_elapsed_ns");
    private static final List<String> BUDGET_COUNTERS = List.of("near_probes", "near_inspections",
        "outer_probes", "outer_inspections", "rechecks", "assignment_attempts", "send_attempts");
    private PrivateCommunicationTrial() {}

    private static final class Actor {
        final int slot;
        final int physicalSeat;
        final UUID citizen;
        final double[] initial;
        final boolean initialNoAi;
        // Only own observations persist here. Received evidence remains in the
        // existing bounded private inbox; every decision rebuilds its source view.
        final KnowledgeBook direct = new KnowledgeBook();
        final Map<String, Long> counters = new LinkedHashMap<>();
        final Map<String, Long> maxima = new LinkedHashMap<>();
        final Set<UUID> completed = new HashSet<>();
        RoundBudget budget;
        Actor(int slot, int physicalSeat, Villager citizen) {
            this.slot = slot;
            this.physicalSeat = physicalSeat;
            this.citizen = citizen.getUUID();
            this.initial = new double[] {citizen.getX(), citizen.getY(), citizen.getZ()};
            this.initialNoAi = citizen.isNoAi();
            for (String key : COUNTERS) counters.put(key, 0L);
            for (String key : BUDGET_COUNTERS) maxima.put(key, 0L);
        }
        void add(String key, long amount) { counters.put(key, Math.addExact(counters.get(key), amount)); }
    }
    private static final class Trial {
        final Arm arm;
        final long seed;
        final int horizon;
        final BlockPos destination;
        final UUID world, episode;
        final List<Integer> seatMap;
        final String blockId, trialId;
        final Actor[] actors = new Actor[PrivateCommunicationPolicy.WORKERS];
        final BoundedSourceDiscovery discovery = new BoundedSourceDiscovery();
        final List<JsonObject> records = new ArrayList<>();
        final List<String> errors = new ArrayList<>();
        String status = "CONFIGURED";
        long start = -1, end = -1, rounds, recordCapacityDenials;
        Trial(ServerLevel level, Arm arm, long seed, int horizon, BlockPos destination) {
            this(level, arm, seed, horizon, destination, null, null, null);
        }
        Trial(ServerLevel level, Arm arm, long seed, int horizon, BlockPos destination,
              List<Integer> seatMap, String blockId, String trialId) {
            PrivateCommunicationPolicy.validateHorizon(horizon);
            this.arm = arm; this.seed = seed; this.horizon = horizon;
            this.seatMap = seatMap == null ? null : List.copyOf(seatMap);
            this.blockId = blockId; this.trialId = trialId;
            this.destination = destination.immutable();
            world = HearthboundWorldIdentity.get(level); episode = SourceReportSession.episode(level);
        }
        boolean networkQualification() { return seatMap != null; }
    }

    /** A sticky explicit marker prevents default control after stop/restart. */
    public static boolean controls(Villager citizen) {
        if (!citizen.getPersistentData().getBoolean(MARKER)) return false;
        Trial trial = citizen.level() instanceof ServerLevel level ? TRIALS.get(level) : null;
        boolean owned = trial != null && trial.status.equals("RUNNING")
            && java.util.Arrays.stream(trial.actors)
                .anyMatch(actor -> actor != null && actor.citizen.equals(citizen.getUUID()));
        if (!owned) {
            citizen.getNavigation().stop(); citizen.setNoAi(true);
        }
        return true;
    }

    private static Villager citizen(ServerLevel level, Actor actor) {
        if (level.getEntity(actor.citizen) instanceof Villager citizen && citizen.level() == level
                && citizen.isAlive() && CitizenSourceKnowledge.isCitizen(citizen)
                && !NeedServiceRuntime.controls(citizen) && !VillageEconomyRuntime.controls(citizen)
                && citizen.getPersistentData().getBoolean(MARKER))
            return citizen;
        throw new IllegalStateException("Original enrolled citizen unavailable: slot " + actor.slot);
    }
    private static Trial trial(ServerLevel level) {
        Trial trial = TRIALS.get(level);
        if (trial == null) throw new IllegalStateException("No private communication trial configured");
        if (!trial.world.equals(HearthboundWorldIdentity.get(level))
                || !trial.episode.equals(SourceReportSession.episode(level)))
            throw new IllegalStateException("Trial world/session changed");
        return trial;
    }
    private static void uncontaminated(ServerLevel level, Trial trial) {
        if (CivilizationRuntime.enabled(level))
            throw new IllegalStateException("Production colony dispatch must remain disabled during the trial");
        Set<UUID> roster = new HashSet<>();
        for (Actor actor : trial.actors) if (actor != null) roster.add(actor.citizen);
        for (Villager other : level.getEntitiesOfClass(Villager.class,
                new net.minecraft.world.phys.AABB(trial.destination).inflate(32), CitizenSourceKnowledge::isCitizen))
            if (!roster.contains(other.getUUID()))
                throw new IllegalStateException("Unenrolled marked citizen inside the trial arena");
    }
    private static Point point(BlockPos pos) { return new Point(pos.getX(), pos.getY(), pos.getZ()); }
    private static BlockPos block(Point point) { return new BlockPos(point.x(), point.y(), point.z()); }
    private static JsonArray xyz(BlockPos pos) {
        JsonArray value = new JsonArray(); value.add(pos.getX()); value.add(pos.getY()); value.add(pos.getZ());
        return value;
    }
    private static JsonArray position(Villager citizen) {
        JsonArray value = new JsonArray(); value.add(citizen.getX()); value.add(citizen.getY()); value.add(citizen.getZ());
        return value;
    }
    private static JsonObject event(ServerLevel level, Trial trial, Actor actor, String kind) {
        JsonObject row = new JsonObject(); row.addProperty("kind", kind);
        row.addProperty("tick", level.getGameTime());
        row.addProperty("relative_tick", trial.start < 0 ? -1 : level.getGameTime() - trial.start);
        row.addProperty("slot", actor.slot); row.addProperty("citizen", actor.citizen.toString());
        if (trial.networkQualification()) {
            networkContext(row, trial);
            row.addProperty("round", trial.rounds);
            row.addProperty("physical_seat", actor.physicalSeat);
        }
        return row;
    }
    private static void networkContext(JsonObject row, Trial trial) {
        row.addProperty("world", trial.world.toString()); row.addProperty("episode", trial.episode.toString());
        row.addProperty("arm", trial.arm.name());
        row.addProperty("block_id", trial.blockId); row.addProperty("trial_id", trial.trialId);
        row.addProperty("design_sha256", CommunicationNetworkPolicy.DESIGN_SHA256);
        row.addProperty("qualification_only", true);
    }
    private static void record(Trial trial, JsonObject row) {
        if (trial.records.size() >= MAX_RECORDS) {
            trial.recordCapacityDenials++;
            throw new IllegalStateException("Trial record capacity exhausted");
        }
        row.addProperty("sequence", trial.records.size() + 1);
        trial.records.add(row);
    }

    private static SourceWheatObservation.Snapshot observe(ServerLevel level, Trial trial,
            Actor actor, Villager citizen, BlockPos source, String phase) {
        SourceWheatObservation.Snapshot observed = SourceWheatObservation.inspect(level, source, citizen);
        JsonObject row = event(level, trial, actor, "OBSERVE");
        row.addProperty("phase", phase); row.add("source", xyz(source)); row.add("observer", position(citizen));
        row.addProperty("state", observed.state().name()); row.addProperty("wheat", observed.wheat());
        row.addProperty("reason", observed.reason());
        if (observed.state() != SourceWheatObservation.State.UNKNOWN) {
            CitizenSourceKnowledge.remember(level, source, citizen, observed);
            actor.direct.remember(new Knowledge(point(source), State.valueOf(observed.state().name()),
                observed.wheat(), observed.tick(), Origin.DIRECT, null), observed.tick());
            CompoundTag evidence = CitizenSourceKnowledge.directEvidence(level, source, citizen);
            row.addProperty("revision", evidence.getInt("revision"));
        } else row.add("revision", JsonNull.INSTANCE);
        record(trial, row);
        return observed;
    }

    private static void discover(ServerLevel level, Trial trial, Actor actor, Villager citizen) {
        long begun = System.nanoTime();
        actor.add("idle_opportunities", 1);
        BlockPos center = citizen.blockPosition();
        boolean full = false;
        for (int dx = -2; dx <= 2 && !full; dx++)
            for (int dy = -1; dy <= 1 && !full; dy++)
                for (int dz = -2; dz <= 2; dz++) {
                    if (!actor.budget.tryNearPosition()) { full = true; break; }
                    actor.add("near_probes", 1);
                    BlockPos source = center.offset(dx, dy, dz);
                    if (source.equals(trial.destination) || !level.hasChunkAt(source)
                            || level.getBlockEntity(source) == null) continue;
                    if (!actor.budget.tryNearInspection()) { full = true; break; }
                    actor.add("near_inspections", 1);
                    observe(level, trial, actor, citizen, source, "NEAR");
                }
        var scope = new BoundedSourceDiscovery.Scope(trial.world, trial.episode,
            level.dimension().location().toString(), new BoundedSourceDiscovery.Point(
                trial.destination.getX(), trial.destination.getY(), trial.destination.getZ()));
        trial.discovery.advance(scope, actor.citizen, new BoundedSourceDiscovery.Position(
            citizen.getX(), citizen.getY(), citizen.getZ()), level.getGameTime(), new BoundedSourceDiscovery.WorldView() {
                private BlockPos pos(BoundedSourceDiscovery.Point source) {
                    return new BlockPos(source.x(), source.y(), source.z());
                }
                @Override public boolean loaded(BoundedSourceDiscovery.Point source) { return level.hasChunkAt(pos(source)); }
                @Override public boolean blockEntity(BoundedSourceDiscovery.Point source) { return level.getBlockEntity(pos(source)) != null; }
                @Override public BoundedSourceDiscovery.Observation inspect(BoundedSourceDiscovery.Point source) {
                    var observation = observe(level, trial, actor, citizen, pos(source), "OUTER");
                    return new BoundedSourceDiscovery.Observation(
                        BoundedSourceDiscovery.State.valueOf(observation.state().name()), observation.wheat(),
                        observation.tick(), observation.reason(), null, BoundedSourceDiscovery.Proposal.NONE);
                }
            });
        var costs = trial.discovery.citizen(scope, actor.citizen);
        for (int i = 0; i < costs.lastCycleProbes(); i++)
            if (!actor.budget.tryOuterPosition()) throw new IllegalStateException("Outer probe budget exceeded");
        for (int i = 0; i < costs.lastCycleInspections(); i++)
            if (!actor.budget.tryOuterInspection()) throw new IllegalStateException("Outer inspection budget exceeded");
        actor.add("outer_probes", costs.lastCycleProbes());
        actor.add("outer_inspections", costs.lastCycleInspections());
        actor.add("discovery_elapsed_ns", System.nanoTime() - begun);
    }

    private static void communicate(ServerLevel level, Trial trial, Actor actor, Villager sender) {
        if (trial.networkQualification()) {
            communicateNetwork(level, trial, actor, sender);
            return;
        }
        long begun = System.nanoTime(), now = level.getGameTime();
        List<Knowledge> own = actor.direct.ownDirect(now).stream()
            .filter(item -> now - item.observedTick() <= CitizenSourceKnowledge.FRESH_TICKS)
            .sorted(Comparator.comparingInt((Knowledge item) -> item.source().x())
                .thenComparingInt(item -> item.source().y()).thenComparingInt(item -> item.source().z())).toList();
        if (!own.isEmpty()) {
            if (!actor.budget.trySend()) throw new IllegalStateException("Send budget exceeded");
            int peerSlot = (actor.slot + 1 + (int) (trial.rounds % 3)) % PrivateCommunicationPolicy.WORKERS;
            Villager recipient = citizen(level, trial.actors[peerSlot]);
            BlockPos source = block(own.get((int) (trial.rounds % own.size())).source());
            actor.add("send_attempts", 1);
            JsonObject row = event(level, trial, actor, "SEND");
            row.addProperty("recipient_slot", peerSlot); row.addProperty("recipient", recipient.getUUID().toString());
            row.add("source", xyz(source));
            if (trial.arm == Arm.NO_MESSAGES) {
                UUID attempt = CitizenCommunicationRecords.sendAttempt(level, source, sender, recipient);
                CitizenCommunicationRecords.rejected(level, attempt, "NETWORK_DISABLED");
                row.addProperty("result", "REJECTED_NETWORK_DISABLED");
            } else row.addProperty("result", CitizenKnowledgeExchange.share(level, source, sender, recipient));
            record(trial, row);
        }
        actor.add("communication_elapsed_ns", System.nanoTime() - begun);
    }

    private static void communicateNetwork(ServerLevel level, Trial trial, Actor actor, Villager sender) {
        long begun = System.nanoTime(), now = level.getGameTime();
        List<Knowledge> own = actor.direct.ownDirect(now).stream()
            .filter(item -> now - item.observedTick() <= CitizenSourceKnowledge.FRESH_TICKS)
            .sorted(Comparator.comparingInt((Knowledge item) -> item.source().x())
                .thenComparingInt(item -> item.source().y()).thenComparingInt(item -> item.source().z())).toList();
        int peerSlot = CommunicationNetworkPolicy.recipientSlot(actor.slot, trial.rounds);
        Actor peer = trial.actors[peerSlot];
        Villager recipient = citizen(level, peer);
        JsonObject row = event(level, trial, actor, own.isEmpty() ? "SEND_OPPORTUNITY" : "SEND");
        row.addProperty("recipient_slot", peerSlot); row.addProperty("recipient_seat", peer.physicalSeat);
        row.addProperty("recipient", recipient.getUUID().toString());
        JsonArray edge = new JsonArray(); edge.add(Math.min(actor.slot, peerSlot)); edge.add(Math.max(actor.slot, peerSlot));
        row.add("permission_edge", edge);
        JsonArray route = new JsonArray(); route.add(sender.getUUID().toString()); route.add(recipient.getUUID().toString());
        row.add("route", route);
        if (own.isEmpty()) {
            row.addProperty("edge_allowed", trial.arm.permits(actor.slot, peerSlot));
            row.addProperty("edge_decision", "NOT_ATTEMPTED_NO_PAYLOAD");
            row.addProperty("route_semantics", "PROPOSED_DIRECT_RECIPIENT");
            row.addProperty("charged_send_budget", 0);
            row.addProperty("result", "NO_ELIGIBLE_DIRECT_EVIDENCE");
            for (String key : List.of("attempt_id", "source", "source_observation_owner", "observed_tick",
                    "source_revision", "claimed_wheat", "source_state", "observation_world",
                    "observation_session", "observation_episode"))
                row.add(key, JsonNull.INSTANCE);
        } else {
            Knowledge chosen = own.get((int) (trial.rounds % own.size()));
            BlockPos source = block(chosen.source());
            CompoundTag evidence = CitizenSourceKnowledge.directEvidence(level, source, sender);
            if (evidence == null || evidence.getLong("observed_tick") != chosen.observedTick()
                    || evidence.getInt("wheat") != chosen.wheat()
                    || !evidence.getString("state").equals(chosen.state().name())
                    || evidence.getInt("revision") < 1
                    || !evidence.hasUUID("observationWorld") || !evidence.getUUID("observationWorld").equals(trial.world)
                    || !evidence.hasUUID("observationSession") || !SourceReportSession.accepts(level, evidence, now))
                throw new IllegalStateException("Outgoing payload does not match the sender's native direct evidence");
            UUID observationEpisode = CommunicationNetworkPolicy.bindObservationEpisode(trial.world, trial.episode,
                evidence.getUUID("observationWorld"), evidence.getUUID("observationSession"),
                level.dimension().location().toString());
            String permission = CommunicationNetworkPolicy.chargeAndCheck(trial.arm, actor.slot, trial.rounds, actor.budget);
            actor.add("send_attempts", 1);
            row.addProperty("edge_allowed", permission.equals("ALLOWED"));
            row.addProperty("edge_decision", permission);
            row.addProperty("route_semantics", "ATTEMPTED_DIRECT_RECIPIENT");
            row.addProperty("charged_send_budget", 1);
            row.add("source", xyz(source));
            row.addProperty("source_observation_owner", sender.getUUID().toString());
            row.addProperty("observed_tick", evidence.getLong("observed_tick"));
            row.addProperty("source_revision", evidence.getInt("revision"));
            row.addProperty("claimed_wheat", evidence.getInt("wheat"));
            row.addProperty("source_state", evidence.getString("state"));
            row.addProperty("observation_world", evidence.getUUID("observationWorld").toString());
            row.addProperty("observation_session", evidence.getUUID("observationSession").toString());
            row.addProperty("observation_episode", observationEpisode.toString());
            if (!permission.equals("ALLOWED")) {
                UUID attempt = CitizenCommunicationRecords.sendAttempt(level, source, sender, recipient);
                CitizenCommunicationRecords.rejected(level, attempt, permission);
                row.addProperty("attempt_id", attempt.toString());
                row.addProperty("result", "REJECTED_" + permission);
            } else {
                var receipt = CitizenKnowledgeExchange.shareWithReceipt(level, source, sender, recipient);
                row.addProperty("attempt_id", receipt.attempt().toString());
                row.addProperty("result", receipt.result());
            }
        }
        record(trial, row);
        actor.add("communication_elapsed_ns", System.nanoTime() - begun);
    }

    private static void decide(ServerLevel level, Trial trial, Actor actor, Villager citizen) {
        long begun = System.nanoTime(), now = level.getGameTime();
        UUID decision = UUID.randomUUID();
        KnowledgeBook menu = new KnowledgeBook();
        for (Knowledge own : actor.direct.ownDirect(now)) menu.remember(own, now);
        Map<String, CompoundTag> readReports = new LinkedHashMap<>();
        if (trial.arm.reportsExposedToDecisions()) {
            for (CompoundTag report : CommunicationNetworkPolicy.policyReports(trial.arm,
                    () -> CitizenKnowledgeExchange.decisionReports(level, citizen))) {
                BlockPos source = CitizenKnowledgeExchange.reportedSource(level, report);
                long observed = report.getLong("observed_tick");
                if (source == null || observed > now || now - observed > PrivateCommunicationPolicy.MAX_AGE_TICKS)
                    continue;
                // Actual policy consumption, even when a newer direct observation
                // ultimately vetoes the report. Operator audit never calls this.
                CitizenCommunicationRecords.read(level, citizen, decision, report);
                actor.add("report_reads", 1);
                readReports.put(report.getString("id"), report);
                menu.remember(new Knowledge(point(source), State.valueOf(report.getString("state")),
                    report.getInt("wheat"), observed, Origin.REPORT, report.getString("id")), now);
            }
        }
        Set<Point> claimed = new HashSet<>();
        // Claims only exclude sources already present in this private menu.
        for (Knowledge item : menu.knowledge(now)) {
            UUID owner = HaulClaims.owner(level, block(item.source()));
            if (owner != null && !owner.equals(citizen.getUUID())) claimed.add(item.source());
        }
        var choice = menu.choose(new PrivateCommunicationPolicy.Position(citizen.getX(), citizen.getY(),
            citizen.getZ()), now, claimed, point(trial.destination));
        JsonObject row = event(level, trial, actor, "DECISION");
        row.addProperty("decision", decision.toString());
        row.addProperty("report_inputs", readReports.size());
        row.addProperty("private_source_candidates", menu.knowledge(now).size());
        row.addProperty("claimed_candidates", claimed.size());
        if (choice == null) {
            row.addProperty("result", "ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE"); record(trial, row);
            actor.add("decision_elapsed_ns", System.nanoTime() - begun); return;
        }
        BlockPos source = block(choice.source());
        row.add("source", xyz(source)); row.addProperty("mode", choice.kind());
        row.addProperty("evidence_observed_tick", choice.evidence().observedTick());
        if (choice.reportCued()) {
            if (!trial.arm.reportsExposedToDecisions())
                throw new IllegalStateException("Policy-inaccessible report cannot cue a job");
            if (!readReports.containsKey(choice.evidence().reportId()))
                throw new IllegalStateException("Chosen report was not actually read");
            row.addProperty("report_id", choice.evidence().reportId());
            CitizenCommunicationRecords.selected(level, citizen, decision, choice.evidence().reportId(), now);
        } else row.add("report_id", JsonNull.INSTANCE);
        if (!actor.budget.tryRecheck()) throw new IllegalStateException("Recheck budget exceeded");
        actor.add("rechecks", 1);
        var checked = observe(level, trial, actor, citizen, source, "RECHECK");
        Knowledge recheck = checked.state() == SourceWheatObservation.State.UNKNOWN ? null
            : new Knowledge(point(source), State.valueOf(checked.state().name()), checked.wheat(),
                checked.tick(), Origin.DIRECT, null);
        if (!PrivateCommunicationPolicy.isCurrentPositiveRecheck(choice, recheck, now)) {
            row.addProperty("result", "CUE_RECHECK_NOT_AVAILABLE"); record(trial, row);
            actor.add("decision_elapsed_ns", System.nanoTime() - begun); return;
        }
        row.addProperty("result", "SELECTED_FRESH_RECHECK"); record(trial, row);
        if (!actor.budget.tryAssignment()) throw new IllegalStateException("Assignment budget exceeded");
        actor.add("assignment_attempts", 1);
        SableHauling.assign(level, citizen, source, trial.destination);
        CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
        UUID job = haul.getUUID("jobId");
        long assigned = haul.getLong("assignedTick");
        if (choice.reportCued()) {
            CompoundTag receipt = new CompoundTag();
            receipt.putUUID("communicationDecision", decision);
            receipt.putString("reportId", choice.evidence().reportId());
            receipt.putString("semantics", "REPORT_CUED_DIRECT_RECHECK");
            haul.put("communicationDispatch.v1", receipt);
            CitizenCommunicationRecords.assigned(level, citizen, decision, choice.evidence().reportId(), job,
                source.asLong(), trial.destination.asLong(), assigned);
        }
        actor.add("assignments", 1);
        JsonObject accepted = event(level, trial, actor, "ASSIGNED");
        accepted.addProperty("job", job.toString()); accepted.addProperty("decision", decision.toString());
        accepted.add("source", xyz(source)); accepted.add("destination", xyz(trial.destination));
        accepted.addProperty("assigned_tick", assigned); accepted.addProperty("mode", choice.kind());
        if (choice.reportCued()) accepted.addProperty("report_id", choice.evidence().reportId());
        else accepted.add("report_id", JsonNull.INSTANCE);
        record(trial, accepted);
        actor.add("decision_elapsed_ns", System.nanoTime() - begun);
    }

    private static void motor(ServerLevel level, Trial trial, Actor actor, Villager citizen) {
        if (!SableHauling.active(citizen)) return;
        long begun = System.nanoTime(); actor.add("motor_ticks", 1);
        SableHauling.tick(level, citizen);
        CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
        if (haul.hasUUID("jobId") && SableHauling.completedJob(citizen, haul.getUUID("jobId"), trial.destination)
                && !actor.completed.contains(haul.getUUID("jobId"))) {
            UUID job = haul.getUUID("jobId");
            var assignment = SableHauling.completedAssignment(level, citizen, job, trial.destination);
            JsonObject row = event(level, trial, actor, "COMPLETE");
            row.addProperty("job", job.toString()); row.add("source", xyz(BlockPos.of(assignment.source())));
            row.add("destination", xyz(BlockPos.of(assignment.destination())));
            row.addProperty("assigned_tick", assignment.assignedTick());
            row.addProperty("delivered_tick", haul.getLong("physicalDeliveredTick")); row.addProperty("wheat", 1);
            row.addProperty("witness", "EXECUTOR_INSERTION_RETURNED_NO_REMAINDER");
            record(trial, row); actor.completed.add(job); actor.add("completed_jobs", 1);
        }
        actor.add("motor_elapsed_ns", System.nanoTime() - begun);
    }

    private static void freeze(ServerLevel level, Trial trial) {
        for (Actor actor : trial.actors) if (actor != null
                && level.getEntity(actor.citizen) instanceof Villager citizen) {
            citizen.getNavigation().stop(); citizen.setNoAi(true);
        }
    }
    private static void fail(ServerLevel level, Trial trial, RuntimeException failure) {
        String text = failure.getClass().getSimpleName() + ": " + failure.getMessage();
        trial.errors.add(text.substring(0, Math.min(512, text.length())));
        trial.status = "ERROR"; freeze(level, trial);
        org.slf4j.LoggerFactory.getLogger(PrivateCommunicationTrial.class)
            .warn("Private communication trial stopped: {}", text);
    }

    @SubscribeEvent public static void levelTick(TickEvent.LevelTickEvent event) {
        if (event.phase != TickEvent.Phase.END || !(event.level instanceof ServerLevel level)) return;
        Trial trial = TRIALS.get(level);
        if (trial == null || !(trial.status.equals("SCHEDULED") || trial.status.equals("RUNNING"))) return;
        try {
            long now = level.getGameTime();
            if (now < trial.start) return;
            if (now >= trial.end) {
                trial.status = "COMPLETE"; freeze(level, trial); return;
            }
            if (trial.status.equals("SCHEDULED")) {
                for (Actor actor : trial.actors) citizen(level, actor).setNoAi(false);
                trial.status = "RUNNING";
            }
            if ((now - trial.start) % PrivateCommunicationPolicy.CADENCE_TICKS != 0) return;
            uncontaminated(level, trial);
            List<Integer> order = PrivateCommunicationPolicy.roundOrder(trial.seed, trial.rounds);
            Map<Integer, Map<String, Long>> before = new LinkedHashMap<>();
            for (int slot : order) {
                Actor actor = trial.actors[slot]; actor.budget = new RoundBudget();
                before.put(slot, new LinkedHashMap<>(actor.counters));
                motor(level, trial, actor, citizen(level, actor));
            }
            for (int slot : order) {
                Actor actor = trial.actors[slot]; Villager citizen = citizen(level, actor);
                if (!SableHauling.active(citizen)) discover(level, trial, actor, citizen);
            }
            for (int slot : order) {
                Actor actor = trial.actors[slot]; communicate(level, trial, actor, citizen(level, actor));
            }
            for (int slot : order) {
                Actor actor = trial.actors[slot]; Villager citizen = citizen(level, actor);
                if (!SableHauling.active(citizen)) decide(level, trial, actor, citizen);
            }
            for (int slot : order) for (String key : BUDGET_COUNTERS) {
                Actor actor = trial.actors[slot];
                actor.maxima.put(key, Math.max(actor.maxima.get(key),
                    actor.counters.get(key) - before.get(slot).get(key)));
            }
            trial.rounds++;
        } catch (RuntimeException failure) { fail(level, trial, failure); }
    }

    @SubscribeEvent public static void stopped(ServerStoppedEvent event) {
        TRIALS.keySet().removeIf(level -> level.getServer() == event.getServer());
    }

    private static JsonObject common(ServerLevel level, Trial trial, String kind) {
        JsonObject result = new JsonObject();
        result.addProperty("schema", trial.networkQualification() ? NETWORK_SCHEMA : SCHEMA);
        result.addProperty("kind", kind);
        result.addProperty("world", trial.world.toString()); result.addProperty("episode", trial.episode.toString());
        result.addProperty("dimension", level.dimension().location().toString()); result.addProperty("read_only", true);
        if (trial.networkQualification()) networkContext(result, trial);
        return result;
    }
    private static JsonObject audit(ServerLevel level, Trial trial) {
        JsonObject result = common(level, trial, "audit");
        result.addProperty("arm", trial.arm.name()); result.addProperty("policy_seed", trial.seed);
        result.addProperty("horizon_ticks", trial.horizon); result.addProperty("status", trial.status);
        result.addProperty("actor_count", java.util.Arrays.stream(trial.actors).filter(java.util.Objects::nonNull).count());
        if (trial.start >= 0) { result.addProperty("start_tick", trial.start); result.addProperty("end_tick", trial.end); }
        else { result.add("start_tick", JsonNull.INSTANCE); result.add("end_tick", JsonNull.INSTANCE); }
        result.addProperty("observed_tick", level.getGameTime());
        result.addProperty("elapsed_ticks", trial.start < 0 ? 0 : Math.max(0, Math.min(trial.horizon, level.getGameTime() - trial.start)));
        result.addProperty("rounds", trial.rounds); result.addProperty("records_total", trial.records.size());
        result.addProperty("record_capacity_denials", trial.recordCapacityDenials);
        JsonArray errors = new JsonArray(); trial.errors.forEach(errors::add); result.add("errors", errors);
        result.add("destination", xyz(trial.destination)); result.addProperty("cadence_ticks", 20);
        result.addProperty("max_records", MAX_RECORDS); result.addProperty("causal_benefit_established", false);
        if (trial.networkQualification()) {
            JsonArray seats = new JsonArray(); trial.seatMap.forEach(seats::add); result.add("slot_to_seat", seats);
            JsonArray edges = new JsonArray();
            for (List<Integer> edge : trial.arm.undirectedEdges()) {
                JsonArray pair = new JsonArray(); edge.forEach(pair::add); edges.add(pair);
            }
            result.add("undirected_permission_edges", edges);
            result.addProperty("transport_enabled", trial.arm.transportEnabled());
            result.addProperty("reports_exposed_to_decisions", trial.arm.reportsExposedToDecisions());
        }
        return result;
    }
    private static JsonObject actor(ServerLevel level, Trial trial, Actor actor) {
        JsonObject result = new JsonObject(); result.addProperty("slot", actor.slot);
        if (trial.networkQualification()) result.addProperty("physical_seat", actor.physicalSeat);
        result.addProperty("citizen", actor.citizen.toString()); JsonArray initial = new JsonArray();
        for (double coordinate : actor.initial) initial.add(coordinate); result.add("initial_position", initial);
        result.addProperty("initial_no_ai", actor.initialNoAi); result.addProperty("policy_id", "SCRIPTED_PRIVATE_NEAREST_V1");
        JsonObject counters = new JsonObject(); actor.counters.forEach(counters::addProperty); result.add("counters", counters);
        JsonObject maxima = new JsonObject(); actor.maxima.forEach(maxima::addProperty); result.add("max_per_round", maxima);
        result.addProperty("private_sources", actor.direct.size());
        if (level.getEntity(actor.citizen) instanceof Villager citizen) {
            result.addProperty("present", true); result.add("current_position", position(citizen));
            result.addProperty("no_ai", citizen.isNoAi()); result.addProperty("active", SableHauling.active(citizen));
            CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
            if (haul.hasUUID("jobId")) result.addProperty("current_job", haul.getUUID("jobId").toString());
            else result.add("current_job", JsonNull.INSTANCE);
            if (haul.contains("phase", Tag.TAG_INT)) result.addProperty("phase", haul.getInt("phase"));
            else result.add("phase", JsonNull.INSTANCE);
            ItemStack cargo = haul.contains("cargo", Tag.TAG_COMPOUND) ? ItemStack.of(haul.getCompound("cargo")) : ItemStack.EMPTY;
            result.addProperty("cargo_wheat", cargo.is(Items.WHEAT) ? cargo.getCount() : 0);
            result.addProperty("motor_status", SableHauling.status(citizen));
        } else result.addProperty("present", false);
        return result;
    }
    private static JsonObject page(ServerLevel level, Trial trial, String kind, int offset) {
        JsonObject root = common(level, trial, kind); JsonArray rows = new JsonArray();
        List<JsonObject> all = kind.equals("actors")
            ? java.util.Arrays.stream(trial.actors).filter(java.util.Objects::nonNull).map(a -> actor(level, trial, a)).toList()
            : trial.records;
        int end = Math.min(all.size(), offset + (kind.equals("actors") ? 1 : 2));
        for (int i = offset; i < end; i++) rows.add(all.get(i));
        root.addProperty("offset", offset); root.addProperty("total", all.size()); root.add("records", rows);
        if (end < all.size()) root.addProperty("next_offset", end); else root.add("next_offset", JsonNull.INSTANCE);
        return root;
    }
    private static int reply(CommandSourceStack source, JsonObject result) {
        String prefix = NETWORK_SCHEMA.equals(result.get("schema").getAsString()) ? NETWORK_PREFIX : PREFIX;
        source.sendSuccess(() -> Component.literal(prefix + result), false); return 1;
    }
    private static int configure(CommandSourceStack source, String arm, long seed, int horizon, BlockPos destination) {
        ServerLevel level = source.getLevel();
        if (TRIALS.containsKey(level)) throw new IllegalStateException("One trial per fresh dimension/session");
        if (CivilizationRuntime.enabled(level))
            throw new IllegalStateException("Production colony dispatch must be disabled before configuration");
        if (!level.hasChunkAt(destination) || level.getBlockEntity(destination) == null)
            throw new IllegalArgumentException("Trial destination must be a loaded inventory block entity");
        Trial trial = new Trial(level, CommunicationNetworkPolicy.legacyArm(arm), seed, horizon, destination);
        TRIALS.put(level, trial); return reply(source, audit(level, trial));
    }
    private static int configureNetwork(CommandSourceStack source, String arm, long seed, int horizon,
                                        BlockPos destination, String seats, String blockId, String trialId) {
        ServerLevel level = source.getLevel();
        if (TRIALS.containsKey(level)) throw new IllegalStateException("One trial per fresh dimension/session");
        if (CivilizationRuntime.enabled(level))
            throw new IllegalStateException("Production colony dispatch must be disabled before configuration");
        if (!level.dimension().location().toString().equals("minecraft:overworld")
                || !level.hasChunkAt(destination) || level.getBlockEntity(destination) == null)
            throw new IllegalArgumentException("Network qualification requires a loaded overworld destination");
        CommunicationNetworkPolicy.validateQualification(level.getSeed(), horizon, point(destination));
        Trial trial = new Trial(level, Arm.valueOf(arm), seed, horizon, destination,
            CommunicationNetworkPolicy.seatMap(seats),
            CommunicationNetworkPolicy.qualificationIdentity(blockId),
            CommunicationNetworkPolicy.qualificationIdentity(trialId));
        TRIALS.put(level, trial); return reply(source, audit(level, trial));
    }
    private static int enroll(CommandSourceStack source, int slot, net.minecraft.world.entity.Entity entity) {
        ServerLevel level = source.getLevel(); Trial trial = trial(level);
        if (!trial.status.equals("CONFIGURED") || trial.actors[slot] != null)
            throw new IllegalStateException("Enrollment closed or slot already occupied");
        if (!(entity instanceof Villager citizen) || citizen.level() != level || !citizen.isAlive()
                || !CitizenSourceKnowledge.isCitizen(citizen) || citizen.getPersistentData().getBoolean(MARKER)
                || NeedServiceRuntime.controls(citizen) || VillageEconomyRuntime.controls(citizen)
                || citizen.getPersistentData().contains("hearthbound.haul")
                || citizen.getPersistentData().contains("hearthbound.source_knowledge.v1")
                || citizen.getPersistentData().contains("hearthbound.citizen_reports.v1"))
            throw new IllegalArgumentException("Enrollment requires a fresh marked idle citizen in this dimension");
        for (Actor actor : trial.actors) if (actor != null && actor.citizen.equals(citizen.getUUID()))
            throw new IllegalArgumentException("Duplicate citizen enrollment");
        int seat = trial.networkQualification() ? trial.seatMap.get(slot) : slot;
        if (trial.networkQualification()) {
            var expected = CommunicationNetworkPolicy.seatPosition(seat);
            if (!citizen.isNoAi() || citizen.getX() != expected.x() || citizen.getY() != expected.y()
                    || citizen.getZ() != expected.z())
                throw new IllegalArgumentException("Network actor must start frozen at its declared physical seat");
        }
        trial.actors[slot] = new Actor(slot, seat, citizen);
        citizen.getPersistentData().putBoolean(MARKER, true);
        citizen.getNavigation().stop(); citizen.setNoAi(true);
        return reply(source, audit(level, trial));
    }
    private static int start(CommandSourceStack source) {
        ServerLevel level = source.getLevel(); Trial trial = trial(level);
        if (!trial.status.equals("CONFIGURED")) throw new IllegalStateException("Trial already started");
        for (Actor actor : trial.actors) {
            if (actor == null) throw new IllegalStateException("Four original actors must be enrolled");
            Villager citizen = citizen(level, actor);
            if (NeedServiceRuntime.controls(citizen) || VillageEconomyRuntime.controls(citizen) || !citizen.isNoAi() || SableHauling.active(citizen)
                    || citizen.getPersistentData().contains("hearthbound.haul")
                    || citizen.getPersistentData().contains("hearthbound.source_knowledge.v1")
                    || citizen.getPersistentData().contains("hearthbound.citizen_reports.v1")
                    || citizen.getX() != actor.initial[0] || citizen.getY() != actor.initial[1]
                    || citizen.getZ() != actor.initial[2])
                throw new IllegalStateException("Enrolled actor moved or became active before start");
        }
        uncontaminated(level, trial);
        trial.start = Math.addExact(level.getGameTime(), 20L);
        trial.end = Math.addExact(trial.start, trial.horizon); trial.status = "SCHEDULED";
        return reply(source, audit(level, trial));
    }

    @SubscribeEvent public static void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("hearthbound-communication-trial")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("configure")
                .then(Commands.argument("arm", StringArgumentType.word())
                    .then(Commands.argument("policy_seed", LongArgumentType.longArg())
                        .then(Commands.argument("horizon", IntegerArgumentType.integer(20, 1200))
                            .then(Commands.argument("destination", BlockPosArgument.blockPos())
                                .executes(ctx -> configure(ctx.getSource(), StringArgumentType.getString(ctx, "arm"),
                                    LongArgumentType.getLong(ctx, "policy_seed"), IntegerArgumentType.getInteger(ctx, "horizon"),
                                    BlockPosArgument.getLoadedBlockPos(ctx, "destination"))))))))
            .then(Commands.literal("configure-network")
                .then(Commands.argument("arm", StringArgumentType.word())
                    .then(Commands.argument("policy_seed", LongArgumentType.longArg())
                        .then(Commands.argument("horizon", IntegerArgumentType.integer(600, 600))
                            .then(Commands.argument("destination", BlockPosArgument.blockPos())
                                .then(Commands.argument("seat_map", StringArgumentType.word())
                                    .then(Commands.argument("block_id", StringArgumentType.word())
                                        .then(Commands.argument("trial_id", StringArgumentType.word())
                                            .executes(ctx -> configureNetwork(ctx.getSource(),
                                                StringArgumentType.getString(ctx, "arm"),
                                                LongArgumentType.getLong(ctx, "policy_seed"),
                                                IntegerArgumentType.getInteger(ctx, "horizon"),
                                                BlockPosArgument.getLoadedBlockPos(ctx, "destination"),
                                                StringArgumentType.getString(ctx, "seat_map"),
                                                StringArgumentType.getString(ctx, "block_id"),
                                                StringArgumentType.getString(ctx, "trial_id")))))))))))
            .then(Commands.literal("enroll").then(Commands.argument("slot", IntegerArgumentType.integer(0, 3))
                .then(Commands.argument("citizen", EntityArgument.entity())
                    .executes(ctx -> enroll(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "slot"),
                        EntityArgument.getEntity(ctx, "citizen"))))))
            .then(Commands.literal("start").executes(ctx -> start(ctx.getSource())))
            .then(Commands.literal("audit").executes(ctx -> reply(ctx.getSource(), audit(ctx.getSource().getLevel(), trial(ctx.getSource().getLevel())))))
            .then(Commands.literal("actors").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> reply(ctx.getSource(), page(ctx.getSource().getLevel(), trial(ctx.getSource().getLevel()),
                    "actors", IntegerArgumentType.getInteger(ctx, "offset"))))))
            .then(Commands.literal("records").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> reply(ctx.getSource(), page(ctx.getSource().getLevel(), trial(ctx.getSource().getLevel()),
                    "records", IntegerArgumentType.getInteger(ctx, "offset")))))));
    }
}
