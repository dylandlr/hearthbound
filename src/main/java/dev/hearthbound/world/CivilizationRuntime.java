package dev.hearthbound.world;

import com.mojang.brigadier.CommandDispatcher;
import dev.hearthbound.civilization.CivilizationContracts;
import dev.hearthbound.civilization.ColonyDecisionTrace;
import dev.hearthbound.civilization.CitizenDecisionHistory;
import dev.hearthbound.civilization.ColonyTaskQueue;
import dev.hearthbound.civilization.ColonyTaskQueue.State;
import dev.hearthbound.civilization.ColonyTaskQueue.Task;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.coordinates.BlockPosArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Opt-in, server-thread colony dispatcher. Source/destination tasks are supplied
 * by an operator; the policy does NOT discover work or claim emergent technology.
 * Only SableHauling performs physical actions and verifies their outcomes.
 */
public final class CivilizationRuntime {
    private static final String MEMORY = "hearthbound.civilization.v1";
    private static final String STORAGE = "hearthbound_colony_tasks_v1";
    private CivilizationRuntime() {}

    private static final class ColonyData extends SavedData {
        final ColonyTaskQueue tasks = new ColonyTaskQueue();
        final CitizenDecisionHistory decisionHistory = new CitizenDecisionHistory(1024);
        boolean enabled;
        boolean hasDestination;
        long destination;
        // Local counters do not expose another citizen's decision activity.
        final java.util.Map<UUID, Long> observationRevisions = new java.util.HashMap<>();

        long nextObservationRevision(UUID citizen) {
            long revision = Math.addExact(observationRevisions.getOrDefault(citizen, 0L), 1L);
            observationRevisions.put(citizen, revision);
            return revision;
        }

        static ColonyData load(CompoundTag root) {
            ColonyData result = new ColonyData();
            result.hasDestination = root.contains("destination", Tag.TAG_LONG);
            if (result.hasDestination) result.destination = root.getLong("destination");
            ListTag entries = root.getList("tasks", Tag.TAG_COMPOUND);
            for (int i = 0; i < entries.size(); i++) {
                CompoundTag e = entries.getCompound(i);
                if (!e.contains("id", Tag.TAG_LONG) ||
                        !e.contains("dimension", Tag.TAG_STRING) ||
                        !e.contains("source", Tag.TAG_LONG) ||
                        !e.contains("destination", Tag.TAG_LONG) ||
                        !e.contains("state", Tag.TAG_STRING))
                    throw new IllegalStateException("Invalid persisted colony task");
                State state = State.valueOf(e.getString("state"));
                UUID owner = e.hasUUID("owner") ? e.getUUID("owner") : null;
                UUID job = e.hasUUID("job") ? e.getUUID("job") : null;
                long tick = e.contains("assignedTick", Tag.TAG_LONG)
                        ? e.getLong("assignedTick") : -1;
                // No automatic retry of a reservation interrupted by a crash.
                result.tasks.restore(new Task(e.getLong("id"), e.getString("dimension"),
                    e.getLong("source"), e.getLong("destination"),
                    state == State.RESERVED ? State.HELD : state, owner, job, tick));
            }
            if (root.contains("decisionHistory", Tag.TAG_LIST)) {
                ListTag history = root.getList("decisionHistory", Tag.TAG_COMPOUND);
                for (int i = 0; i < history.size(); i++) {
                    CompoundTag e = history.getCompound(i);
                    if (!e.contains("task", Tag.TAG_LONG) || !e.hasUUID("citizen")
                        || !e.hasUUID("job") || !e.hasUUID("episode")
                        || !e.hasUUID("decision") || !e.hasUUID("evidence")
                        || !e.contains("revision", Tag.TAG_LONG)
                        || !e.contains("observed", Tag.TAG_LONG)
                        || !e.contains("decided", Tag.TAG_LONG)
                        || !e.contains("assigned", Tag.TAG_LONG)
                        || !e.contains("delivered", Tag.TAG_LONG)
                        || !e.contains("source", Tag.TAG_LONG)
                        || !e.contains("destination", Tag.TAG_LONG)
                        || !e.contains("status", Tag.TAG_STRING))
                        throw new IllegalStateException("Invalid saved decision history");
                    result.decisionHistory.restore(new CitizenDecisionHistory.Entry(
                        e.getLong("task"), e.getUUID("citizen"), e.getUUID("job"),
                        e.getUUID("episode"), e.getUUID("decision"), e.getUUID("evidence"),
                        e.getLong("revision"), e.getLong("observed"), e.getLong("decided"),
                        e.getLong("assigned"), e.getLong("delivered"), e.getLong("source"),
                        e.getLong("destination"),
                        CitizenDecisionHistory.Status.valueOf(e.getString("status"))));
                }
            }
            if (root.contains("historyDeniedCapacity", Tag.TAG_LONG))
                result.decisionHistory.restoreDeniedCapacity(root.getLong("historyDeniedCapacity"));
            // Enabled is deliberately session-scoped and always resets to false.
            return result;
        }

        @Override
        public CompoundTag save(CompoundTag root) {
            ListTag entries = new ListTag();
            for (Task task : tasks.snapshot()) {
                CompoundTag e = new CompoundTag();
                e.putLong("id", task.id());
                e.putString("dimension", task.dimension());
                e.putLong("source", task.source());
                e.putLong("destination", task.destination());
                e.putString("state", task.state().name());
                if (task.owner() != null) e.putUUID("owner", task.owner());
                if (task.job() != null) e.putUUID("job", task.job());
                e.putLong("assignedTick", task.assignedTick());
                entries.add(e);
            }
            root.put("tasks", entries);
            ListTag history = new ListTag();
            for (var entry : decisionHistory.snapshot()) {
                CompoundTag e = new CompoundTag();
                e.putLong("task", entry.taskId());
                e.putUUID("citizen", entry.citizen());
                e.putUUID("job", entry.job());
                e.putUUID("episode", entry.episode());
                e.putUUID("decision", entry.decision());
                e.putUUID("evidence", entry.evidence());
                e.putLong("revision", entry.revision());
                e.putLong("observed", entry.observedTick());
                e.putLong("decided", entry.decisionTick());
                e.putLong("assigned", entry.assignedTick());
                e.putLong("delivered", entry.deliveredTick());
                e.putLong("source", entry.source());
                e.putLong("destination", entry.destination());
                e.putString("status", entry.status().name());
                history.add(e);
            }
            root.put("decisionHistory", history);
            root.putLong("historyDeniedCapacity", decisionHistory.deniedCapacity());
            if (hasDestination) root.putLong("destination", destination);
            return root;
        }
    }

    private static ColonyData data(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(ColonyData::load,
                ColonyData::new, STORAGE);
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("hearthbound-colony")
            .requires(source -> source.hasPermission(2))
            .then(Commands.literal("enable").executes(ctx -> {
                data(ctx.getSource().getLevel()).enabled = true;
                ctx.getSource().sendSuccess(() -> Component.literal(
                    "Colony dispatch enabled in this dimension for this server session"), false);
                return 1;
            }))
            .then(Commands.literal("disable").executes(ctx -> {
                data(ctx.getSource().getLevel()).enabled = false;
                ctx.getSource().sendSuccess(() -> Component.literal(
                    "Dispatch disabled; active jobs retain all existing recovery gates"), false);
                return 1;
            }))
            .then(Commands.literal("set-destination")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        ServerLevel level = ctx.getSource().getLevel();
                        BlockPos pos = BlockPosArgument.getLoadedBlockPos(ctx, "position");
                        if (level.getBlockEntity(pos) == null) {
                            ctx.getSource().sendFailure(Component.literal(
                                "Destination must be a loaded block entity"));
                            return 0;
                        }
                        ColonyData board = data(level);
                        board.destination = pos.asLong();
                        board.hasDestination = true;
                        board.setDirty();
                        ctx.getSource().sendSuccess(() -> Component.literal(
                            "Registered shared destination " + pos
                            + "; local citizen observations may now propose wheat hauls"), false);
                        return 1;
                    })))
            .then(Commands.literal("add-haul")
                .then(Commands.argument("source", BlockPosArgument.blockPos())
                    .then(Commands.argument("destination", BlockPosArgument.blockPos())
                        .executes(ctx -> {
                            ServerLevel level = ctx.getSource().getLevel();
                            BlockPos from = BlockPosArgument.getLoadedBlockPos(ctx, "source");
                            BlockPos to = BlockPosArgument.getLoadedBlockPos(ctx, "destination");
                            if (from.equals(to)) {
                                ctx.getSource().sendFailure(Component.literal("Identical endpoints"));
                                return 0;
                            }
                            ColonyData data = data(level);
                            Task task = data.tasks.enqueue(level.dimension().location().toString(),
                                    from.asLong(), to.asLong());
                            data.setDirty();
                            ctx.getSource().sendSuccess(() -> Component.literal(
                                "Queued operator-defined colony task=" + task.id()
                                + " (no inventory action performed)"), false);
                            return 1;
                        }))))
            .then(Commands.literal("decision-audit").executes(ctx -> {
                ServerLevel level = ctx.getSource().getLevel();
                ColonyData board = data(level);
                UUID currentEpisode = SourceReportSession.episode(level);
                Set<UUID> verifiedCitizens = new java.util.HashSet<>();
                for (Task task : board.tasks.snapshot()) {
                    if (task.state() != State.DONE || task.owner() == null)
                        continue;
                    var entity = level.getEntity(task.owner());
                    if (!(entity instanceof Villager citizen)) continue;
                    CompoundTag memory = citizen.getPersistentData().getCompound(MEMORY);
                    BlockPos source = BlockPos.of(task.source());
                    String target = task.dimension() + "|" + source.getX() + ","
                            + source.getY() + "," + source.getZ();
                    if (!memory.hasUUID("episodeId") || !memory.hasUUID("decisionId")
                            || !memory.hasUUID("evidenceId") || !memory.hasUUID("jobId")
                            || !memory.contains("snapshotRevision", Tag.TAG_LONG)
                            || !memory.contains("evidenceObservedTick", Tag.TAG_LONG)
                            || !memory.contains("decisionTick", Tag.TAG_LONG)
                            || !memory.contains("taskId", Tag.TAG_LONG)
                            || !currentEpisode.equals(memory.getUUID("episodeId"))
                            || !"hearthbound.civilization.v3".equals(memory.getString("schema"))
                            || !"GATHER".equals(memory.getString("actionKind"))
                            || !target.equals(memory.getString("evidenceTarget"))
                            || memory.getLong("taskId") != task.id()
                            || !memory.getUUID("jobId").equals(task.job())
                            || memory.getLong("snapshotRevision") < 1)
                        continue;
                    long observed = memory.getLong("evidenceObservedTick");
                    long decided = memory.getLong("decisionTick");
                    if (observed < 0 || decided < observed || decided > task.assignedTick()
                            || task.assignedTick() > level.getGameTime()
                            || task.assignedTick() - observed >
                                CivilizationContracts.MAX_GATHER_EVIDENCE_AGE_TICKS)
                        continue;
                    verifiedCitizens.add(task.owner());
                }
                ctx.getSource().sendSuccess(() -> Component.literal(
                    "COLONY_DECISIONS_V0_3 latest_scoped_completed_citizens="
                    + verifiedCitizens.size()
                    + " scope=CURRENT_SESSION_LATEST_CITIZEN_MEMORY"
                    + " physical_reward_authorized=false"), false);
                return 1;
            }))
            .then(Commands.literal("decision-traces").executes(ctx -> {
                ServerLevel level = ctx.getSource().getLevel();
                ColonyData board = data(level);
                UUID episode = SourceReportSession.episode(level);
                List<String> traces = new java.util.ArrayList<>();
                for (Task task : board.tasks.snapshot()) {
                    if (task.state() != State.DONE || task.owner() == null || task.job() == null)
                        continue;
                    var entity = level.getEntity(task.owner());
                    if (!(entity instanceof Villager citizen)) continue;
                    CompoundTag memory = citizen.getPersistentData().getCompound(MEMORY);
                    CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
                    if (!memory.hasUUID("episodeId") || !memory.hasUUID("decisionId")
                            || !memory.hasUUID("evidenceId") || !memory.hasUUID("jobId")
                            || !memory.contains("snapshotRevision", Tag.TAG_LONG)
                            || !memory.contains("evidenceObservedTick", Tag.TAG_LONG)
                            || !memory.contains("decisionTick", Tag.TAG_LONG)
                            || !memory.contains("taskId", Tag.TAG_LONG)
                            || !haul.contains("physicalDeliveredTick", Tag.TAG_LONG)
                            || !episode.equals(memory.getUUID("episodeId"))
                            || !"hearthbound.civilization.v3".equals(memory.getString("schema"))
                            || memory.getLong("taskId") != task.id()
                            || !task.job().equals(memory.getUUID("jobId"))
                            || !SableHauling.completedJob(citizen, task.job(),
                                BlockPos.of(task.destination())))
                        continue;
                    String target = task.dimension() + "|" + BlockPos.of(task.source()).getX()
                        + "," + BlockPos.of(task.source()).getY() + ","
                        + BlockPos.of(task.source()).getZ();
                    if (!target.equals(memory.getString("evidenceTarget")))
                        continue;
                    try {
                        var assignment = SableHauling.completedAssignment(level, citizen,
                            task.job(), BlockPos.of(task.destination()));
                        if (assignment.source() != task.source()
                                || assignment.assignedTick() != task.assignedTick()
                                || !assignment.citizen().equals(task.owner()))
                            continue;
                        var trace = new ColonyDecisionTrace.Trace(task.id(), task.owner(),
                            task.job(), memory.getUUID("episodeId"),
                            memory.getUUID("decisionId"), memory.getUUID("evidenceId"),
                            memory.getLong("snapshotRevision"),
                            memory.getLong("evidenceObservedTick"),
                            memory.getLong("decisionTick"), task.assignedTick(),
                            haul.getLong("physicalDeliveredTick"),
                            memory.getString("actionKind"), target,
                            memory.getString("decisionPolicy"));
                        if (ColonyDecisionTrace.valid(trace, episode, level.getGameTime()))
                            traces.add(ColonyDecisionTrace.encode(trace));
                    } catch (RuntimeException invalid) {
                        // Unloaded, conflicting or incomplete evidence is omitted.
                    }
                }
                String result = "COLONY_TRACES_V0_4 count=" + traces.size()
                    + " episode=" + episode
                    + " scope=LOADED_LATEST_CITIZEN_MEMORY_AND_PHYSICAL_JOB"
                    + " entries=" + String.join(";", traces)
                    + " learning_authorized=false reward_authorized=false";
                ctx.getSource().sendSuccess(() -> Component.literal(result), false);
                return 1;
            }))
            .then(Commands.literal("source-readiness-audit")
                .then(Commands.argument("position", BlockPosArgument.blockPos())
                    .executes(ctx -> {
                        ServerLevel level = ctx.getSource().getLevel();
                        ColonyData board = data(level);
                        BlockPos source = BlockPosArgument.getBlockPos(ctx, "position");
                        // One operator-selected source. Never load chunks, scan
                        // distant world data, or mutate citizen/task/inventory state.
                        StringBuilder report = new StringBuilder(
                            "COLONY_SOURCE_READINESS_V0_9 source="
                            + source.getX() + "," + source.getY() + "," + source.getZ()
                            + " source_chunk_loaded=" + level.hasChunkAt(source));
                        if (!level.hasChunkAt(source)) {
                            report.append(" citizens=0 unknown_unloaded=true");
                        } else {
                            var candidates = level.getEntitiesOfClass(Villager.class,
                                new net.minecraft.world.phys.AABB(source).inflate(16.0),
                                CitizenSourceKnowledge::isCitizen);
                            candidates.sort(java.util.Comparator.comparing(v -> v.getUUID().toString()));
                            int visible = Math.min(candidates.size(), 16);
                            report.append(" citizens=").append(candidates.size())
                                .append(" truncated=").append(candidates.size() > visible);
                            for (int i = 0; i < visible; i++) {
                                Villager citizen = candidates.get(i);
                                UUID id = citizen.getUUID();
                                long done = board.tasks.snapshot().stream().filter(t ->
                                    t.state() == State.DONE && id.equals(t.owner())).count();
                                long assigned = board.tasks.snapshot().stream().filter(t ->
                                    t.state() == State.ASSIGNED && id.equals(t.owner())).count();
                                long held = board.tasks.snapshot().stream().filter(t ->
                                    (t.state() == State.HELD || t.state() == State.RESERVED)
                                    && id.equals(t.owner())).count();
                                double distanceSq = citizen.distanceToSqr(
                                    source.getX() + 0.5, source.getY() + 0.5,
                                    source.getZ() + 0.5);
                                BlockPos position = citizen.blockPosition();
                                boolean localScanReach = Math.abs(position.getX() - source.getX()) <= 2
                                    && Math.abs(position.getY() - source.getY()) <= 1
                                    && Math.abs(position.getZ() - source.getZ()) <= 2;
                                report.append(" citizen_").append(i).append("=")
                                    .append(id).append(",pos:")
                                    .append(position.getX()).append(":")
                                    .append(position.getY()).append(":")
                                    .append(position.getZ())
                                    .append(",distance_sq:").append((long)Math.ceil(distanceSq))
                                    .append(",local_scan_reach:").append(localScanReach)
                                    .append(",task_menu_reach:").append(distanceSq <= 256.0)
                                    .append(",active_motor:").append(SableHauling.active(citizen))
                                    .append(",done:").append(done)
                                    .append(",assigned:").append(assigned)
                                    .append(",held:").append(held);
                            }
                        }
                        report.append(" strictly_read_only=true policy_control=false")
                            .append(" reward_authorized=false");
                        String output = report.toString();
                        ctx.getSource().sendSuccess(() -> Component.literal(output), false);
                        return 1;
                    })))
            .then(Commands.literal("physical-reconciliation-audit").executes(ctx -> {
                ServerLevel level = ctx.getSource().getLevel();
                ColonyData board = data(level);
                int assigned = 0;
                int assignedLoadedIncomplete = 0;
                int assignedLoadedPhysicallyComplete = 0;
                int assignedUnloaded = 0;
                int done = 0;
                int doneLoaded = 0;
                int doneUnloaded = 0;
                java.util.List<String> anomalies = new java.util.ArrayList<>();
                for (Task task : board.tasks.snapshot()) {
                    if (task.state() != State.ASSIGNED && task.state() != State.DONE)
                        continue;
                    if (task.state() == State.ASSIGNED) assigned++;
                    else done++;
                    var entity = task.owner() == null ? null : level.getEntity(task.owner());
                    if (!(entity instanceof Villager citizen)) {
                        if (task.state() == State.ASSIGNED) assignedUnloaded++;
                        else doneUnloaded++;
                        continue;
                    }
                    if (task.state() == State.DONE) {
                        doneLoaded++;
                        continue;
                    }
                    if (task.job() == null || !SableHauling.completedJob(citizen,
                            task.job(), BlockPos.of(task.destination()))) {
                        assignedLoadedIncomplete++;
                        if (anomalies.size() < 8)
                            anomalies.add("not-complete:" + task.id() + ":" + task.owner());
                    } else {
                        assignedLoadedPhysicallyComplete++;
                        if (anomalies.size() < 8)
                            anomalies.add("physical-complete-queue-assigned:" + task.id()
                                + ":" + task.owner());
                    }
                }
                final String report = "COLONY_PHYSICAL_RECONCILIATION_V0_6 assigned="
                    + assigned + " assigned_loaded_incomplete=" + assignedLoadedIncomplete
                    + " assigned_loaded_physically_complete=" + assignedLoadedPhysicallyComplete
                    + " assigned_unloaded=" + assignedUnloaded
                    + " done=" + done + " done_loaded=" + doneLoaded
                    + " done_unloaded=" + doneUnloaded
                    + " history_records=" + board.decisionHistory.snapshot().size()
                    + " history_capacity_denials=" + board.decisionHistory.deniedCapacity()
                    + " anomalies=" + String.join(";", anomalies)
                    + " strictly_read_only=true policy_control=false reward_authorized=false";
                ctx.getSource().sendSuccess(() -> Component.literal(report), false);
                return 1;
            }))
            .then(Commands.literal("history-audit").executes(ctx -> {
                ColonyData board = data(ctx.getSource().getLevel());
                var records = board.decisionHistory.snapshot();
                long completed = records.stream()
                    .filter(e -> e.status() == CitizenDecisionHistory.Status.PHYSICALLY_COMPLETED)
                    .count();
                long pending = records.size() - completed;
                ctx.getSource().sendSuccess(() -> Component.literal(
                    "COLONY_HISTORY_V0_5 records=" + records.size()
                    + " physically_completed=" + completed
                    + " assigned_without_verified_completion=" + pending
                    + " capacity_denials=" + board.decisionHistory.deniedCapacity()
                    + " policy_control=false reward_authorized=false"
                    + " scope=PERSISTED_SAVEDDATA_CURRENT_DIMENSION"), false);
                return 1;
            }))
            .then(Commands.literal("audit").executes(ctx -> {
                ColonyData data = data(ctx.getSource().getLevel());
                long queued = data.tasks.snapshot().stream()
                    .filter(t -> t.state() == State.QUEUED).count();
                long assigned = data.tasks.snapshot().stream()
                    .filter(t -> t.state() == State.ASSIGNED).count();
                long held = data.tasks.snapshot().stream()
                    .filter(t -> t.state() == State.HELD || t.state() == State.RESERVED).count();
                long done = data.tasks.snapshot().stream()
                    .filter(t -> t.state() == State.DONE).count();
                long distinctCompletedCitizens = data.tasks.snapshot().stream()
                    .filter(t -> t.state() == State.DONE).map(Task::owner)
                    .distinct().count();
                ctx.getSource().sendSuccess(() -> Component.literal(
                    "COLONY_V1 enabled=" + data.enabled + " queued=" + queued
                    + " assigned=" + assigned + " held=" + held + " done=" + done
                    + " distinct_completed_citizens=" + distinctCompletedCitizens
                    + " destination_registered=" + data.hasDestination
                    + " task_sources=OPERATOR_OR_LOCAL_OBSERVATION"
                    + " decision_contract=V0_3"
                    + " reward_authorized=false"), false);
                return 1;
            })));
    }

    /** Called for idle, marked citizens on the authoritative server thread. */
    public static boolean tick(ServerLevel level, Villager citizen) {
        ColonyData board = data(level);
        if (!board.enabled || !CitizenSourceKnowledge.isCitizen(citizen))
            return false;
        String dimension = level.dimension().location().toString();
        UUID citizenId = citizen.getUUID();
        for (Task assigned : board.tasks.snapshot()) {
            if (!citizenId.equals(assigned.owner()) || !dimension.equals(assigned.dimension()))
                continue;
            if (assigned.state() == State.ASSIGNED) {
                if (SableHauling.completedJob(citizen, assigned.job(),
                        BlockPos.of(assigned.destination()))) {
                    board.tasks.finish(assigned.id(), citizenId, assigned.job());
                    board.setDirty();
                    // Research history is read-only. Never retry, cancel or
                    // mutate physical work on an observation-log error.
                    try {
                        CompoundTag haul = citizen.getPersistentData()
                            .getCompound("hearthbound.haul");
                        if (haul.contains("physicalDeliveredTick", Tag.TAG_LONG)) {
                            var assignment = SableHauling.completedAssignment(level, citizen,
                                assigned.job(), BlockPos.of(assigned.destination()));
                            if (board.decisionHistory.complete(assigned.job(), citizenId,
                                    SourceReportSession.episode(level),
                                    haul.getLong("physicalDeliveredTick"),
                                    assignment.source(), assignment.destination()))
                                board.setDirty();
                        }
                    } catch (RuntimeException invalidHistory) {
                        org.apache.logging.log4j.LogManager.getLogger().warn(
                            "Colony history incomplete for completed physical job {}",
                            assigned.job(), invalidHistory);
                    }
                } else if (!SableHauling.active(citizen)) {
                    board.tasks.hold(assigned.id(), citizenId);
                    board.setDirty();
                    return true;
                } else return true;
            } else if (assigned.state() == State.RESERVED || assigned.state() == State.HELD) {
                return true; // Never retry uncertain reservations automatically.
            }
        }
        if (SableHauling.active(citizen)) return true;
        // Only loaded, nearby inventories may seed tasks; never sample distant
        // chunk inventory, bypass the sensor, or infer success from a proposal.
        // Evaluate once per citizen tick cycle (20 game ticks). Waiting 100 ticks
        // allowed unloaded/vanilla-wandering citizens to leave a small sensor
        // neighborhood without ever recording their initial nearby chest.
        if (board.hasDestination) {
            BlockPos destination = BlockPos.of(board.destination);
            if (level.hasChunkAt(destination) && level.getBlockEntity(destination) != null) {
                BlockPos center = citizen.blockPosition();
                boolean filled = false;
                for (int dx = -2; dx <= 2 && !filled; dx++) {
                    for (int dy = -1; dy <= 1 && !filled; dy++) {
                        for (int dz = -2; dz <= 2; dz++) {
                            BlockPos source = center.offset(dx, dy, dz);
                            if (source.equals(destination) || !level.hasChunkAt(source)
                                    || level.getBlockEntity(source) == null)
                                continue;
                            SourceWheatObservation.Snapshot sensed =
                                SourceWheatObservation.inspect(level, source, citizen);
                            if (sensed.state() != SourceWheatObservation.State.AVAILABLE)
                                continue;
                            CitizenSourceKnowledge.remember(level, source, citizen, sensed);
                            int count = board.tasks.snapshot().size();
                            Task proposed = board.tasks.propose(dimension,
                                source.asLong(), destination.asLong());
                            if (proposed != null && board.tasks.snapshot().size() > count)
                                board.setDirty();
                            // Don't keep scanning after reaching the bounded task cap.
                            if (proposed == null) { filled = true; break; }
                        }
                    }
                }
            }
        }
        // Individual differences affect which feasible, locally witnessed task
        // is chosen. This remains scripted task ranking, not learned specialization.
        var traits = dev.hearthbound.civilization.CitizenGoalPolicy.fromIdentity(
                citizenId, HearthboundWorldIdentity.get(level).hashCode());
        var menu = new java.util.ArrayList<
                dev.hearthbound.civilization.CitizenGoalPolicy.Candidate>();
        var eligible = new java.util.HashMap<Long, Task>();
        var observations = new java.util.HashMap<Long, CivilizationContracts.Observation>();
        var decisions = new java.util.HashMap<Long, CivilizationContracts.Decision>();
        UUID episode = SourceReportSession.episode(level);
        for (Task task : board.tasks.snapshot()) {
            if (task.state() != State.QUEUED || !dimension.equals(task.dimension()))
                continue;
            BlockPos from = BlockPos.of(task.source());
            BlockPos to = BlockPos.of(task.destination());
            if (!level.hasChunkAt(from) || !level.hasChunkAt(to) ||
                    citizen.distanceToSqr(from.getX()+0.5, from.getY()+0.5,
                        from.getZ()+0.5) > 16.0 * 16.0)
                continue;
            SourceWheatObservation.Snapshot sensor =
                SourceWheatObservation.inspect(level, from, citizen);
            if (sensor.state() != SourceWheatObservation.State.AVAILABLE)
                continue;
            CitizenSourceKnowledge.remember(level, from, citizen, sensor);
            String target = dimension + "|" + from.getX() + "," + from.getY()
                    + "," + from.getZ();
            long revision = board.nextObservationRevision(citizenId);
            UUID evidenceId = UUID.nameUUIDFromBytes(
                    (episode + ":" + citizenId + ":" + target + ":" + sensor.tick()
                        + ":" + revision)
                    .getBytes(StandardCharsets.UTF_8));
            var evidence = new CivilizationContracts.Evidence(evidenceId, citizenId,
                citizenId, target, CivilizationContracts.EvidenceKind.DIRECT,
                sensor.tick(), level.getGameTime(), sensor.wheat(), episode, revision);
            var observation = new CivilizationContracts.Observation(citizenId,
                level.getGameTime(), List.of(evidence),
                Set.of(CivilizationContracts.ActionKind.GATHER,
                       CivilizationContracts.ActionKind.WAIT), episode, revision);
            var decision = new CivilizationContracts.ScriptedPolicy().decide(observation);
            CivilizationContracts.validate(observation, decision);
            if (decision.action() != CivilizationContracts.ActionKind.GATHER
                    || !evidenceId.equals(decision.evidenceId()))
                continue;
            long distance = (long) Math.ceil(citizen.distanceToSqr(
                from.getX()+0.5, from.getY()+0.5, from.getZ()+0.5));
            menu.add(new dev.hearthbound.civilization.CitizenGoalPolicy.Candidate(
                task.id(), sensor.wheat(), distance, 0));
            eligible.put(task.id(), task);
            observations.put(task.id(), observation);
            decisions.put(task.id(), decision);
        }
        var selection = dev.hearthbound.civilization.CitizenGoalPolicy.select(traits, menu);
        Task candidate = selection == null ? null : eligible.get(selection.taskId());
        if (candidate == null) return false;
        long chosenId = candidate.id();
        var selectedObservation = observations.get(chosenId);
        var selectedDecision = decisions.get(chosenId);
        // Validate against the authoritative dispatch tick immediately before
        // reserving work. Actual pickup still uses SableHauling's local gates.
        CivilizationContracts.validateAt(selectedObservation, selectedDecision,
                level.getGameTime());
        Task reserved = board.tasks.reserve(citizenId, dimension, t -> t.id() == chosenId);
        if (reserved == null) return false;
        board.setDirty();
        try {
            SableHauling.assign(level, citizen, BlockPos.of(reserved.source()),
                    BlockPos.of(reserved.destination()));
            CompoundTag haul = citizen.getPersistentData().getCompound("hearthbound.haul");
            if (!haul.hasUUID("jobId") || !haul.contains("assignedTick", Tag.TAG_LONG))
                throw new IllegalStateException("Physical assignment identity absent");
            board.tasks.assign(reserved.id(), citizenId,
                    haul.getUUID("jobId"), haul.getLong("assignedTick"));
            board.setDirty();
            CompoundTag memory = citizen.getPersistentData().getCompound(MEMORY);
            memory.putString("schema", "hearthbound.civilization.v3");
            memory.putUUID("episodeId", episode);
            memory.putLong("snapshotRevision", selectedObservation.snapshotRevision());
            memory.putUUID("decisionId", selectedDecision.id());
            memory.putUUID("evidenceId", selectedDecision.evidenceId());
            memory.putLong("evidenceObservedTick", selectedObservation.evidence().get(0).observedTick());
            memory.putString("evidenceTarget", selectedDecision.target());
            memory.putString("actionKind", selectedDecision.action().name());
            memory.putString("goal", "SUPPLY_WHEAT");
            memory.putString("decisionPolicy", "DETERMINISTIC_TRAIT_RANK_V1");
            memory.putInt("diligence", traits.diligence());
            memory.putInt("exploration", traits.exploration());
            memory.putInt("cooperation", traits.cooperation());
            memory.putLong("taskId", reserved.id());
            memory.putUUID("jobId", haul.getUUID("jobId"));
            memory.putLong("decisionTick", level.getGameTime());
            citizen.getPersistentData().put(MEMORY, memory);
            try {
                boolean retained = board.decisionHistory.register(
                    new CitizenDecisionHistory.Entry(reserved.id(), citizenId,
                        haul.getUUID("jobId"), episode, selectedDecision.id(),
                        selectedDecision.evidenceId(), selectedObservation.snapshotRevision(),
                        selectedObservation.evidence().get(0).observedTick(),
                        selectedDecision.tick(), haul.getLong("assignedTick"), -1L,
                        reserved.source(), reserved.destination(),
                        CitizenDecisionHistory.Status.ASSIGNED));
                board.setDirty();
                if (!retained)
                    org.apache.logging.log4j.LogManager.getLogger().warn(
                        "Colony history capacity reached for job {}", haul.getUUID("jobId"));
            } catch (RuntimeException invalidHistory) {
                org.apache.logging.log4j.LogManager.getLogger().warn(
                    "Colony history could not record job {}", haul.getUUID("jobId"),
                    invalidHistory);
            }
        } catch (RuntimeException failure) {
            // Do not replay a possibly partly mutated assignment.
            board.tasks.hold(reserved.id(), citizenId);
            board.setDirty();
            org.apache.logging.log4j.LogManager.getLogger().warn(
                "Hearthbound colony task held for manual audit: task={} citizen={}",
                reserved.id(), citizenId, failure);
        }
        return true;
    }
}
