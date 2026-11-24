package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;

/**
 * Private need evidence and authoritative one-unit service arbitration.
 * No Minecraft reads, navigation, inventory changes, or reward authority live
 * here. The Forge adapter must independently establish local observations,
 * physical message encounters, motor cancellation, and transfer receipts.
 * Public record constructors validate data contracts, not physical authenticity.
 */
public final class NeedServiceKernel {
    public static final int SCHEMA_VERSION = 1;
    public static final int MAX_NEEDS = 128, MAX_CITIZENS = 128, MAX_KNOWN = 64;
    public static final int MAX_RECORDS = 8192, MAX_PACKETS = 16384, MAX_HOPS = 8;

    public record Scope(UUID world, String dimension) {
        public Scope { Objects.requireNonNull(world); text(dimension, 256); }
    }
    public record Need(UUID id, Scope scope, long site, String item, int units,
                       long revision, UUID observer, long observedTick, long expiresTick) {
        public Need {
            Objects.requireNonNull(id); Objects.requireNonNull(scope); Objects.requireNonNull(observer);
            text(item, 256);
            if (units < 0 || units > 64 || revision < 1 || observedTick < 0
                    || expiresTick <= observedTick || expiresTick - observedTick > 24000)
                throw new IllegalArgumentException("Invalid observed need");
        }
    }
    public record Knowledge(Need need, UUID packetId, UUID from, long learnedTick, int hops) {
        public Knowledge {
            Objects.requireNonNull(need); Objects.requireNonNull(from);
            if (learnedTick < need.observedTick() || learnedTick > need.expiresTick()
                    || hops < 0 || hops > MAX_HOPS || (packetId == null) != (hops == 0)
                    || (packetId == null && !from.equals(need.observer())))
                throw new IllegalArgumentException("Invalid private need knowledge");
        }
        public boolean direct() { return packetId == null; }
    }
    public record Packet(UUID id, Need need, UUID sender, UUID recipient,
                         long sentTick, int hops, UUID parent) {
        public Packet {
            Objects.requireNonNull(id); Objects.requireNonNull(need);
            Objects.requireNonNull(sender); Objects.requireNonNull(recipient);
            if (sender.equals(recipient) || sentTick < need.observedTick()
                    || sentTick > need.expiresTick() || hops < 1 || hops > MAX_HOPS
                    || (parent == null) != (hops == 1)
                    || (parent == null && !sender.equals(need.observer())))
                throw new IllegalArgumentException("Invalid request packet");
        }
    }
    public enum State { RESERVED, RUNNING, CARRYING, DRAINING, HELD, DELIVERED, CANCELLED }
    public record Commitment(UUID id, UUID citizen, UUID needId, long revision,
                             State state, UUID job, long reservedTick, long leaseUntil,
                             long finishedTick, UUID transferReceipt, String reason) {
        public Commitment {
            Objects.requireNonNull(id); Objects.requireNonNull(citizen); Objects.requireNonNull(needId);
            Objects.requireNonNull(state); text(reason, 512);
            boolean terminal = state == State.DELIVERED || state == State.CANCELLED;
            if (revision < 1 || reservedTick < 0 || leaseUntil <= reservedTick
                    || (terminal ? finishedTick < reservedTick : finishedTick != -1)
                    || (state == State.RESERVED && job != null)
                    || ((state == State.RUNNING || state == State.CARRYING
                         || state == State.DRAINING || state == State.DELIVERED) && job == null)
                    || (state == State.DELIVERED) != (transferReceipt != null))
                throw new IllegalArgumentException("Invalid service commitment");
        }
        public boolean active() { return state != State.DELIVERED && state != State.CANCELLED; }
    }
    public record TransferReceipt(UUID id, Scope scope, UUID commitment, UUID citizen,
                                  UUID job, long destination, long tick, int units) {
        public TransferReceipt {
            Objects.requireNonNull(id); Objects.requireNonNull(scope); Objects.requireNonNull(commitment);
            Objects.requireNonNull(citizen); Objects.requireNonNull(job);
            if (tick < 0 || units != 1) throw new IllegalArgumentException("A lease transfers exactly one unit");
        }
    }
    public record NeedState(Need need, int deliveredSinceObservation, long refreshAfterTick) {
        public NeedState(Need need, int deliveredSinceObservation) { this(need, deliveredSinceObservation, -1); }
        public NeedState {
            Objects.requireNonNull(need);
            if (deliveredSinceObservation < 0 || deliveredSinceObservation > MAX_RECORDS || refreshAfterTick < -1)
                throw new IllegalArgumentException("Invalid observed-need delivery count");
        }
    }
    public record BookEntry(UUID citizen, Knowledge knowledge) {
        public BookEntry { Objects.requireNonNull(citizen); Objects.requireNonNull(knowledge); }
    }
    public record Reception(UUID packetId, long deliveredTick) {
        public Reception {
            Objects.requireNonNull(packetId);
            if (deliveredTick < 0) throw new IllegalArgumentException("Negative request delivery tick");
        }
    }
    public record Snapshot(int schemaVersion, Scope scope, List<NeedState> needs,
                           List<BookEntry> books, List<Packet> packets, List<Reception> receivedPackets,
                           List<Commitment> commitments, List<TransferReceipt> transfers) {
        public Snapshot {
            Objects.requireNonNull(scope);
            needs = List.copyOf(needs); books = List.copyOf(books); packets = List.copyOf(packets);
            receivedPackets = List.copyOf(receivedPackets); commitments = List.copyOf(commitments);
            transfers = List.copyOf(transfers);
            if (schemaVersion != SCHEMA_VERSION || needs.size() > MAX_NEEDS
                    || books.size() > MAX_CITIZENS * MAX_KNOWN || packets.size() > MAX_PACKETS
                    || receivedPackets.size() > MAX_PACKETS || commitments.size() > MAX_RECORDS
                    || transfers.size() > MAX_RECORDS)
                throw new IllegalArgumentException("Invalid or over-capacity service snapshot");
        }
    }

    private final Scope scope;
    private final LinkedHashMap<UUID, NeedState> needs = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, LinkedHashMap<UUID, Knowledge>> books = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, Packet> packets = new LinkedHashMap<>();
    private final Map<String, UUID> packetKeys = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, Long> received = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, Commitment> commitments = new LinkedHashMap<>();
    private final LinkedHashMap<UUID, TransferReceipt> transfers = new LinkedHashMap<>();

    public NeedServiceKernel(Scope scope) { this.scope = Objects.requireNonNull(scope); }
    public Scope scope() { return scope; }
    private static void text(String value, int maximum) {
        if (value == null || value.isBlank() || value.length() > maximum)
            throw new IllegalArgumentException("Invalid bounded text");
    }
    private static void tick(long now) { if (now < 0) throw new IllegalArgumentException("Negative tick"); }
    private static boolean fresh(Need need, long now) {
        return need.observedTick() <= now && now <= need.expiresTick();
    }
    private void sameScope(Scope other) {
        if (!scope.equals(other)) throw new IllegalArgumentException("Foreign service scope");
    }
    private static boolean sameSubject(Need a, Need b) {
        return a.id().equals(b.id()) && a.scope().equals(b.scope())
            && a.site() == b.site() && a.item().equals(b.item());
    }
    private LinkedHashMap<UUID, Knowledge> book(UUID citizen) {
        Objects.requireNonNull(citizen);
        var existing = books.get(citizen);
        if (existing != null) return existing;
        if (books.size() >= MAX_CITIZENS) throw new IllegalStateException("Private-book capacity exhausted");
        var created = new LinkedHashMap<UUID, Knowledge>();
        books.put(citizen, created);
        return created;
    }
    private void remember(UUID citizen, Knowledge knowledge) {
        var book = book(citizen);
        book.remove(knowledge.need().id());
        if (book.size() >= MAX_KNOWN) book.remove(book.keySet().iterator().next());
        book.put(knowledge.need().id(), knowledge);
    }

    /** Direct sensor admission. A higher revision must come from a current local observation. */
    public synchronized boolean observe(Need need, long now) {
        Objects.requireNonNull(need); tick(now); sameScope(need.scope());
        if (need.observedTick() != now) throw new IllegalArgumentException("Direct need must be observed now");
        NeedState old = needs.get(need.id());
        if (old != null) {
            if (!sameSubject(old.need(), need)) throw new IllegalArgumentException("Need identity changed subject");
            if (need.revision() < old.need().revision()) return false;
            if (need.revision() == old.need().revision()) {
                if (!need.equals(old.need())) throw new IllegalStateException("Conflicting need revision");
                return false;
            }
            if (need.observedTick() < old.need().observedTick()) return false;
        } else if (needs.size() >= MAX_NEEDS) return false;
        if (!books.containsKey(need.observer()) && books.size() >= MAX_CITIZENS) return false;
        // The new physical shortfall already reflects all preceding insertions.
        // Existing physical jobs still reserve their one unit across revisions.
        long refreshAfter = old != null && need.observedTick() <= old.refreshAfterTick() ? old.refreshAfterTick() : -1;
        needs.put(need.id(), new NeedState(need, 0, refreshAfter));
        remember(need.observer(), new Knowledge(need, null, need.observer(), now, 0));
        return true;
    }

    /** Actor-facing reads use only this citizen's own acquired evidence. */
    public synchronized List<Knowledge> known(UUID citizen, long now) {
        Objects.requireNonNull(citizen); tick(now);
        var own = books.get(citizen);
        if (own == null) return List.of();
        return own.values().stream().filter(k -> fresh(k.need(), now)).toList();
    }
    /** Authoritative arbitration data, never a source for actor candidate enumeration. */
    public synchronized Need latest(UUID needId) {
        var state = needs.get(needId); return state == null ? null : state.need();
    }
    private static String packetKey(Packet p) {
        return p.sender() + ":" + p.recipient() + ":" + p.need().id() + ":"
            + p.need().revision() + ":" + p.need().observedTick() + ":" + p.parent();
    }
    public synchronized Packet packet(UUID sender, UUID recipient, UUID needId, long now) {
        Objects.requireNonNull(sender); Objects.requireNonNull(recipient); Objects.requireNonNull(needId); tick(now);
        if (sender.equals(recipient)) return null;
        Knowledge own = books.containsKey(sender) ? books.get(sender).get(needId) : null;
        if (own == null || !fresh(own.need(), now) || own.hops() >= MAX_HOPS) return null;
        Packet made = new Packet(UUID.randomUUID(), own.need(), sender, recipient, now,
                                 own.hops() + 1, own.packetId());
        UUID prior = packetKeys.get(packetKey(made));
        if (prior != null) return packets.get(prior);
        if (packets.size() >= MAX_PACKETS) return null;
        packets.put(made.id(), made); packetKeys.put(packetKey(made), made.id());
        return made;
    }
    /** The adapter must check the actual sender/recipient encounter before calling. */
    public synchronized boolean receive(Packet packet, long now) {
        Objects.requireNonNull(packet); tick(now); sameScope(packet.need().scope());
        if (!packet.equals(packets.get(packet.id()))) throw new IllegalArgumentException("Unregistered or changed packet");
        if (received.containsKey(packet.id()) || now < packet.sentTick() || !fresh(packet.need(), now)) return false;
        if (!books.containsKey(packet.recipient()) && books.size() >= MAX_CITIZENS) return false;
        var own = books.get(packet.recipient());
        Knowledge previous = own == null ? null : own.get(packet.need().id());
        received.put(packet.id(), now);
        if (previous != null && previous.need().revision() >= packet.need().revision()) return false;
        remember(packet.recipient(), new Knowledge(packet.need(), packet.id(), packet.sender(), now, packet.hops()));
        return true;
    }

    public synchronized Commitment active(UUID citizen) {
        Objects.requireNonNull(citizen);
        for (Commitment c : commitments.values()) if (c.citizen().equals(citizen) && c.active()) return c;
        return null;
    }
    public synchronized Commitment commitment(UUID id) { return commitments.get(id); }
    public synchronized List<Commitment> commitments() { return List.copyOf(commitments.values()); }
    public synchronized int availableUnits(UUID needId, long now) {
        tick(now); NeedState state = needs.get(needId);
        if (state == null || !fresh(state.need(), now)
                || state.need().observedTick() <= state.refreshAfterTick()) return 0;
        long held = commitments.values().stream().filter(c -> c.needId().equals(needId) && c.active()).count();
        return (int)Math.max(0L, state.need().units() - state.deliveredSinceObservation() - held);
    }
    public synchronized Commitment reserve(UUID citizen, UUID needId, long expectedRevision,
                                            long now, long leaseUntil) {
        Objects.requireNonNull(citizen); Objects.requireNonNull(needId); tick(now);
        if (leaseUntil <= now) throw new IllegalArgumentException("Invalid lease interval");
        Need need = latest(needId);
        Knowledge own = books.containsKey(citizen) ? books.get(citizen).get(needId) : null;
        if (need == null || own == null || !fresh(own.need(), now) || own.need().units() == 0
                || own.need().revision() != expectedRevision || expectedRevision > need.revision()
                || active(citizen) != null || availableUnits(needId, now) == 0
                || commitments.size() >= MAX_RECORDS) return null;
        Commitment made = new Commitment(UUID.randomUUID(), citizen, needId, expectedRevision,
            State.RESERVED, null, now, leaseUntil, -1, null, "ONE_UNIT_RESERVED");
        commitments.put(made.id(), made); return made;
    }
    private Commitment require(UUID id) {
        Commitment c = commitments.get(id);
        if (c == null) throw new IllegalArgumentException("Unknown commitment");
        return c;
    }
    private Commitment replace(Commitment c, State state, UUID job, long finished, UUID receipt, String reason) {
        Commitment updated = new Commitment(c.id(), c.citizen(), c.needId(), c.revision(), state, job,
            c.reservedTick(), c.leaseUntil(), finished, receipt, reason);
        commitments.put(c.id(), updated); return updated;
    }
    public synchronized Commitment begin(UUID id, UUID citizen, UUID job, long now) {
        Objects.requireNonNull(job); tick(now); Commitment c = require(id);
        if (!c.citizen().equals(citizen) || c.state() != State.RESERVED || shouldCancel(id, now))
            throw new IllegalStateException("Cannot start this reserved service");
        if (commitments.values().stream().anyMatch(other -> job.equals(other.job())))
            throw new IllegalStateException("Physical job already belongs to a commitment");
        return replace(c, State.RUNNING, job, -1, null, "PHYSICAL_JOB_STARTED");
    }
    public synchronized Commitment pickedUp(UUID id, UUID job, long now) {
        tick(now); Commitment c = require(id);
        if (!Objects.equals(c.job(), job) || now < c.reservedTick()
                || (c.state() != State.RUNNING && c.state() != State.CARRYING && c.state() != State.DRAINING))
            throw new IllegalStateException("Pickup does not belong to an active physical job");
        if (c.state() != State.RUNNING) return c;
        return replace(c, shouldCancel(id, now) ? State.DRAINING : State.CARRYING, job, -1, null,
                       "PHYSICAL_PICKUP_OBSERVED");
    }
    public synchronized boolean shouldCancel(UUID id, long now) {
        tick(now); Commitment c = require(id); Need need = latest(c.needId());
        if (!c.active()) return false;
        return now < c.reservedTick() || now > c.leaseUntil() || need == null
            || need.units() == 0 || !fresh(need, now);
    }
    /** A native motor cancellation/no-cargo acknowledgement is a caller prerequisite. */
    public synchronized Commitment cancelBeforePickup(UUID id, UUID citizen, UUID expectedJob, long now) {
        tick(now); Commitment c = require(id);
        if (!c.citizen().equals(citizen) || !Objects.equals(c.job(), expectedJob) || now < c.reservedTick()
                || (c.state() != State.RESERVED && c.state() != State.RUNNING && c.state() != State.HELD))
            throw new IllegalStateException("Unsafe or mismatched pre-pickup cancellation");
        return replace(c, State.CANCELLED, c.job(), now, null, "NATIVE_NO_CARGO_CANCELLATION_CONFIRMED");
    }
    public synchronized Commitment hold(UUID id, String reason, long now) {
        tick(now); text(reason, 512); Commitment c = require(id);
        if (!c.active()) throw new IllegalStateException("Completed service cannot become uncertain");
        return replace(c, State.HELD, c.job(), -1, null, reason);
    }
    public synchronized void expire(long now) {
        tick(now);
        for (Commitment c : List.copyOf(commitments.values())) {
            if (!c.active() || !shouldCancel(c.id(), now)) continue;
            if (c.state() == State.RESERVED && now >= c.reservedTick())
                replace(c, State.CANCELLED, null, now, null, "UNSTARTED_LEASE_EXPIRED_OR_NEED_CLOSED");
            else if (c.state() == State.CARRYING)
                replace(c, State.DRAINING, c.job(), -1, null, "CARGO_MUST_DRAIN_OR_BE_RECONCILED");
            // RUNNING and HELD still own their physical job and their one unit.
        }
    }
    /** Independently verified insertion finishes a service, not production learning. */
    public synchronized boolean delivered(TransferReceipt receipt) {
        Objects.requireNonNull(receipt); sameScope(receipt.scope());
        TransferReceipt old = transfers.get(receipt.id());
        if (old != null) {
            if (!old.equals(receipt)) throw new IllegalStateException("Conflicting transfer receipt");
            return false;
        }
        Commitment c = require(receipt.commitment()); NeedState state = needs.get(c.needId());
        if (!c.active() || c.job() == null || !c.job().equals(receipt.job())
                || !c.citizen().equals(receipt.citizen()) || receipt.tick() < c.reservedTick()
                || state == null || state.need().site() != receipt.destination()
                || transfers.size() >= MAX_RECORDS)
            throw new IllegalStateException("Transfer does not independently settle the reserved physical job");
        transfers.put(receipt.id(), receipt);
        int delivered = state.deliveredSinceObservation();
        long refreshAfter = state.refreshAfterTick();
        if (receipt.tick() > state.need().observedTick() || state.need().revision() == c.revision()) delivered++;
        else if (receipt.tick() == state.need().observedTick()) {
            // A newer observation in the same Minecraft tick can be before or
            // after insertion. No new quantity is granted until a later sensor
            // sample resolves that ordering; the completed motor is still settled.
            refreshAfter = Math.max(refreshAfter, receipt.tick());
        }
        // A strictly later direct observation already includes an older receipt.
        needs.put(c.needId(), new NeedState(state.need(), delivered, refreshAfter));
        replace(c, State.DELIVERED, c.job(), receipt.tick(), receipt.id(), "ONE_UNIT_TRANSFER_VERIFIED");
        return true;
    }

    public synchronized Snapshot snapshot() {
        var entries = new ArrayList<BookEntry>();
        books.forEach((citizen, own) -> own.values().forEach(k -> entries.add(new BookEntry(citizen, k))));
        return new Snapshot(SCHEMA_VERSION, scope, List.copyOf(needs.values()), entries,
            List.copyOf(packets.values()), received.entrySet().stream().map(e -> new Reception(e.getKey(), e.getValue())).toList(),
            List.copyOf(commitments.values()),
            List.copyOf(transfers.values()));
    }
    /** Restored active physical commitments are held until native reconciliation. */
    public static NeedServiceKernel restore(Snapshot snapshot, Scope expected, long now) {
        Objects.requireNonNull(snapshot); tick(now);
        if (!snapshot.scope().equals(expected)) throw new IllegalArgumentException("Restored service scope mismatch");
        NeedServiceKernel result = new NeedServiceKernel(expected);
        Map<String, Need> versions = new LinkedHashMap<>();
        for (NeedState state : snapshot.needs()) {
            result.sameScope(state.need().scope());
            if (state.need().observedTick() > now || state.refreshAfterTick() > now
                    || result.needs.putIfAbsent(state.need().id(), state) != null)
                throw new IllegalArgumentException("Duplicate restored need");
            consistentVersion(versions, state.need());
        }
        for (Packet packet : snapshot.packets()) {
            result.sameScope(packet.need().scope());
            Need latest = result.latest(packet.need().id());
            if (latest == null || packet.sentTick() > now || !sameSubject(latest, packet.need())
                    || packet.need().revision() > latest.revision()
                    || result.packets.putIfAbsent(packet.id(), packet) != null
                    || result.packetKeys.putIfAbsent(packetKey(packet), packet.id()) != null)
                throw new IllegalArgumentException("Invalid restored request packet");
            consistentVersion(versions, packet.need());
        }
        for (Reception reception : snapshot.receivedPackets()) {
            Packet packet = result.packets.get(reception.packetId());
            if (packet == null || reception.deliveredTick() < packet.sentTick() || reception.deliveredTick() > now
                    || !fresh(packet.need(), reception.deliveredTick())
                    || result.received.putIfAbsent(reception.packetId(), reception.deliveredTick()) != null)
                throw new IllegalArgumentException("Invalid restored receipt identity");
        }
        for (Packet packet : snapshot.packets()) if (packet.parent() != null) {
            Packet parent = result.packets.get(packet.parent());
            Long delivered = result.received.get(packet.parent());
            if (parent == null || delivered == null || !parent.recipient().equals(packet.sender())
                    || !parent.need().equals(packet.need()) || parent.hops() + 1 != packet.hops()
                    || delivered > packet.sentTick())
                throw new IllegalArgumentException("Broken restored packet provenance");
        }
        for (BookEntry entry : snapshot.books()) {
            Knowledge k = entry.knowledge(); Need latest = result.latest(k.need().id());
            if (latest == null || k.learnedTick() > now || !sameSubject(latest, k.need())
                    || k.need().revision() > latest.revision()
                    || (k.direct() && !entry.citizen().equals(k.need().observer())))
                throw new IllegalArgumentException("Invalid restored private need evidence");
            consistentVersion(versions, k.need());
            if (!k.direct()) {
                Packet packet = result.packets.get(k.packetId());
                if (packet == null || !Objects.equals(result.received.get(packet.id()), k.learnedTick())
                        || !packet.need().equals(k.need())
                        || !packet.recipient().equals(entry.citizen()) || !packet.sender().equals(k.from())
                        || packet.hops() != k.hops() || packet.sentTick() > k.learnedTick())
                    throw new IllegalArgumentException("Restored private receipt lacks its transport");
            }
            var own = result.book(entry.citizen());
            if (own.size() >= MAX_KNOWN || own.putIfAbsent(k.need().id(), k) != null)
                throw new IllegalArgumentException("Duplicate or over-capacity restored private book");
        }
        Set<UUID> activeOwners = new LinkedHashSet<>(), jobs = new LinkedHashSet<>();
        for (Commitment c : snapshot.commitments()) {
            Need need = result.latest(c.needId());
            if (need == null || c.reservedTick() > now || c.finishedTick() > now || c.revision() > need.revision()
                    || (c.active() && !activeOwners.add(c.citizen()))
                    || (c.job() != null && !jobs.add(c.job())) || result.commitments.containsKey(c.id()))
                throw new IllegalArgumentException("Invalid restored one-owner commitment");
            result.commitments.put(c.id(), c);
            if (c.active()) result.replace(c, State.HELD, c.job(), -1, null, "RESTART_RECONCILIATION_REQUIRED");
        }
        for (TransferReceipt receipt : snapshot.transfers()) {
            result.sameScope(receipt.scope()); Commitment c = result.commitments.get(receipt.commitment());
            if (c == null || c.state() != State.DELIVERED || !receipt.id().equals(c.transferReceipt())
                    || !receipt.job().equals(c.job()) || !receipt.citizen().equals(c.citizen())
                    || receipt.tick() != c.finishedTick() || result.latest(c.needId()).site() != receipt.destination()
                    || result.transfers.putIfAbsent(receipt.id(), receipt) != null)
                throw new IllegalArgumentException("Invalid restored transfer outcome");
        }
        for (Commitment c : result.commitments.values()) if (c.state() == State.DELIVERED
                && !result.transfers.containsKey(c.transferReceipt()))
            throw new IllegalArgumentException("Completed commitment lacks its verified receipt");
        return result;
    }
    private static void consistentVersion(Map<String, Need> versions, Need need) {
        Need prior = versions.putIfAbsent(need.id() + ":" + need.revision(), need);
        if (prior != null && !prior.equals(need)) throw new IllegalArgumentException("Conflicting restored need revision");
    }
}
