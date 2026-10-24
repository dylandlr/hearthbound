package dev.hearthbound.gametest;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.research.DurableOperationIntents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.TagParser;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;

/** CI fixture bridge. Credits only an isolated fixture ledger, never live citizens. */
final class MillingCheckpointFixture {
    private MillingCheckpointFixture() {}
    static CompoundTag inventory(MillstoneBlockEntity mill) {
        CompoundTag result = new CompoundTag();
        result.put("Input", mill.inputInv.getStackInSlot(0).save(new CompoundTag()));
        ListTag outputs = new ListTag();
        for (int slot = 0; slot < mill.outputInv.getSlots(); slot++)
            outputs.add(mill.outputInv.getStackInSlot(slot).save(new CompoundTag()));
        result.put("Outputs", outputs);
        return result;
    }
    private static DurableOperationIntents store(MinecraftServer server) throws java.io.IOException {
        var path = server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-intents");
        java.nio.file.Files.createDirectories(path);
        return new DurableOperationIntents(path);
    }
    static DurableOperationIntents.Intent prepare(MillstoneBlockEntity mill) {
        try {
            // Fixture incarnation is unique; production requires persistent world/machine identity.
            String key = "fixture/" + java.util.UUID.randomUUID() + "/"
                    + mill.getLevel().dimension().location() + "/" + mill.getBlockPos().asLong();
            var prepared = store(mill.getLevel().getServer()).prepare(key, inventory(mill).toString());
            if (!prepared.newlyCreated()) throw new IllegalStateException("Fixture intent must be new");
            return prepared.intent();
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot persist fixture intent before enabling motor", failure);
        }
    }
    static void checkpoint(MillstoneBlockEntity mill, DurableOperationIntents.Intent intent) {
        try {
            CompoundTag expected = new CompoundTag();
            expected.putUUID("Operation", intent.operationId());
            expected.putString("MachineKey", intent.machineKey());
            expected.putString("Before", intent.evidence());
            expected.putLong("Position", mill.getBlockPos().asLong());
            expected.put("Inventory", inventory(mill));
            mill.setChanged();
            mill.getLevel().getServer().saveAllChunks(false, true, true);
            MillingDiscoveryFixture.award(mill, intent, expected);
            NbtIo.writeCompressed(expected, new java.io.File("milling-machine-expected.nbt"));
        } catch (java.io.IOException failure) {
            throw new IllegalStateException("Cannot checkpoint fixture machine", failure);
        }
    }
    static void verify(MinecraftServer server, java.io.File expectedFile) throws java.io.IOException {
        CompoundTag expected = NbtIo.readCompressed(expectedFile);
        var intents = store(server);
        var pending = intents.pending(expected.getString("MachineKey"))
                .orElseThrow(() -> new IllegalStateException("Missing pre-operation intent after restart"));
        if (!pending.operationId().equals(expected.getUUID("Operation"))
                || !pending.evidence().equals(expected.getString("Before")))
            throw new IllegalStateException("Intent identity or full evidence changed");
        var recovered = intents.prepare(pending.machineKey(), pending.evidence());
        if (recovered.newlyCreated() || !recovered.intent().equals(pending))
            throw new IllegalStateException("Recovered intent must require reconciliation");
        var entity = server.overworld().getBlockEntity(BlockPos.of(expected.getLong("Position")));
        if (!(entity instanceof MillstoneBlockEntity mill))
            throw new IllegalStateException("Checkpointed millstone missing");
        CompoundTag actual = inventory(mill);
        if (!actual.equals(expected.getCompound("Inventory")) || mill.getSpeed() != 0)
            throw new IllegalStateException("Reloaded machine inventory or stopped state differs");
        try {
            if (actual.equals(TagParser.parseTag(pending.evidence())))
                throw new IllegalStateException("Test must distinguish pre-operation and completed inventory");
        } catch (com.mojang.brigadier.exceptions.CommandSyntaxException invalid) {
            throw new IllegalStateException("Invalid full intent evidence", invalid);
        }
        boolean conflictRejected = false;
        try { intents.prepare(pending.machineKey(), actual.toString()); }
        catch (java.io.IOException expectedConflict) { conflictRejected = true; }
        if (!conflictRejected || !intents.pending(pending.machineKey()).orElseThrow().equals(pending))
            throw new IllegalStateException("Changed machine state must preserve unresolved intent");
        MillingDiscoveryFixture.verify(server, pending, expected);
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_MACHINE_CHECKPOINT_PASS operation={} inventory=true recoveredIntent=true researchCredit=false",
                pending.operationId());
    }
}
