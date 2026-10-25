package dev.hearthbound.gametest;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.integration.MillingObservationSavedData;
import dev.hearthbound.research.DurableCreditLedger;
import dev.hearthbound.research.CitizenDiscoveryGate;
import dev.hearthbound.research.CitizenDiscoveryCommitter;
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
    private static CitizenDiscoveryGate.Assignment assignment(Intent intent, CompoundTag observed) {
        return new CitizenDiscoveryGate.Assignment(intent.operationId(), TEST_CITIZEN,
                "world", observed.getString("Dimension"),
                Long.toString(observed.getLong("Position")), "create:milling/wheat", true);
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
        var attributed = citizen.commit(assignment(intent, observed), outcome(intent, observed), serialized);
        if (!attributed.newlyCredited() || attributed.citizenResearchBalance() != 1)
            throw new IllegalStateException("Fixture citizen did not receive exactly one verified credit");
        if (citizen.commit(assignment(intent, observed), outcome(intent, observed), serialized).newlyCredited())
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
                citizen.commit(assignment(intent, observed), outcome(intent, observed), serialized).newlyCredited())
            throw new IllegalStateException("Citizen credit missing or duplicated after restart");
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_CITIZEN_CREDIT_RESTART_PASS operation={} citizen={} balance=1 duplicateRejected=true",
                intent.operationId(), TEST_CITIZEN);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_DISCOVERY_RESTART_PASS operation={} recipe=create:milling/wheat balance=1 duplicateRejected=true",
                intent.operationId());
    }
}
