package dev.hearthbound.gametest;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.integration.MillingObservationSavedData;
import dev.hearthbound.research.DurableCreditLedger;
import dev.hearthbound.research.CitizenDiscoveryGate;
import dev.hearthbound.research.CitizenDiscoveryCommitter;
import dev.hearthbound.research.DurableMachineClaim;
import dev.hearthbound.research.DurableMachineHandoff;
import dev.hearthbound.research.MachineClaimRetirementGate;
import dev.hearthbound.research.DurableOperationIntents;
import dev.hearthbound.research.DurableOperationIntents.Intent;
import net.minecraft.nbt.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.storage.LevelResource;
import java.io.IOException;
import java.util.UUID;

/** Isolated end-to-end discovery credit fixture; not a production reward adapter. */
final class MillingDiscoveryFixture {
    private static final UUID BENEFICIARY = UUID.fromString("00000000-0000-0000-0000-000000000076");
    private MillingDiscoveryFixture() {}
    private static DurableCreditLedger ledger(MinecraftServer server) throws IOException {
        var directory = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-credits");
        java.nio.file.Files.createDirectories(directory);
        return new DurableCreditLedger(directory);
    }
    // Dedicated fixed test citizen. Never exposed as a live autonomous actor.
    private static final UUID TEST_CITIZEN = UUID.fromString("00000000-0000-0000-0000-000000000077");
    private static CitizenDiscoveryCommitter citizenCredits(MinecraftServer server) throws IOException {
        var directory = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-citizen-credits");
        java.nio.file.Files.createDirectories(directory);
        return new CitizenDiscoveryCommitter(directory);
    }
    private static DurableMachineHandoff handoffs(MinecraftServer server) throws IOException {
        var directory = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-machine-handoffs");
        java.nio.file.Files.createDirectories(directory);
        return new DurableMachineHandoff(directory);
    }
    static void acquireHandoff(MinecraftServer server, Intent intent) {
        try {
            var store = handoffs(server);
            var owner = store.acquire(intent.machineKey(), intent.operationId(), TEST_CITIZEN);
            if (owner.retired() || owner.owner().generation() != 1)
                throw new IllegalStateException("Initial machine owner must hold generation 1");
            boolean rejected = false;
            try {
                store.acquire(intent.machineKey(), UUID.randomUUID(), UUID.randomUUID());
            } catch (IOException conflict) { rejected = true; }
            if (!rejected) throw new IllegalStateException("Competing machine handoff accepted");
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot persist machine handoff before operation", failure);
        }
    }
    private static void verifyActiveHandoff(MinecraftServer server, Intent intent) throws IOException {
        var state = handoffs(server).current(intent.machineKey());
        if (state == null || state.retired() || state.owner().generation() != 1
                || !state.owner().operation().equals(intent.operationId())
                || !state.owner().citizen().equals(TEST_CITIZEN))
            throw new IllegalStateException("Machine handoff owner differs from active milling operation");
    }
    private static void finishHandoffAfterRestart(MinecraftServer server, Intent intent) throws IOException {
        var store = handoffs(server);
        verifyActiveHandoff(server, intent);
        // The calling restart fixture already checked authoritative milling observation,
        // actual machine inventory, persisted receipt and exact citizen research credit.
        var claim = machineClaims(server).recover(intent.machineKey());
        var proof = new MachineClaimRetirementGate.Evidence(intent.operationId(), TEST_CITIZEN,
                true, true, true, true, true, false);
        var decision = MachineClaimRetirementGate.evaluate(claim, proof);
        if (decision != MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT)
            throw new IllegalStateException("Verified fixture cannot retire machine");
        var retired = store.retire(intent.machineKey(), intent.operationId(), TEST_CITIZEN, decision);
        if (!retired.retired()) throw new IllegalStateException("Claim retirement was not persisted");
        UUID nextCitizen = UUID.fromString("00000000-0000-0000-0000-000000000078");
        UUID nextOperation = UUID.randomUUID();
        var successor = new DurableMachineHandoff(server.getWorldPath(LevelResource.ROOT)
                .resolve("hearthbound-fixture-machine-handoffs"))
                .acquire(intent.machineKey(), nextOperation, nextCitizen);
        if (successor.retired() || successor.owner().generation() != 2
                || !successor.owner().citizen().equals(nextCitizen))
            throw new IllegalStateException("Second citizen did not acquire generation 2");
        boolean staleRejected = false;
        try {
            store.retire(intent.machineKey(), intent.operationId(), TEST_CITIZEN,
                    MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT);
        } catch (IOException expected) { staleRejected = true; }
        if (!staleRejected) throw new IllegalStateException("Stale owner retired successor");
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_MACHINE_HANDOFF_RESTART_PASS previousCitizen={} nextCitizen={} generation=2 staleRejected=true",
                TEST_CITIZEN, nextCitizen);
    }
    private static DurableMachineClaim machineClaims(MinecraftServer server) throws IOException {
        var directory = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-machine-claims");
        java.nio.file.Files.createDirectories(directory);
        return new DurableMachineClaim(directory);
    }
    static void claimMachine(MinecraftServer server, Intent intent) {
        try {
            if (!machineClaims(server).claim(intent.machineKey(), intent.operationId(), TEST_CITIZEN).newlyCreated())
                throw new IllegalStateException("Fixture machine claim was not new");
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot claim machine before powered operation", failure);
        }
    }
    private static void verifyClaim(MinecraftServer server, Intent intent) throws IOException {
        var claim = machineClaims(server).recover(intent.machineKey());
        if (!claim.operationId().equals(intent.operationId()) || !claim.citizenId().equals(TEST_CITIZEN))
            throw new IllegalStateException("Recovered machine claim belongs to different operation or citizen");
        boolean rejected = false;
        try {
            machineClaims(server).claim(intent.machineKey(), UUID.randomUUID(), UUID.randomUUID());
        } catch (IOException conflict) { rejected = true; }
        if (!rejected) throw new IllegalStateException("Competing machine claim accepted");
    }
    private static DurableOperationIntents assignmentStore(MinecraftServer server) throws IOException {
        var directory = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-citizen-assignments");
        java.nio.file.Files.createDirectories(directory);
        return new DurableOperationIntents(directory);
    }
    private static String assignmentKey(Intent intent) {
        return "citizen-assignment/" + intent.operationId();
    }
    static void prepareAssignment(MinecraftServer server, Intent intent, String dimension, long position) {
        CompoundTag record = new CompoundTag();
        record.putUUID("Operation", intent.operationId());
        record.putUUID("Citizen", TEST_CITIZEN);
        record.putString("World", "world");
        record.putString("Dimension", dimension);
        record.putString("Position", Long.toString(position));
        record.putString("Recipe", "create:milling/wheat");
        try {
            if (!assignmentStore(server).prepare(assignmentKey(intent), record.toString()).newlyCreated())
                throw new IllegalStateException("Fixture citizen assignment must be new");
        } catch (IOException error) {
            throw new IllegalStateException("Cannot persist citizen assignment before milling", error);
        }
    }
    private static CitizenDiscoveryGate.Assignment assignment(MinecraftServer server, Intent intent) throws IOException {
        var stored = assignmentStore(server).pending(assignmentKey(intent))
                .orElseThrow(() -> new IllegalStateException("Missing pre-operation citizen assignment"));
        CompoundTag record = parse(stored.evidence());
        if (!record.hasUUID("Operation") || !record.hasUUID("Citizen")
                || !record.getUUID("Operation").equals(intent.operationId())
                || !record.getUUID("Citizen").equals(TEST_CITIZEN))
            throw new IllegalStateException("Citizen assignment does not match durable operation");
        return new CitizenDiscoveryGate.Assignment(record.getUUID("Operation"), record.getUUID("Citizen"),
                record.getString("World"), record.getString("Dimension"),
                record.getString("Position"), record.getString("Recipe"), true);
    }
    private static CitizenDiscoveryGate.Observation outcome(Intent intent, CompoundTag observed) {
        return new CitizenDiscoveryGate.Observation(intent.operationId(), "world",
                observed.getString("Dimension"), Long.toString(observed.getLong("Position")),
                observed.getString("CandidateRecipe"), observed.getString("Recipe"),
                1, observed.getString("Quality").equals("positive_deltas"), true);
    }
    private static CompoundTag parse(String evidence) {
        try { return TagParser.parseTag(evidence); }
        catch (com.mojang.brigadier.exceptions.CommandSyntaxException invalid) {
            throw new IllegalStateException("Invalid fixture evidence", invalid);
        }
    }
    private static CompoundTag observation(MinecraftServer server, long position) {
        var entries = MillingObservationSavedData.get(server).snapshot();
        CompoundTag found = null;
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag entry = entries.getCompound(i);
            if (entry.getLong("Position") == position
                    && entry.getString("Dimension").equals("minecraft:overworld")) {
                if (found != null) throw new IllegalStateException("Ambiguous fixture observations");
                found = entry;
            }
        }
        if (found == null) throw new IllegalStateException("Missing real milling outcome");
        return found;
    }
    private static void validate(Intent intent, CompoundTag observation, CompoundTag checkpoint) {
        CompoundTag before = parse(intent.evidence());
        ItemStack input = ItemStack.of(observation.getCompound("InputBefore"));
        if (!before.getCompound("Input").equals(observation.getCompound("InputBefore"))
                || !before.getList("Outputs", Tag.TAG_COMPOUND).equals(observation.getList("OutputBefore", Tag.TAG_COMPOUND))
                || !input.is(Items.WHEAT) || input.getCount() != 1
                || !ItemStack.of(observation.getCompound("InputAfter")).isEmpty()
                || !observation.getString("Recipe").equals("create:milling/wheat")
                || !observation.getString("Quality").equals("positive_deltas")
                || !checkpoint.getList("Outputs", Tag.TAG_COMPOUND).equals(observation.getList("OutputAfter", Tag.TAG_COMPOUND)))
            throw new IllegalStateException("Intent, real outcome and checkpoint do not agree");
    }
    static void award(MillstoneBlockEntity mill, Intent intent, CompoundTag expected) throws IOException {
        var server = mill.getLevel().getServer();
        verifyClaim(server, intent);
        verifyActiveHandoff(server, intent);
        CompoundTag observed = observation(server, mill.getBlockPos().asLong());
        validate(intent, observed, expected.getCompound("Inventory"));
        CompoundTag receipt = new CompoundTag();
        receipt.putUUID("Operation", intent.operationId());
        receipt.putString("MachineKey", intent.machineKey());
        receipt.putString("Discovery", "create:milling/wheat");
        receipt.put("Before", parse(intent.evidence()));
        receipt.put("Observation", observed.copy());
        // Preserve the exact serialized receipt for idempotent retry across processes.
        String serialized = receipt.toString();
        var credit = new DurableCreditLedger.Credit(intent.operationId(), BENEFICIARY, 1, serialized);
        var credits = ledger(server);
        if (credits.balance(BENEFICIARY) != 0 || !credits.commit(credit)
                || credits.commit(credit) || credits.balance(BENEFICIARY) != 1)
            throw new IllegalStateException("Fixture discovery must credit exactly once");
        var citizen = citizenCredits(server);
        var attributed = citizen.commit(assignment(server, intent), outcome(intent, observed), serialized);
        if (!attributed.newlyCredited() || attributed.citizenResearchBalance() != 1)
            throw new IllegalStateException("Fixture citizen did not receive exactly one verified credit");
        if (citizen.commit(assignment(server, intent), outcome(intent, observed), serialized).newlyCredited())
            throw new IllegalStateException("Fixture citizen received duplicate credit");
        expected.putUUID("Citizen", TEST_CITIZEN);
        expected.putString("CitizenReceipt", serialized);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_CREDIT_FIXTURE_PASS operation={} citizen={} balance=1",
                intent.operationId(), TEST_CITIZEN);
        expected.putString("DiscoveryReceipt", serialized);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_DISCOVERY_FIXTURE_AWARDED operation={} recipe=create:milling/wheat balance=1", intent.operationId());
    }
    static void verify(MinecraftServer server, Intent intent, CompoundTag expected) throws IOException {
        verifyClaim(server, intent);
        CompoundTag observed = observation(server, expected.getLong("Position"));
        validate(intent, observed, expected.getCompound("Inventory"));
        String serialized = expected.getString("DiscoveryReceipt");
        CompoundTag receipt = parse(serialized);
        if (!receipt.getUUID("Operation").equals(intent.operationId())
                || !receipt.getString("MachineKey").equals(intent.machineKey())
                || !receipt.getString("Discovery").equals("create:milling/wheat")
                || !receipt.getCompound("Before").equals(parse(intent.evidence()))
                || !receipt.getCompound("Observation").equals(observed))
            throw new IllegalStateException("Persisted discovery receipt changed");
        var credits = ledger(server);
        if (credits.balance(BENEFICIARY) != 1)
            throw new IllegalStateException("Discovery credit missing after restart");
        var credit = new DurableCreditLedger.Credit(intent.operationId(), BENEFICIARY, 1, serialized);
        if (credits.commit(credit)) throw new IllegalStateException("Discovery awarded twice after restart");
        boolean rejected = false;
        try { credits.commit(new DurableCreditLedger.Credit(intent.operationId(), BENEFICIARY, 2, serialized)); }
        catch (IOException conflict) { rejected = true; }
        if (!rejected || credits.balance(BENEFICIARY) != 1)
            throw new IllegalStateException("Conflicting retry changed discovery credit");
        if (!expected.hasUUID("Citizen") || !expected.getUUID("Citizen").equals(TEST_CITIZEN)
                || !expected.getString("CitizenReceipt").equals(serialized))
            throw new IllegalStateException("Citizen fixture provenance changed");
        var citizen = citizenCredits(server);
        if (citizen.balance(TEST_CITIZEN) != 1 ||
                citizen.commit(assignment(server, intent), outcome(intent, observed), serialized).newlyCredited())
            throw new IllegalStateException("Citizen credit missing or duplicated after restart");
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_CREDIT_RESTART_PASS operation={} citizen={} balance=1 duplicateRejected=true",
                intent.operationId(), TEST_CITIZEN);
        finishHandoffAfterRestart(server, intent);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_DISCOVERY_RESTART_PASS operation={} recipe=create:milling/wheat balance=1 duplicateRejected=true",
                intent.operationId());
    }
}
