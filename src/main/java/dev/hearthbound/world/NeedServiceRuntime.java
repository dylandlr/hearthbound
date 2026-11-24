package dev.hearthbound.world;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonNull;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import dev.hearthbound.civilization.NeedServiceKernel;
import dev.hearthbound.civilization.CitizenServiceLearning;
import dev.hearthbound.civilization.ServiceValueLearner;
import dev.hearthbound.civilization.ServiceValueLearner.Candidate;
import dev.hearthbound.civilization.ServiceValueLearner.Kind;
import dev.hearthbound.civilization.ServiceValueLearner.Outcome;
import dev.hearthbound.civilization.ServiceValueLearner.ProductionReceipt;
import dev.hearthbound.civilization.NeedServiceKernel.Commitment;
import dev.hearthbound.civilization.NeedServiceKernel.Knowledge;
import dev.hearthbound.civilization.NeedServiceKernel.Need;
import dev.hearthbound.civilization.NeedServiceKernel.Scope;
import dev.hearthbound.civilization.NeedServiceKernel.State;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
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
 * Opt-in, Minecraft-facing hierarchy: local sensing -> private requests -> one
 * persistent option -> the existing physical motor. Geometry and the enrolled
 * roster are public; stock, requests and source candidates are never read from
 * another citizen's memory. The kernel's shared state is an execution arbiter,
 * not an actor observation or a global task board.
 *
 * Each citizen scores privately eligible options with its own persisted RLS
 * outcome estimator and explicit authored priors. Any citizen can carry a
 * request or supply material; these capabilities do not assign occupations.
 * Storage transfers and complete Create/output cycles have separate evidence.
 *
 * Plain native hauling does not have the experimental report dispatch journal.
 * Consequently every restored service motor is held before it can tick; this
 * adapter does not claim crash-atomic pickup or automatically reconcile cargo.
 */
public final class NeedServiceRuntime {
    private static final String STORAGE = "hearthbound_need_services_v1";
    private static final String MEMORY = "hearthbound.need_services.v1";
    private static final String HAUL = "hearthbound.haul";
    private static final String POLICY = "PRIVATE_CONTEXTUAL_SERVICE_RLS_V1";
    private static final int MAX_SITES = 8, MAX_CITIZENS = 16, MAX_RECORDS = 4096;
    private static final long NEED_TTL = 600, LEASE_TICKS = 1200;
    private static final Gson GSON = new Gson();
    private NeedServiceRuntime() {}

    private static final class Buffer {
        final long position;
        int target;
        long revision;
        final Long machine;
        Buffer(long position, int target, long revision) { this(position, target, revision, null); }
        Buffer(long position, int target, long revision, Long machine) {
            this.position = position; this.target = target; this.revision = revision; this.machine = machine;
        }
        boolean production() { return machine != null; }
        String item() { return production() ? "create:wheat_flour" : "minecraft:wheat"; }
    }

    private static final class ServiceData extends SavedData {
        final Map<Long, Buffer> buffers = new LinkedHashMap<>();
        final Set<Long> sources = new LinkedHashSet<>();
        final Set<UUID> enrolled = new LinkedHashSet<>();
        final List<JsonObject> records = new ArrayList<>();
        // Session admissions are deliberately absent from saved authority. An
        // old private book remains auditable but cannot become fresh on restart.
        final Map<UUID, Map<UUID, Long>> admitted = new LinkedHashMap<>();
        final Map<UUID, CitizenServiceLearning> learners = new LinkedHashMap<>();
        final Map<UUID, String> savedLearners = new LinkedHashMap<>();
        NeedServiceKernel kernel;
        String savedKernel;
        String failure = "";
        UUID session;
        boolean enabled;
        long assigned, transfers, cancelled, capacityDenials, productionJobs, outputUnits;

        static ServiceData load(CompoundTag root) {
            ServiceData d = new ServiceData();
            try {
                if (root.getInt("schema") != 1 && root.getInt("schema") != 2)
                    throw new IllegalStateException("Unknown service schema");
                ListTag buffers = root.getList("buffers", Tag.TAG_COMPOUND);
                if (buffers.size() > MAX_SITES) throw new IllegalStateException("Too many buffer sites");
                for (int i = 0; i < buffers.size(); i++) {
                    CompoundTag b = buffers.getCompound(i);
                    long pos = b.getLong("position"); int target = b.getInt("target");
                    long revision = b.getLong("revision");
                    if (target < 0 || target > 64 || revision < 0 || d.buffers.containsKey(pos))
                        throw new IllegalStateException("Invalid saved buffer");
                    d.buffers.put(pos, new Buffer(pos, target, revision, b.contains("machine") ? b.getLong("machine") : null));
                }
                Set<Long> machines = new LinkedHashSet<>();
                for (Buffer b : d.buffers.values()) if (b.production()) {
                    if (b.machine == b.position || d.buffers.containsKey(b.machine) || !machines.add(b.machine))
                        throw new IllegalStateException("Invalid production geometry");
                }
                for (long pos : root.getLongArray("sources")) {
                    if (!d.sources.add(pos) || d.sources.size() > MAX_SITES || d.buffers.containsKey(pos) || machines.contains(pos))
                        throw new IllegalStateException("Invalid saved source geometry");
                }
                ListTag citizens = root.getList("enrolled", Tag.TAG_COMPOUND);
                if (citizens.size() > MAX_CITIZENS) throw new IllegalStateException("Too many service citizens");
                for (int i = 0; i < citizens.size(); i++) {
                    CompoundTag c = citizens.getCompound(i);
                    if (!c.hasUUID("citizen") || !d.enrolled.add(c.getUUID("citizen")))
                        throw new IllegalStateException("Invalid service citizen identity");
                }
                ListTag learners = root.getList("learners", Tag.TAG_COMPOUND);
                for (int i = 0; i < learners.size(); i++) {
                    CompoundTag entry = learners.getCompound(i);
                    if (!entry.hasUUID("citizen") || !d.enrolled.contains(entry.getUUID("citizen"))
                            || d.savedLearners.putIfAbsent(entry.getUUID("citizen"), ServiceJsonPayload.read(entry, "snapshot")) != null)
                        throw new IllegalStateException("Invalid private learning owner");
                }
                d.savedKernel = ServiceJsonPayload.read(root, "kernel");
                if (d.savedKernel.isBlank()) throw new IllegalStateException("Missing service kernel");
                JsonArray records = GSON.fromJson(ServiceJsonPayload.read(root, "records"), JsonArray.class);
                if (records == null || records.size() > MAX_RECORDS)
                    throw new IllegalStateException("Invalid service records");
                for (var e : records) d.records.add(e.getAsJsonObject());
                for (int i = 0; i < d.records.size(); i++)
                    if (d.records.get(i).get("sequence").getAsInt() != i + 1)
                        throw new IllegalStateException("Service record sequence gap");
                d.assigned = root.getLong("assigned"); d.transfers = root.getLong("transfers");
                d.cancelled = root.getLong("cancelled"); d.capacityDenials = root.getLong("capacityDenials");
                d.productionJobs = root.getLong("productionJobs"); d.outputUnits = root.getLong("outputUnits");
                if (d.assigned < 0 || d.transfers < 0 || d.cancelled < 0 || d.capacityDenials < 0
                        || d.productionJobs < 0 || d.outputUnits < 0)
                    throw new IllegalStateException("Invalid service counters");
            } catch (RuntimeException invalid) {
                d.failure = "PERSISTENCE_REQUIRES_REVIEW: " + invalid.getMessage();
            }
            // Enabled/session and fresh admissions are intentionally never restored.
            return d;
        }

        @Override public CompoundTag save(CompoundTag root) {
            root.putInt("schema", 2);
            ListTag buffers = new ListTag();
            for (Buffer b : this.buffers.values()) {
                CompoundTag entry = new CompoundTag(); entry.putLong("position", b.position);
                entry.putInt("target", b.target); entry.putLong("revision", b.revision);
                if (b.production()) entry.putLong("machine", b.machine); buffers.add(entry);
            }
            root.put("buffers", buffers); root.putLongArray("sources", sources.stream().mapToLong(Long::longValue).toArray());
            ListTag citizens = new ListTag();
            for (UUID citizen : enrolled) {
                CompoundTag entry = new CompoundTag(); entry.putUUID("citizen", citizen); citizens.add(entry);
            }
            root.put("enrolled", citizens);
            ListTag learning = new ListTag();
            for (UUID citizen : enrolled) {
                String snapshot = learners.containsKey(citizen) ? GSON.toJson(learners.get(citizen).snapshot()) : savedLearners.get(citizen);
                if (snapshot == null) continue;
                CompoundTag entry = new CompoundTag(); entry.putUUID("citizen", citizen);
                ServiceJsonPayload.write(entry, "snapshot", snapshot); learning.add(entry);
            }
            root.put("learners", learning);
            ServiceJsonPayload.write(root, "kernel", kernel == null ? (savedKernel == null ? "" : savedKernel) : GSON.toJson(kernel.snapshot()));
            ServiceJsonPayload.write(root, "records", GSON.toJson(records));
            root.putLong("assigned", assigned); root.putLong("transfers", transfers);
            root.putLong("cancelled", cancelled); root.putLong("capacityDenials", capacityDenials);
            root.putLong("productionJobs", productionJobs); root.putLong("outputUnits", outputUnits);
            return root;
        }
    }

    private static ServiceData data(ServerLevel level) {
        ServiceData d = level.getDataStorage().computeIfAbsent(ServiceData::load, ServiceData::new, STORAGE);
        if (d.kernel == null && d.failure.isEmpty()) {
            try {
                Scope scope = new Scope(HearthboundWorldIdentity.get(level), level.dimension().location().toString());
                d.kernel = d.savedKernel == null ? new NeedServiceKernel(scope)
                    : NeedServiceKernel.restore(GSON.fromJson(d.savedKernel, NeedServiceKernel.Snapshot.class), scope, level.getGameTime());
                for (UUID citizen : d.enrolled) {
                    String saved = d.savedLearners.get(citizen);
                    d.learners.put(citizen, saved == null ? new CitizenServiceLearning(scope, citizen)
                        : CitizenServiceLearning.restore(GSON.fromJson(saved, CitizenServiceLearning.Snapshot.class), scope, citizen, level.getGameTime()));
                }
                long productionSamples = d.learners.values().stream().mapToLong(l -> l.status().productionSamples()).sum();
                long output = d.learners.values().stream().mapToLong(l -> l.status().independentlyVerifiedOutputUnits()).sum();
                if (productionSamples != d.productionJobs || output != d.outputUnits)
                    throw new IllegalStateException("Production counters disagree with private settled evidence");
                d.session = SourceReportSession.episode(level);
            } catch (RuntimeException invalid) {
                d.failure = "PERSISTENCE_REQUIRES_REVIEW: " + invalid.getMessage();
            }
        }
        return d;
    }

    private static CitizenServiceLearning learner(ServiceData d, UUID citizen) {
        return d.learners.computeIfAbsent(citizen, id -> new CitizenServiceLearning(d.kernel.scope(), id));
    }

    /** Sticky ownership also holds unloaded/restored actors while dispatch is off. */
    static boolean controls(Villager citizen) {
        return citizen.getPersistentData().getCompound(MEMORY).getBoolean("enrolled");
    }

    private static CompoundTag memory(Villager citizen) {
        return citizen.getPersistentData().getCompound(MEMORY);
    }

    private static void saveMemory(Villager citizen, CompoundTag memory) {
        citizen.getPersistentData().put(MEMORY, memory);
    }

    private static UUID needId(ServiceData d, long site) {
        return UUID.nameUUIDFromBytes((d.kernel.scope().world() + "|" + d.kernel.scope().dimension()
            + (d.buffers.get(site) != null && d.buffers.get(site).production() ? "|flour-buffer|" : "|wheat-buffer|") + site).getBytes(StandardCharsets.UTF_8));
    }

    private static JsonArray position(long packed) {
        BlockPos p = BlockPos.of(packed); JsonArray result = new JsonArray();
        result.add(p.getX()); result.add(p.getY()); result.add(p.getZ()); return result;
    }

    private static void id(JsonObject record, String name, UUID value) {
        if (value == null) record.add(name, JsonNull.INSTANCE); else record.addProperty(name, value.toString());
    }

    private static JsonObject event(ServiceData d, ServerLevel level, String type,
                                    Villager citizen, UUID request, UUID job) {
        JsonObject r = new JsonObject(); r.addProperty("sequence", d.records.size() + 1);
        r.addProperty("type", type); r.addProperty("tick", level.getGameTime());
        id(r, "citizen", citizen == null ? null : citizen.getUUID()); id(r, "request", request); id(r, "job", job);
        r.addProperty("policy", POLICY); id(r, "session", d.session);
        if (citizen != null) {
            r.addProperty("x", citizen.getX()); r.addProperty("y", citizen.getY()); r.addProperty("z", citizen.getZ());
        }
        if (d.records.size() >= MAX_RECORDS) {
            d.capacityDenials++; d.enabled = false;
        } else d.records.add(r);
        d.setDirty(); return r;
    }

    private static void evidence(JsonObject r, Knowledge k) {
        r.addProperty("revision", k.need().revision()); id(r, "observer", k.need().observer());
        r.addProperty("observed_tick", k.need().observedTick()); r.addProperty("expires_tick", k.need().expiresTick());
        r.addProperty("origin", k.direct() ? "DIRECT" : "REPORT"); id(r, "selected_packet", k.packetId());
    }

    private static void admit(ServiceData d, UUID citizen, Need need) {
        d.admitted.computeIfAbsent(citizen, ignored -> new LinkedHashMap<>()).put(need.id(), need.revision());
    }

    private static List<Knowledge> own(ServiceData d, UUID citizen, long now) {
        Map<UUID, Long> admitted = d.admitted.get(citizen);
        if (admitted == null) return List.of();
        return d.kernel.known(citizen, now).stream()
            .filter(k -> admitted.getOrDefault(k.need().id(), -1L) == k.need().revision()).toList();
    }

    private static Knowledge ownNeed(ServiceData d, Villager citizen, UUID request, long now) {
        return own(d, citizen.getUUID(), now).stream().filter(k -> k.need().id().equals(request)).findFirst().orElse(null);
    }

    private static void stopMotion(Villager citizen) {
        citizen.getNavigation().stop(); citizen.setNoAi(true);
    }

    private static void hold(ServiceData d, ServerLevel level, Villager citizen, String reason) {
        CompoundTag m = memory(citizen);
        Commitment active = d.kernel == null ? null : d.kernel.active(citizen.getUUID());
        if (active != null && active.state() != State.HELD) d.kernel.hold(active.id(), reason, level.getGameTime());
        if (!"HELD".equals(m.getString("state")) || !reason.equals(m.getString("reason"))) {
            JsonObject r = event(d, level, "OPTION_HELD", citizen, active == null ? null : active.needId(), active == null ? null : active.job());
            r.addProperty("reason", reason); id(r, "commitment", active == null ? null : active.id());
        }
        m.putString("state", "HELD"); m.putString("reason", reason); saveMemory(citizen, m); stopMotion(citizen);
    }

    private static void idle(Villager citizen, long until) {
        CompoundTag m = memory(citizen); m.putString("option", "WAIT"); m.putString("state", "IDLE");
        m.putLong("until", until); m.remove("request"); m.remove("commitment"); m.remove("job");
        m.remove("reason"); m.remove("optionId"); m.remove(ServiceProductionBridge.PHASE); m.remove(ServiceProductionBridge.CARGO);
        saveMemory(citizen, m); stopMotion(citizen);
    }

    private static void park(Villager citizen) {
        CompoundTag m = memory(citizen);
        m.putString("option", "WAIT"); m.putString("state", "STOPPED");
        m.remove("request"); m.remove("commitment"); m.remove("job"); m.remove("reason");
        saveMemory(citizen, m); stopMotion(citizen);
    }

    private static void startOption(ServiceData d, ServerLevel level, Villager citizen,
                                    String option, Knowledge selected, long goal, Candidate candidate) {
        CompoundTag m = memory(citizen); m.putString("option", option); m.putString("state", "ACTIVE");
        m.putUUID("optionId", UUID.randomUUID()); m.putLong("started", level.getGameTime());
        m.putLong("goal", goal); m.remove("reason");
        m.putDouble("lastX", citizen.getX()); m.putDouble("lastY", citizen.getY()); m.putDouble("lastZ", citizen.getZ());
        m.putDouble("travelDistance", 0); m.putInt("sentCount", 0);
        learner(d, citizen.getUUID()).begin(m.getUUID("optionId"), candidate, level.getGameTime());
        if (selected != null) m.putUUID("request", selected.need().id()); else m.remove("request");
        saveMemory(citizen, m);
        JsonObject r = event(d, level, "OPTION_STARTED", citizen, selected == null ? null : selected.need().id(), null);
        r.addProperty("option", option); id(r, "option_id", m.getUUID("optionId")); r.add("goal", position(goal));
        if (selected != null) evidence(r, selected);
    }

    private static void observeLocal(ServiceData d, ServerLevel level, Villager citizen) {
        long now = level.getGameTime();
        for (long source : d.sources) {
            BlockPos pos = BlockPos.of(source);
            var observed = SourceWheatObservation.inspect(level, pos, citizen);
            if (observed.state() != SourceWheatObservation.State.UNKNOWN)
                CitizenSourceKnowledge.remember(level, pos, citizen, observed);
        }
        for (Buffer buffer : d.buffers.values()) {
            if (buffer.target == 0) continue; // An operator withdrawal is not a stock observation.
            int stock;
            if (buffer.production()) {
                var observed = ServiceProductionBridge.inspectFlour(level, BlockPos.of(buffer.position), citizen);
                if (!observed.known()) continue; stock = observed.units();
            } else {
                var observed = SourceWheatObservation.inspect(level, BlockPos.of(buffer.position), citizen);
                if (observed.state() == SourceWheatObservation.State.UNKNOWN) continue; stock = observed.wheat();
            }
            int units = Math.max(0, buffer.target - stock);
            UUID request = needId(d, buffer.position);
            Knowledge previous = ownNeed(d, citizen, request, now);
            if (previous != null && previous.direct() && previous.need().units() == units
                    && now - previous.need().observedTick() < 100) continue;
            Need need = new Need(request, d.kernel.scope(), buffer.position, buffer.item(), units,
                ++buffer.revision, citizen.getUUID(), now, now + NEED_TTL);
            if (d.kernel.observe(need, now)) {
                admit(d, citizen.getUUID(), need);
                JsonObject r = event(d, level, "NEED_OBSERVED", citizen, request, null);
                r.addProperty("revision", need.revision()); id(r, "observer", citizen.getUUID());
                r.addProperty("observed_tick", now); r.addProperty("expires_tick", need.expiresTick());
                r.addProperty("units", units); r.addProperty("stock", stock); r.addProperty("item", buffer.item());
                r.addProperty("target", buffer.target); r.add("site", position(buffer.position));
            } else d.capacityDenials++;
            d.setDirty();
        }
    }

    private static List<Long> localSources(ServiceData d, ServerLevel level, Villager citizen) {
        long now = level.getGameTime(); List<Long> result = new ArrayList<>();
        for (long source : d.sources) {
            CompoundTag e = CitizenSourceKnowledge.directEvidence(level, BlockPos.of(source), citizen);
            if (e != null && "AVAILABLE".equals(e.getString("state")) && e.getInt("wheat") > 0
                    && now >= e.getLong("observed_tick") && now - e.getLong("observed_tick") <= CitizenSourceKnowledge.FRESH_TICKS
                    && SourceReportSession.accepts(level, e, now)) result.add(source);
        }
        result.sort(Comparator.comparingDouble(pos -> distance(citizen, pos))); return result;
    }

    private static double distance(Villager citizen, long pos) {
        BlockPos p = BlockPos.of(pos); return citizen.distanceToSqr(p.getX() + .5, p.getY() + .5, p.getZ() + .5);
    }

    private static void move(Villager citizen, long pos) {
        BlockPos p = BlockPos.of(pos); citizen.setNoAi(false);
        citizen.getNavigation().moveTo(p.getX() + .5, p.getY(), p.getZ() + .5, .85);
    }

    private static boolean sent(CompoundTag memory, UUID recipient, Need need) {
        ListTag entries = memory.getList("sent", Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag e = entries.getCompound(i);
            if (e.hasUUID("recipient") && e.hasUUID("request") && e.getUUID("recipient").equals(recipient)
                    && e.getUUID("request").equals(need.id()) && e.getLong("revision") == need.revision()) return true;
        }
        return false;
    }

    private static boolean carryRequest(ServiceData d, ServerLevel level, Villager citizen, Knowledge selected) {
        // Encounters come from a local spatial query; no remote actor location is
        // read for planning. The route is to configured public source geometry.
        List<Villager> peers = level.getEntitiesOfClass(Villager.class, citizen.getBoundingBox().inflate(12),
            peer -> !peer.getUUID().equals(citizen.getUUID()) && d.enrolled.contains(peer.getUUID())
                && controls(peer) && citizen.distanceToSqr(peer) <= 144);
        peers.sort(Comparator.comparing(v -> v.getUUID().toString()));
        boolean handedOff = false;
        for (Villager peer : peers) {
            if (d.records.size() > MAX_RECORDS - 2) {
                d.capacityDenials++; d.enabled = false; d.setDirty(); break;
            }
            CompoundTag m = memory(citizen);
            if (sent(m, peer.getUUID(), selected.need())) continue;
            var packet = d.kernel.packet(citizen.getUUID(), peer.getUUID(), selected.need().id(), level.getGameTime());
            if (packet == null) { d.capacityDenials++; continue; }
            ListTag sent = m.getList("sent", Tag.TAG_COMPOUND);
            while (sent.size() >= 128) sent.remove(0);
            CompoundTag s = new CompoundTag(); s.putUUID("recipient", peer.getUUID()); s.putUUID("request", selected.need().id());
            s.putLong("revision", selected.need().revision()); s.putUUID("packet", packet.id()); sent.add(s);
            m.put("sent", sent); m.putInt("sentCount", m.getInt("sentCount") + 1); saveMemory(citizen, m);
            JsonObject send = event(d, level, "REQUEST_SENT", citizen, packet.need().id(), null);
            packetEvidence(send, packet); send.addProperty("distance", Math.sqrt(citizen.distanceToSqr(peer)));
            boolean accepted = d.kernel.receive(packet, level.getGameTime());
            JsonObject received = event(d, level, accepted ? "REQUEST_RECEIVED" : "REQUEST_REJECTED", peer, packet.need().id(), null);
            packetEvidence(received, packet);
            if (accepted) {
                admit(d, peer.getUUID(), packet.need()); handedOff = true;
                // Wake only the recipient's idle option; this does not select a
                // job or let the sender inspect the recipient's private beliefs.
                CompoundTag pm = memory(peer);
                if ("IDLE".equals(pm.getString("state"))) { pm.putLong("until", level.getGameTime()); saveMemory(peer, pm); }
            } else received.addProperty("reason", "DUPLICATE_STALE_OR_SUPERSEDED");
        }
        return handedOff;
    }

    private static void packetEvidence(JsonObject r, NeedServiceKernel.Packet p) {
        id(r, "packet", p.id()); id(r, "sender", p.sender()); id(r, "recipient", p.recipient());
        id(r, "observer", p.need().observer()); id(r, "parent", p.parent());
        r.addProperty("revision", p.need().revision()); r.addProperty("observed_tick", p.need().observedTick());
        r.addProperty("expires_tick", p.need().expiresTick()); r.addProperty("hops", p.hops()); r.addProperty("units", p.need().units());
    }

    private static boolean assign(ServiceData d, ServerLevel level, Villager citizen, Knowledge selected, long source, Candidate candidate) {
        long now = level.getGameTime();
        // This ownership lookup is executor conflict arbitration on an already
        // privately observed candidate, not discovery of a hidden source.
        UUID owner = HaulClaims.owner(level, BlockPos.of(source));
        if (owner != null) return false;
        Commitment commitment = d.kernel.reserve(citizen.getUUID(), selected.need().id(), selected.need().revision(), now, now + LEASE_TICKS);
        if (commitment == null) {
            JsonObject denied = event(d, level, "ARBITRATION_REFUSED", citizen, selected.need().id(), null);
            evidence(denied, selected); denied.addProperty("reason", "NO_EXECUTABLE_PRIVATE_REQUEST_CAPACITY");
            idle(citizen, now + 100); return true;
        }
        startOption(d, level, citizen, "SUPPLY_WHEAT", selected, selected.need().site(), candidate);
        CompoundTag m = memory(citizen); m.putUUID("commitment", commitment.id()); m.putLong("source", source);
        m.putLong("revision", selected.need().revision()); m.putString("origin", selected.direct() ? "DIRECT" : "REPORT");
        if (selected.packetId() != null) m.putUUID("selectedPacket", selected.packetId()); else m.remove("selectedPacket");
        saveMemory(citizen, m);
        JsonObject claimed = event(d, level, "SUPPLY_CLAIMED", citizen, selected.need().id(), null);
        id(claimed, "commitment", commitment.id()); evidence(claimed, selected);
        try {
            Buffer buffer = d.buffers.get(selected.need().site());
            long physicalDestination = buffer.production() ? buffer.machine : selected.need().site();
            SableHauling.assign(level, citizen, BlockPos.of(source), BlockPos.of(physicalDestination));
            CompoundTag motor = citizen.getPersistentData().getCompound(HAUL);
            if (!motor.hasUUID("jobId")) throw new IllegalStateException("Native motor omitted job identity");
            UUID job = motor.getUUID("jobId");
            d.kernel.begin(commitment.id(), citizen.getUUID(), job, now);
            learner(d, citizen.getUUID()).bind(m.getUUID("optionId"), commitment.id(), job, now);
            m = memory(citizen); m.putUUID("job", job); saveMemory(citizen, m); citizen.setNoAi(false);
            d.assigned++;
            JsonObject r = event(d, level, "MOTOR_ASSIGNED", citizen, selected.need().id(), job);
            id(r, "commitment", commitment.id()); evidence(r, selected);
            r.add("source", position(source)); r.add("destination", position(physicalDestination));
            if (buffer.production()) r.add("output_destination", position(buffer.position));
            r.addProperty("assigned_tick", motor.getLong("assignedTick"));
            return true;
        } catch (RuntimeException failure) {
            // A partially assigned or foreign motor is uncertain, not an
            // excuse to free its lease or manufacture an outcome.
            if (SableHauling.active(citizen)) hold(d, level, citizen, "ASSIGNMENT_UNCERTAIN: " + failure.getMessage());
            else {
                d.kernel.cancelBeforePickup(commitment.id(), citizen.getUUID(), null, now); d.cancelled++;
                learner(d, citizen.getUUID()).bind(m.getUUID("optionId"), commitment.id(), null, now);
                JsonObject r = event(d, level, "OPTION_CANCELLED", citizen, selected.need().id(), null);
                r.addProperty("reason", "NATIVE_ASSIGNMENT_REFUSED"); id(r, "commitment", commitment.id());
                settleService(d, level, citizen, Outcome.VERIFIED_FAILURE_NO_CARGO); idle(citizen, now + 100);
            }
            d.setDirty(); return true;
        }
    }

    private static boolean motor(ServiceData d, ServerLevel level, Villager citizen, Commitment c) {
        CompoundTag m = memory(citizen), nativeTag = citizen.getPersistentData().getCompound(HAUL);
        if (!m.hasUUID("commitment") || !m.getUUID("commitment").equals(c.id())
                || c.job() == null || !m.hasUUID("job") || !m.getUUID("job").equals(c.job())
                || !nativeTag.hasUUID("jobId") || !nativeTag.getUUID("jobId").equals(c.job())) {
            hold(d, level, citizen, "OWNERSHIP_OR_JOB_MISMATCH"); return true;
        }
        if (c.state() == State.HELD) { hold(d, level, citizen, c.reason()); return true; }
        if (c.state() == State.PROCESSING) return production(d, level, citizen, c);
        if (SableHauling.cancelledBeforePickup(citizen, c.job())) {
            d.kernel.cancelBeforePickup(c.id(), citizen.getUUID(), c.job(), level.getGameTime()); d.cancelled++;
            JsonObject r = event(d, level, "OPTION_CANCELLED", citizen, c.needId(), c.job());
            id(r, "commitment", c.id()); r.addProperty("reason", "NATIVE_OPERATOR_CANCELLATION_CONFIRMED");
            settleService(d, level, citizen, Outcome.VERIFIED_NO_CARGO_CANCEL); idle(citizen, level.getGameTime() + 40); return true;
        }
        Buffer buffer = d.buffers.get(m.getLong("goal"));
        boolean withdrawn = buffer == null || buffer.target == 0;
        boolean cancel = withdrawn || d.kernel.shouldCancel(c.id(), level.getGameTime());
        if (cancel && !nativeTag.contains("cargo")) {
            if (SableHauling.cancelledBeforePickup(citizen, c.job()) || SableHauling.cancelBeforePickup(level, citizen)) {
                d.kernel.cancelBeforePickup(c.id(), citizen.getUUID(), c.job(), level.getGameTime()); d.cancelled++;
                JsonObject r = event(d, level, "OPTION_CANCELLED", citizen, c.needId(), c.job());
                id(r, "commitment", c.id()); r.addProperty("reason", withdrawn ? "OPERATOR_CONFIGURATION_GOAL_WITHDRAWN" : "EXECUTION_GATE_CLOSED_OR_EXPIRED");
                settleService(d, level, citizen, Outcome.VERIFIED_NO_CARGO_CANCEL); idle(citizen, level.getGameTime() + 40); d.setDirty(); return true;
            }
            hold(d, level, citizen, "CANCELLATION_NOT_PROVEN_SAFE"); return true;
        }
        if (nativeTag.contains("cargo") && c.state() == State.RUNNING) {
            d.kernel.pickedUp(c.id(), c.job(), level.getGameTime());
            if (cancel) d.kernel.expire(level.getGameTime());
        }
        int phase = nativeTag.getInt("phase");
        if (phase == 3 || phase == 4 || phase == 5) { hold(d, level, citizen, "NATIVE_MOTOR_PAUSED_OR_UNCERTAIN"); return true; }
        citizen.setNoAi(false);
        SableHauling.tick(level, citizen);
        // Reconcile at the physical boundary, before any later sensing or idle
        // tick. Only the exact native complete assignment can settle this lease.
        BlockPos destination = BlockPos.of(nativeTag.getLong("destination"));
        if (SableHauling.completedJob(citizen, c.job(), destination)) {
            var verified = SableHauling.completedAssignment(level, citizen, c.job(), destination);
            long expectedDestination = buffer != null && buffer.production() ? buffer.machine : m.getLong("goal");
            if (verified.source() != m.getLong("source") || verified.destination() != expectedDestination) {
                hold(d, level, citizen, "COMPLETED_ENDPOINT_MISMATCH"); return true;
            }
            long delivered = citizen.getPersistentData().getCompound(HAUL).getLong("physicalDeliveredTick");
            UUID receipt = UUID.nameUUIDFromBytes((d.kernel.scope().world() + "|service-transfer|" + c.id() + "|" + c.job()).getBytes(StandardCharsets.UTF_8));
            if (buffer != null && buffer.production()) {
                d.kernel.beginProcessing(c.id(), c.job(), level.getGameTime());
                ServiceProductionBridge.begin(m, destination); saveMemory(citizen, m); d.transfers++;
                JsonObject r = event(d, level, "TRANSFER_VERIFIED", citizen, c.needId(), c.job());
                id(r, "commitment", c.id()); id(r, "receipt", receipt); r.addProperty("units", 1);
                r.add("source", position(verified.source())); r.add("destination", position(verified.destination()));
                r.addProperty("assigned_tick", verified.assignedTick()); r.addProperty("delivered_tick", delivered);
                r.addProperty("production_credit", false); r.addProperty("purpose", "MILL_INPUT");
                JsonObject begun = event(d, level, "PRODUCTION_STARTED", citizen, c.needId(), c.job());
                id(begun, "commitment", c.id()); begun.add("machine", position(destination.asLong()));
                begun.addProperty("input_delivered_tick", delivered); begun.addProperty("processing_start_tick", -1);
                d.setDirty(); stopMotion(citizen); return true;
            }
            if (d.kernel.delivered(new NeedServiceKernel.TransferReceipt(receipt, d.kernel.scope(), c.id(), citizen.getUUID(), c.job(), destination.asLong(), delivered, 1))) {
                d.transfers++;
                JsonObject r = event(d, level, "TRANSFER_VERIFIED", citizen, c.needId(), c.job());
                id(r, "commitment", c.id()); id(r, "receipt", receipt); r.addProperty("units", 1);
                r.add("source", position(verified.source())); r.add("destination", position(verified.destination()));
                r.addProperty("assigned_tick", verified.assignedTick()); r.addProperty("delivered_tick", delivered);
                r.addProperty("production_credit", false);
            }
            settleService(d, level, citizen, Outcome.VERIFIED_TRANSFER); idle(citizen, level.getGameTime() + 20); d.setDirty();
        } else if (citizen.getPersistentData().getCompound(HAUL).contains("cargo") && c.state() == State.RUNNING) {
            d.kernel.pickedUp(c.id(), c.job(), level.getGameTime()); d.setDirty();
        }
        return true;
    }

    private static UUID serviceReceipt(ServiceData d, UUID option) {
        return UUID.nameUUIDFromBytes((d.kernel.scope().world() + "|service-outcome|" + option).getBytes(StandardCharsets.UTF_8));
    }

    private static double personalCost(CompoundTag memory) {
        // Transparent authored cost units: sampled physical travel and packets sent.
        // Duration remains a separate learned head, not a second movement charge.
        return Math.min(1000., memory.getDouble("travelDistance") * .01 + memory.getInt("sentCount") * .02);
    }

    private static void trackTravel(Villager citizen) {
        CompoundTag m = memory(citizen);
        if (!"ACTIVE".equals(m.getString("state")) || !m.hasUUID("optionId")) return;
        double dx = citizen.getX() - m.getDouble("lastX"), dy = citizen.getY() - m.getDouble("lastY"), dz = citizen.getZ() - m.getDouble("lastZ");
        m.putDouble("travelDistance", m.getDouble("travelDistance") + Math.sqrt(dx * dx + dy * dy + dz * dz));
        m.putDouble("lastX", citizen.getX()); m.putDouble("lastY", citizen.getY()); m.putDouble("lastZ", citizen.getZ());
        saveMemory(citizen, m);
    }

    private static void settleService(ServiceData d, ServerLevel level, Villager citizen, Outcome outcome) {
        CompoundTag m = memory(citizen);
        if (!m.hasUUID("optionId")) throw new IllegalStateException("Service has no captured decision");
        CitizenServiceLearning learning = learner(d, citizen.getUUID());
        var decision = learning.decision(m.getUUID("optionId"));
        if (decision == null) throw new IllegalStateException("Service decision was not persisted");
        if (learning.settle(decision.optionId(), serviceReceipt(d, decision.optionId()), level.getGameTime(), personalCost(m), outcome)) {
            JsonObject r = event(d, level, "SERVICE_SETTLED", citizen, decision.candidate().needId(), decision.job());
            id(r, "option_id", decision.optionId()); id(r, "commitment", decision.commitment());
            r.addProperty("outcome", outcome.name()); r.addProperty("started_tick", decision.startedTick());
            r.addProperty("duration_ticks", level.getGameTime() - decision.startedTick());
            r.addProperty("personal_cost", personalCost(m)); r.addProperty("travel_distance", m.getDouble("travelDistance"));
            r.addProperty("sent_count", m.getInt("sentCount")); r.add("features", GSON.toJsonTree(decision.candidate().features().values()));
            r.addProperty("service_samples", learning.status().serviceSamples());
        }
        d.setDirty();
    }

    private static ProductionReceipt productionReceipt(ServiceData d, Villager citizen, Commitment c,
                                                        ServiceProductionBridge.Proof proof, long tick) {
        UUID receipt = UUID.nameUUIDFromBytes((proof.physicalEvidence() + "|final-output").getBytes(StandardCharsets.UTF_8));
        return new ProductionReceipt(receipt, d.kernel.scope(), proof.physicalEvidence(), c.id(), citizen.getUUID(), c.job(), tick, proof.units());
    }

    private static boolean production(ServiceData d, ServerLevel level, Villager citizen, Commitment c) {
        CompoundTag m = memory(citizen); long now = level.getGameTime();
        String phase = m.getString(ServiceProductionBridge.PHASE);
        if ("AWAIT_PROCESS".equals(phase)) {
            if (MillReservations.isTainted(level, c.job())) { hold(d, level, citizen, "PRODUCTION_INPUT_OR_PROCESS_TAINTED"); return true; }
            if (now - m.getLong("started") > 2400) { hold(d, level, citizen, "PRODUCTION_PROCESS_TIMEOUT_WITH_CUSTODY"); return true; }
            if (distance(citizen, m.getLong("machine")) > 6.25) { move(citizen, m.getLong("machine")); return true; }
            stopMotion(citizen);
            if (!ServiceProductionBridge.callbackPresent(level, m)) return true;
            var proof = ServiceProductionBridge.collect(level, citizen, m, d.kernel.scope()); saveMemory(citizen, m);
            JsonObject r = event(d, level, "PRODUCTION_OUTPUT_COLLECTED", citizen, c.needId(), c.job());
            id(r, "commitment", c.id()); r.addProperty("units", proof.units()); r.add("machine", position(proof.machine()));
            r.addProperty("processing_start_tick", proof.startTick()); r.addProperty("process_tick", proof.processTick());
            var callback = MillProcessReceipts.observedCallback(level, c.job());
            r.addProperty("wheat_before", callback.wheatBefore()); r.addProperty("wheat_after", callback.wheatAfter());
            r.addProperty("flour_before", callback.flourBefore()); r.addProperty("flour_after", callback.flourAfter());
            r.add("items", GSON.toJsonTree(ServiceProductionBridge.outputItems(m)));
            r.addProperty("physical_evidence", proof.physicalEvidence());
            move(citizen, m.getLong("goal")); return true;
        }
        if ("TO_OUTPUT".equals(phase)) {
            if (now - m.getLong("outputPickedTick") > 2400) { hold(d, level, citizen, "OUTPUT_DELIVERY_TIMEOUT_WITH_CARGO"); return true; }
            if (distance(citizen, m.getLong("goal")) > 6.25) { move(citizen, m.getLong("goal")); return true; }
            CitizenServiceLearning learning = learner(d, citizen.getUUID());
            var proof = ServiceProductionBridge.verify(level, citizen, m, d.kernel.scope());
            ProductionReceipt productionReceipt = productionReceipt(d, citizen, c, proof, now);
            learning.validateSettlement(m.getUUID("optionId"), serviceReceipt(d, m.getUUID("optionId")), now,
                personalCost(m), Outcome.VERIFIED_TRANSFER, productionReceipt);
            UUID outputTransfer = UUID.nameUUIDFromBytes((proof.physicalEvidence() + "|buffer-delivery").getBytes(StandardCharsets.UTF_8));
            var transferReceipt = new NeedServiceKernel.TransferReceipt(outputTransfer, d.kernel.scope(), c.id(), citizen.getUUID(),
                c.job(), m.getLong("goal"), now, proof.units());
            d.kernel.validateDelivery(transferReceipt);
            var delivery = ServiceProductionBridge.deliver(level, citizen, m, d.kernel.scope()); saveMemory(citizen, m);
            if (delivery == null) { hold(d, level, citizen, "OUTPUT_BUFFER_FULL_CARGO_RETAINED"); return true; }
            JsonObject r = event(d, level, "PRODUCTION_OUTPUT_DELIVERED", citizen, c.needId(), c.job());
            id(r, "commitment", c.id()); r.addProperty("units", delivery.units());
            r.addProperty("stock_before", delivery.before()); r.addProperty("stock_after", delivery.after());
            r.add("destination", position(m.getLong("goal"))); r.add("items", GSON.toJsonTree(delivery.items()));
            r.add("items_before", GSON.toJsonTree(delivery.beforeItems())); r.add("items_after", GSON.toJsonTree(delivery.afterItems()));
            // Revalidate physical ownership and taint before sealing the output
            // receipt, and retire the old callback trace before the mill is reused.
            ServiceProductionBridge.release(level, citizen, m, d.kernel.scope()); saveMemory(citizen, m);
            d.kernel.delivered(transferReceipt);
            settleService(d, level, citizen, Outcome.VERIFIED_TRANSFER);
            if (!learning.recordProduction(productionReceipt)) throw new IllegalStateException("Production settlement unexpectedly replayed");
            d.productionJobs++; d.outputUnits += proof.units();
            JsonObject finalEvent = event(d, level, "PRODUCTION_SETTLED", citizen, c.needId(), c.job());
            id(finalEvent, "commitment", c.id()); id(finalEvent, "receipt", productionReceipt.id());
            id(finalEvent, "selected_packet", m.hasUUID("selectedPacket") ? m.getUUID("selectedPacket") : null);
            finalEvent.addProperty("units", proof.units()); finalEvent.addProperty("physical_evidence", proof.physicalEvidence());
            finalEvent.addProperty("production_samples", learning.status().productionSamples());
            finalEvent.addProperty("service_samples", learning.status().serviceSamples()); finalEvent.addProperty("reservation_released", true);
            finalEvent.addProperty("trace_retired", true);
            finalEvent.add("items", GSON.toJsonTree(delivery.items()));
            idle(citizen, now + 20); d.setDirty(); return true;
        }
        hold(d, level, citizen, "OUTPUT_TRANSACTION_INTERRUPTED_OR_UNKNOWN: " + phase); return true;
    }

    private record Offer(Candidate candidate, Knowledge knowledge, Long source, long goal) {}

    private static Candidate candidate(ServiceData d, Villager citizen, String id, Kind kind, Knowledge knowledge,
                                       double blocks, double prior) {
        UUID partner = knowledge == null || knowledge.direct() ? null : knowledge.from();
        return new Candidate(id, citizen.getUUID(), knowledge == null ? null : knowledge.need().id(), partner, kind,
            ServiceValueLearner.features(kind, knowledge == null ? 0 : knowledge.need().units(), blocks,
                knowledge == null ? 0 : Math.max(0, citizen.level().getGameTime() - knowledge.need().observedTick()),
                0, learner(d, citizen.getUUID()).partnerSuccess(partner)), prior);
    }

    private static void choose(ServiceData d, ServerLevel level, Villager citizen, long now) {
        List<Offer> offers = new ArrayList<>(); List<Long> sources = localSources(d, level, citizen);
        List<Knowledge> needs = own(d, citizen.getUUID(), now).stream()
            .filter(k -> k.need().units() > 0 && d.buffers.containsKey(k.need().site()) && d.buffers.get(k.need().site()).target > 0).toList();
        for (Knowledge known : needs) {
            Buffer buffer = d.buffers.get(known.need().site());
            for (long source : sources) {
                long destination = buffer.production() ? buffer.machine : buffer.position;
                double blocks = Math.sqrt(distance(citizen, source)) + Math.sqrt(BlockPos.of(source).distSqr(BlockPos.of(destination)));
                if (buffer.production()) blocks += Math.sqrt(BlockPos.of(destination).distSqr(BlockPos.of(buffer.position)));
                Candidate c = candidate(d, citizen, "supply:" + known.need().id() + ":" + source, Kind.SUPPLY_WHEAT, known, blocks, 3.);
                offers.add(new Offer(c, known, source, buffer.position));
            }
            if (sources.isEmpty()) {
                Long rendezvous = d.sources.stream().min(Comparator.comparingDouble(pos -> distance(citizen, pos))).orElse(null);
                if (rendezvous != null) {
                    Candidate c = candidate(d, citizen, "carry:" + known.need().id(), Kind.CARRY_REQUEST, known,
                        Math.sqrt(distance(citizen, rendezvous)), 1.);
                    offers.add(new Offer(c, known, null, rendezvous));
                }
            }
        }
        double sourceDistance = d.sources.stream().mapToDouble(pos -> distance(citizen, pos)).min().orElse(Double.POSITIVE_INFINITY);
        for (Buffer b : d.buffers.values()) if (b.target > 0 && distance(citizen, b.position) < sourceDistance
                && ownNeed(d, citizen, needId(d, b.position), now) == null) {
            Candidate c = candidate(d, citizen, "observe:" + b.position, Kind.OBSERVE_BUFFER, null, Math.sqrt(distance(citizen, b.position)), .6);
            offers.add(new Offer(c, null, null, b.position));
        }
        Candidate wait = candidate(d, citizen, "wait", Kind.WAIT, null, 0, 0);
        offers.add(new Offer(wait, null, null, citizen.blockPosition().asLong()));
        CitizenServiceLearning learning = learner(d, citizen.getUUID());
        Candidate selected = learning.choose(offers.stream().map(Offer::candidate).toList());
        JsonObject record = event(d, level, "POLICY_DECISION", citizen, selected.needId(), null);
        record.addProperty("selected", selected.id()); record.addProperty("selected_kind", selected.kind().name());
        JsonArray scores = new JsonArray();
        for (Offer offer : offers) {
            var score = learning.score(offer.candidate()); JsonObject e = new JsonObject();
            e.addProperty("id", offer.candidate().id()); e.addProperty("kind", offer.candidate().kind().name());
            e.addProperty("total", score.total()); e.addProperty("authored_prior", score.authoredPrior());
            e.addProperty("production_estimate", score.learnedProductionUnits()); e.addProperty("duration_estimate", score.estimatedDurationTicks());
            e.addProperty("personal_cost", score.estimatedPersonalCost()); e.addProperty("success_estimate", score.estimatedSuccess());
            e.addProperty("service_samples", score.serviceSamples()); e.addProperty("production_samples", score.productionSamples());
            e.add("features", GSON.toJsonTree(offer.candidate().features().values())); scores.add(e);
        }
        record.add("scores", scores);
        Offer chosen = offers.stream().filter(o -> o.candidate().id().equals(selected.id())).findFirst().orElseThrow();
        if (selected.kind() == Kind.SUPPLY_WHEAT) {
            if (!assign(d, level, citizen, chosen.knowledge(), chosen.source(), selected)) idle(citizen, now + 40);
        } else {
            startOption(d, level, citizen, selected.kind().name(), chosen.knowledge(), chosen.goal(), selected);
            if (selected.kind() == Kind.WAIT) {
                CompoundTag m = memory(citizen); m.putLong("until", now + 40); saveMemory(citizen, m); stopMotion(citizen);
            } else move(citizen, chosen.goal());
        }
    }

    /** Called before every legacy owner; all world access remains on the server thread. */
    static boolean tick(ServerLevel level, Villager citizen) {
        if (!controls(citizen)) return false;
        ServiceData d = data(level); CompoundTag m = memory(citizen);
        if (!d.failure.isEmpty()) { stopMotion(citizen); return true; }
        if (!d.enrolled.contains(citizen.getUUID()) || !m.hasUUID("world") || !m.getUUID("world").equals(d.kernel.scope().world())
                || !d.kernel.scope().dimension().equals(m.getString("dimension"))) {
            hold(d, level, citizen, "OWNER_SCOPE_MISMATCH"); return true;
        }
        if (m.contains(ServiceProductionBridge.PHASE) && !"FINALIZED".equals(m.getString(ServiceProductionBridge.PHASE))
                && d.kernel.active(citizen.getUUID()) == null) {
            hold(d, level, citizen, "ORPHANED_OUTPUT_CUSTODY_OR_SAVED_STATE_DISAGREEMENT"); return true;
        }
        MillExperimentTrace.monitorAuthorizedInput(level, citizen);
        MillExperimentTrace.sampleCycle(level, citizen);
        if (!d.session.equals(SourceReportSession.episode(level))) {
            d.enabled = false; d.admitted.clear();
            hold(d, level, citizen, "CURRENT_SESSION_FENCE_CHANGED"); return true;
        }
        if (!d.enabled || !m.hasUUID("session") || !m.getUUID("session").equals(d.session)) {
            Commitment unresolved = d.kernel.active(citizen.getUUID());
            if (unresolved != null || SableHauling.active(citizen) || learner(d, citizen.getUUID()).active() != null) {
                if (unresolved == null || unresolved.state() != State.HELD)
                    hold(d, level, citizen, d.enabled ? "SESSION_REVALIDATION_REQUIRED" : "DISPATCH_DISABLED_OR_SESSION_LOST");
                else if (!"HELD".equals(m.getString("state"))) hold(d, level, citizen, unresolved.reason());
                else stopMotion(citizen);
            } else park(citizen);
            return true;
        }
        if (CivilizationRuntime.enabled(level) || citizen.getPersistentData().contains("hearthbound.private_communication_trial.v1")) {
            hold(d, level, citizen, "COMPETING_CONTROLLER_ENABLED"); return true;
        }
        if (citizen.tickCount % 20 != 0) return true;
        try {
            trackTravel(citizen);
            if ("HELD".equals(m.getString("state"))) { stopMotion(citizen); return true; }
            Commitment active = d.kernel.active(citizen.getUUID());
            if (active != null) return motor(d, level, citizen, active);
            if (SableHauling.active(citizen)) { hold(d, level, citizen, "FOREIGN_NATIVE_MOTOR"); return true; }
            if (d.records.size() >= MAX_RECORDS - 16) { d.capacityDenials++; d.enabled = false; hold(d, level, citizen, "RECORD_CAPACITY_EXHAUSTED"); return true; }
            observeLocal(d, level, citizen);
            m = memory(citizen); long now = level.getGameTime();
            if ("ACTIVE".equals(m.getString("state")) && "WAIT".equals(m.getString("option"))) {
                if (now < m.getLong("until")) return true;
                settleService(d, level, citizen, Outcome.VERIFIED_WAIT); idle(citizen, now);
            }
            if ("CARRY_REQUEST".equals(m.getString("option"))) {
                Knowledge selected = m.hasUUID("request") ? ownNeed(d, citizen, m.getUUID("request"), now) : null;
                Buffer buffer = selected == null ? null : d.buffers.get(selected.need().site());
                if (selected == null || selected.need().units() == 0 || buffer == null || buffer.target == 0 || now - m.getLong("started") > NEED_TTL) {
                    JsonObject r = event(d, level, "OPTION_CANCELLED", citizen, m.hasUUID("request") ? m.getUUID("request") : null, null);
                    r.addProperty("reason", buffer != null && buffer.target == 0 ? "OPERATOR_CONFIGURATION_GOAL_WITHDRAWN" : "OWN_REQUEST_CLOSED_OR_EXPIRED");
                    d.cancelled++; settleService(d, level, citizen, Outcome.VERIFIED_NO_CARGO_CANCEL); idle(citizen, now + 40); return true;
                }
                if (carryRequest(d, level, citizen, selected)) {
                    event(d, level, "REQUEST_CARRY_FINISHED", citizen, selected.need().id(), null);
                    settleService(d, level, citizen, Outcome.VERIFIED_REQUEST_DELIVERY); idle(citizen, now + 40); return true;
                }
                if (distance(citizen, m.getLong("goal")) > 6.25) move(citizen, m.getLong("goal")); else stopMotion(citizen);
                return true;
            }
            if ("OBSERVE_BUFFER".equals(m.getString("option"))) {
                UUID request = needId(d, m.getLong("goal")); Knowledge observed = ownNeed(d, citizen, request, now);
                if (observed != null && observed.direct() && observed.need().observedTick() >= m.getLong("started")) {
                    settleService(d, level, citizen, Outcome.VERIFIED_OBSERVATION); idle(citizen, now);
                } else if (now - m.getLong("started") < NEED_TTL) { move(citizen, m.getLong("goal")); return true; }
                else { settleService(d, level, citizen, Outcome.VERIFIED_FAILURE_NO_CARGO); idle(citizen, now + 40); return true; }
            }
            if (now < memory(citizen).getLong("until")) return true;
            choose(d, level, citizen, now); return true;
        } catch (RuntimeException failure) {
            hold(d, level, citizen, "SERVICE_BOUNDARY_FAILURE: " + failure.getClass().getSimpleName() + ": " + failure.getMessage());
            return true;
        }
    }

    public static void register(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(Commands.literal("hearthbound-services").requires(source -> source.hasPermission(2))
            .then(Commands.literal("configure-buffer").then(Commands.argument("position", BlockPosArgument.blockPos())
                .then(Commands.argument("target", IntegerArgumentType.integer(1, 64)).executes(ctx -> configureBuffer(ctx.getSource(),
                    BlockPosArgument.getBlockPos(ctx, "position"), IntegerArgumentType.getInteger(ctx, "target"), false)))))
            .then(Commands.literal("configure-mill").then(Commands.argument("machine", BlockPosArgument.blockPos())
                .then(Commands.argument("output", BlockPosArgument.blockPos())
                    .then(Commands.argument("target", IntegerArgumentType.integer(1, 64)).executes(ctx -> configureMill(ctx.getSource(),
                        BlockPosArgument.getBlockPos(ctx, "machine"), BlockPosArgument.getBlockPos(ctx, "output"), IntegerArgumentType.getInteger(ctx, "target")))))))
            .then(Commands.literal("set-target").then(Commands.argument("position", BlockPosArgument.blockPos())
                .then(Commands.argument("target", IntegerArgumentType.integer(0, 64)).executes(ctx -> configureBuffer(ctx.getSource(),
                    BlockPosArgument.getBlockPos(ctx, "position"), IntegerArgumentType.getInteger(ctx, "target"), true)))))
            .then(Commands.literal("configure-source").then(Commands.argument("position", BlockPosArgument.blockPos())
                .executes(ctx -> configureSource(ctx.getSource(), BlockPosArgument.getBlockPos(ctx, "position")))))
            .then(Commands.literal("enroll").then(Commands.argument("citizen", EntityArgument.entity()).executes(ctx -> {
                if (!(EntityArgument.getEntity(ctx, "citizen") instanceof Villager citizen)) return fail(ctx.getSource(), "A service citizen must be a marked villager");
                return enroll(ctx.getSource(), citizen);
            })))
            .then(Commands.literal("start").executes(ctx -> start(ctx.getSource())))
            .then(Commands.literal("stop").executes(ctx -> stop(ctx.getSource())))
            .then(Commands.literal("status").executes(ctx -> status(ctx.getSource())))
            .then(Commands.literal("records").then(Commands.argument("offset", IntegerArgumentType.integer(0))
                .executes(ctx -> records(ctx.getSource(), IntegerArgumentType.getInteger(ctx, "offset"))))));
    }

    private static int fail(CommandSourceStack source, String message) {
        source.sendFailure(Component.literal("NEED_SERVICES_DENIED " + message)); return 0;
    }

    private static int okay(CommandSourceStack source, String message) {
        source.sendSuccess(() -> Component.literal("NEED_SERVICES_OK " + message), false); return 1;
    }

    private static int configureBuffer(CommandSourceStack source, BlockPos pos, int target, boolean update) {
        ServiceData d = data(source.getLevel()); if (!d.failure.isEmpty()) return fail(source, d.failure);
        if (!update && d.enabled) return fail(source, "Stop before changing public site geometry");
        if (d.sources.contains(pos.asLong()) || d.buffers.values().stream().anyMatch(b -> b.production() && b.machine == pos.asLong()))
            return fail(source, "Source, mill and buffer must be different sites");
        Buffer b = d.buffers.get(pos.asLong());
        if (update && b == null) return fail(source, "Unknown configured buffer");
        if (b == null && d.buffers.size() >= MAX_SITES) { d.capacityDenials++; d.setDirty(); return fail(source, "Buffer capacity exhausted"); }
        if (b == null) d.buffers.put(pos.asLong(), new Buffer(pos.asLong(), target, 0)); else b.target = target;
        JsonObject r = event(d, source.getLevel(), "OPERATOR_CONFIGURATION", null, needId(d, pos.asLong()), null);
        r.addProperty("reason", target == 0 ? "GOAL_WITHDRAWN" : "BUFFER_TARGET_SET"); r.add("site", position(pos.asLong())); r.addProperty("target", target);
        return okay(source, "Public buffer target configured; inventory has not been observed");
    }

    private static int configureMill(CommandSourceStack source, BlockPos machine, BlockPos output, int target) {
        ServerLevel level = source.getLevel(); ServiceData d = data(level);
        if (!d.failure.isEmpty()) return fail(source, d.failure);
        if (d.enabled || d.kernel.commitments().stream().anyMatch(Commitment::active))
            return fail(source, "Stop and reconcile physical jobs before changing production geometry");
        if (machine.equals(output) || d.sources.contains(machine.asLong()) || d.sources.contains(output.asLong())
                || d.buffers.containsKey(machine.asLong())
                || d.buffers.values().stream().anyMatch(b -> b.production() && b.machine == output.asLong()))
            return fail(source, "Production sites and sources must be distinct");
        if (!MillReservations.isMill(level, machine)) return fail(source, "Requires a loaded Create millstone");
        if (!(level.getBlockEntity(output) instanceof net.minecraft.world.Container)) return fail(source, "Requires a loaded output container");
        for (Buffer existing : d.buffers.values()) if (existing.production() && existing.machine == machine.asLong()
                && existing.position != output.asLong()) return fail(source, "A mill belongs to one output buffer");
        Buffer existing = d.buffers.get(output.asLong());
        if (existing != null && (!existing.production() || existing.machine != machine.asLong()))
            return fail(source, "Cannot change an existing buffer's material or mill identity");
        if (existing == null && d.buffers.size() >= MAX_SITES) return fail(source, "Buffer capacity exhausted");
        if (existing == null) d.buffers.put(output.asLong(), new Buffer(output.asLong(), target, 0, machine.asLong()));
        else existing.target = target;
        JsonObject r = event(d, level, "OPERATOR_CONFIGURATION", null, needId(d, output.asLong()), null);
        r.addProperty("reason", "FLOUR_TARGET_SET"); r.add("site", position(output.asLong())); r.add("machine", position(machine.asLong()));
        r.addProperty("item", "create:wheat_flour"); r.addProperty("target", target);
        return okay(source, "Public production geometry configured; flour stock remains privately observed");
    }

    private static int configureSource(CommandSourceStack source, BlockPos pos) {
        ServiceData d = data(source.getLevel()); if (!d.failure.isEmpty()) return fail(source, d.failure);
        if (d.enabled) return fail(source, "Stop before changing public site geometry");
        if (d.buffers.containsKey(pos.asLong()) || d.buffers.values().stream().anyMatch(b -> b.production() && b.machine == pos.asLong()))
            return fail(source, "Source, mill and buffer must be different sites");
        if (!d.sources.contains(pos.asLong()) && d.sources.size() >= MAX_SITES) { d.capacityDenials++; d.setDirty(); return fail(source, "Source capacity exhausted"); }
        d.sources.add(pos.asLong()); d.setDirty(); return okay(source, "Public source rendezvous configured; stock remains private and unknown");
    }

    private static int enroll(CommandSourceStack source, Villager citizen) {
        ServerLevel level = source.getLevel(); ServiceData d = data(level);
        if (!d.failure.isEmpty()) return fail(source, d.failure);
        if (d.enabled || CivilizationRuntime.enabled(level)) return fail(source, "Stop service and legacy colony dispatch before enrollment");
        if (citizen.level() != level || !citizen.getPersistentData().getBoolean("hearthbound.sable")) return fail(source, "Requires a Sable-marked citizen in this dimension");
        if (citizen.getPersistentData().contains("hearthbound.private_communication_trial.v1")
                || citizen.getPersistentData().contains("hearthbound.civilization.v1") || SableHauling.active(citizen))
            return fail(source, "Citizen belongs to another controller or has an unresolved native motor");
        if (!d.enrolled.contains(citizen.getUUID()) && d.enrolled.size() >= MAX_CITIZENS) { d.capacityDenials++; d.setDirty(); return fail(source, "Enrollment capacity exhausted"); }
        d.enrolled.add(citizen.getUUID()); learner(d, citizen.getUUID()); CompoundTag m = memory(citizen);
        m.putBoolean("enrolled", true); m.putUUID("world", d.kernel.scope().world());
        m.putString("dimension", d.kernel.scope().dimension()); m.putString("option", "WAIT"); m.putString("state", "IDLE");
        saveMemory(citizen, m); stopMotion(citizen); citizen.setPersistenceRequired();
        event(d, level, "CITIZEN_ENROLLED", citizen, null, null); return okay(source, "Citizen enrolled with the same service capabilities");
    }

    private static int start(CommandSourceStack source) {
        ServerLevel level = source.getLevel(); ServiceData d = data(level);
        if (!d.failure.isEmpty()) return fail(source, d.failure);
        if (d.enabled) return fail(source, "Service dispatch is already enabled");
        if (CivilizationRuntime.enabled(level)) return fail(source, "Disable legacy colony dispatch first");
        if (d.buffers.isEmpty() || d.sources.isEmpty() || d.enrolled.isEmpty()) return fail(source, "Configure both sites and enroll citizens first");
        if (d.records.size() >= MAX_RECORDS - 16) return fail(source, "Service evidence capacity exhausted");
        if (d.kernel.commitments().stream().anyMatch(Commitment::active)) return fail(source, "Held physical commitments require native reconciliation; start cannot release them");
        List<Villager> citizens = new ArrayList<>();
        for (UUID id : d.enrolled) {
            if (!(level.getEntity(id) instanceof Villager citizen)) return fail(source, "All enrolled citizens must be loaded for explicit revalidation");
            CompoundTag existingMemory = memory(citizen);
            if (!controls(citizen) || SableHauling.active(citizen) || learner(d, id).active() != null
                    || existingMemory.contains(ServiceProductionBridge.CARGO)
                    || (existingMemory.contains(ServiceProductionBridge.PHASE) && !"FINALIZED".equals(existingMemory.getString(ServiceProductionBridge.PHASE)))
                    || citizen.getPersistentData().contains("hearthbound.private_communication_trial.v1"))
                return fail(source, "Foreign or unresolved physical owner blocks start");
            citizens.add(citizen);
        }
        d.session = SourceReportSession.episode(level);
        d.admitted.clear(); d.enabled = true;
        for (Villager citizen : citizens) {
            CompoundTag m = memory(citizen); m.putUUID("session", d.session); m.remove("sent"); saveMemory(citizen, m); idle(citizen, level.getGameTime());
        }
        event(d, level, "SERVICE_STARTED", null, null, null); return okay(source, "Local need services enabled after idle-owner revalidation; selector=" + POLICY);
    }

    private static int stop(CommandSourceStack source) {
        ServerLevel level = source.getLevel(); ServiceData d = data(level); d.enabled = false;
        if (!d.failure.isEmpty()) return fail(source, d.failure);
        for (UUID id : d.enrolled) if (level.getEntity(id) instanceof Villager citizen) {
            trackTravel(citizen);
            Commitment c = d.kernel.active(id);
            CompoundTag motor = citizen.getPersistentData().getCompound(HAUL);
            CompoundTag m = memory(citizen);
            boolean liveOwner = m.hasUUID("session") && m.getUUID("session").equals(d.session)
                && c != null && c.job() != null && motor.hasUUID("jobId") && motor.getUUID("jobId").equals(c.job());
            if (liveOwner && c.state() != State.HELD && !motor.contains("cargo") && SableHauling.cancelBeforePickup(level, citizen)) {
                d.kernel.cancelBeforePickup(c.id(), id, c.job(), level.getGameTime()); d.cancelled++;
                JsonObject r = event(d, level, "OPTION_CANCELLED", citizen, c.needId(), c.job());
                id(r, "commitment", c.id()); r.addProperty("reason", "OPERATOR_STOP_BEFORE_PICKUP");
                settleService(d, level, citizen, Outcome.VERIFIED_NO_CARGO_CANCEL); idle(citizen, level.getGameTime());
            }
            if (d.kernel.active(id) != null || SableHauling.active(citizen)) hold(d, level, citizen, "OPERATOR_STOP");
            else {
                if ("ACTIVE".equals(memory(citizen).getString("state"))) {
                    JsonObject r = event(d, level, "OPTION_CANCELLED", citizen,
                        memory(citizen).hasUUID("request") ? memory(citizen).getUUID("request") : null, null);
                    r.addProperty("reason", "OPERATOR_STOP_NO_PHYSICAL_JOB"); d.cancelled++;
                    settleService(d, level, citizen, Outcome.VERIFIED_NO_CARGO_CANCEL);
                }
                park(citizen);
            }
        }
        event(d, level, "SERVICE_STOPPED", null, null, null); return okay(source, "Dispatch stopped; unpicked live jobs cancel safely and uncertain/carrying work remains held");
    }

    private static String learningDigest(CitizenServiceLearning learning) {
        try {
            return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256")
                .digest(GSON.toJson(learning.snapshot()).getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.NoSuchAlgorithmException impossible) { throw new IllegalStateException(impossible); }
    }

    private static int status(CommandSourceStack source) {
        ServerLevel level = source.getLevel(); ServiceData d = data(level); JsonObject r = new JsonObject();
        r.addProperty("schema", "hearthbound.need-services.v1"); r.addProperty("enabled", d.enabled);
        r.addProperty("enrolled", d.enrolled.size()); int activeOptions = 0, held = 0, activeProductive = 0, activeCarry = 0;
        int serviceSamples = 0, productionSamples = 0;
        JsonArray citizens = new JsonArray();
        for (UUID id : d.enrolled) {
            JsonObject c = new JsonObject(); id(c, "citizen", id);
            if (level.getEntity(id) instanceof Villager citizen) {
                CompoundTag m = memory(citizen); c.addProperty("loaded", true); c.addProperty("option", m.getString("option")); c.addProperty("state", m.getString("state"));
                if ("ACTIVE".equals(m.getString("state"))) {
                    activeOptions++;
                    if ("SUPPLY_WHEAT".equals(m.getString("option"))) activeProductive++;
                    if ("CARRY_REQUEST".equals(m.getString("option"))) activeCarry++;
                }
                if (m.contains(ServiceProductionBridge.PHASE)) c.addProperty("production_phase", m.getString(ServiceProductionBridge.PHASE));
                if (m.contains(ServiceProductionBridge.CARGO)) c.add("cargo", GSON.toJsonTree(ServiceProductionBridge.outputItems(m)));
                if ("HELD".equals(m.getString("state"))) held++;
                if (m.contains("reason")) c.addProperty("reason", m.getString("reason"));
            } else { c.addProperty("loaded", false); c.addProperty("state", "UNLOADED"); }
            if (d.kernel != null) {
                CitizenServiceLearning learning = learner(d, id); var state = learning.status();
                c.addProperty("service_samples", state.serviceSamples()); c.addProperty("production_samples", state.productionSamples());
                c.addProperty("verified_output_units", state.independentlyVerifiedOutputUnits());
                c.addProperty("pending_decision", learning.active() != null);
                c.addProperty("decisions", learning.snapshot().decisions().size()); c.add("parameters", GSON.toJsonTree(learning.parameters()));
                c.addProperty("learning_digest", learningDigest(learning));
                serviceSamples += state.serviceSamples(); productionSamples += state.productionSamples();
            }
            citizens.add(c);
        }
        r.addProperty("active_productive_options", activeProductive); r.addProperty("active_carry_options", activeCarry);
        r.addProperty("active_options", activeOptions); r.addProperty("held", held);
        r.addProperty("active_commitments", d.kernel == null ? 0 : d.kernel.commitments().stream().filter(Commitment::active).count());
        r.addProperty("assigned", d.assigned); r.addProperty("transfers", d.transfers); r.addProperty("cancelled", d.cancelled);
        r.addProperty("records_total", d.records.size()); r.addProperty("capacity_denials", d.capacityDenials);
        r.addProperty("production_jobs", d.productionJobs); r.addProperty("output_units", d.outputUnits);
        r.addProperty("production_credits", productionSamples); r.addProperty("production_credit_count", productionSamples);
        r.addProperty("learning_mode", "PRIVATE_RLS_WITH_AUTHORED_PRIORS"); r.addProperty("learner_ready", productionSamples > 0);
        r.addProperty("learning_cost_updates", serviceSamples); r.addProperty("learning_production_updates", productionSamples);
        r.addProperty("cost_updates", serviceSamples);
        JsonArray errors = new JsonArray(); if (!d.failure.isEmpty()) errors.add(d.failure); r.add("errors", errors);
        r.addProperty("policy", POLICY); r.addProperty("failure", d.failure); id(r, "session", d.session); r.add("citizens", citizens);
        source.sendSuccess(() -> Component.literal("NEED_SERVICES_STATUS " + GSON.toJson(r)), false); return d.failure.isEmpty() ? 1 : 0;
    }

    private static int records(CommandSourceStack source, int offset) {
        ServiceData d = data(source.getLevel()); JsonObject r = new JsonObject(); JsonArray entries = new JsonArray();
        for (int i = offset; i < Math.min(d.records.size(), offset + 4); i++) entries.add(d.records.get(i));
        r.addProperty("offset", offset); r.addProperty("total", d.records.size()); r.add("records", entries);
        source.sendSuccess(() -> Component.literal("NEED_SERVICES_RECORDS " + GSON.toJson(r)), false); return 1;
    }
}
