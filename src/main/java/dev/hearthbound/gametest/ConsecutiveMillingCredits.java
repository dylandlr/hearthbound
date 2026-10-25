package dev.hearthbound.gametest;

import dev.hearthbound.research.CitizenDiscoveryCommitter;
import dev.hearthbound.research.CitizenDiscoveryGate;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.storage.LevelResource;
import java.io.IOException;
import java.util.UUID;

/** Separate fixture-only credits for two actual Create processing events. */
final class ConsecutiveMillingCredits {
    static final UUID FIRST = UUID.fromString("00000000-0000-0000-0000-000000000081");
    static final UUID SECOND = UUID.fromString("00000000-0000-0000-0000-000000000082");
    private ConsecutiveMillingCredits() {}
    private static CitizenDiscoveryCommitter ledger(MinecraftServer server) throws IOException {
        var dir=server.getWorldPath(LevelResource.ROOT).resolve("hearthbound-fixture-consecutive-credits");
        java.nio.file.Files.createDirectories(dir);
        return new CitizenDiscoveryCommitter(dir);
    }
    private static CitizenDiscoveryGate.Assignment assigned(UUID op, UUID citizen, CompoundTag evidence) {
        return new CitizenDiscoveryGate.Assignment(op,citizen,"world",
                evidence.getString("Dimension"),Long.toString(evidence.getLong("Position")),
                "create:milling/wheat",true);
    }
    private static CitizenDiscoveryGate.Observation observed(UUID op,CompoundTag evidence) {
        return new CitizenDiscoveryGate.Observation(op,"world",evidence.getString("Dimension"),
                Long.toString(evidence.getLong("Position")),evidence.getString("CandidateRecipe"),
                evidence.getString("Recipe"),1,
                "positive_deltas".equals(evidence.getString("Quality")),true);
    }
    static void award(MinecraftServer server,UUID operation,UUID citizen,CompoundTag evidence)
            throws IOException {
        if(!"create:milling/wheat".equals(evidence.getString("Recipe"))
                || !"positive_deltas".equals(evidence.getString("Quality")))
            throw new IOException("No verified Create wheat mutation");
        var result=ledger(server).commit(assigned(operation,citizen,evidence),observed(operation,evidence),
                "hearthbound:fixture:real-create:"+operation+":"+evidence.getUUID("Id"));
        if(!result.newlyCredited() || result.citizenResearchBalance()!=1)
            throw new IOException("Operation credit not unique");
    }
    static void saveExpected(UUID opA,UUID opB,CompoundTag first,CompoundTag second)
            throws IOException {
        var tag=new CompoundTag();
        tag.putUUID("FirstOperation",opA);tag.putUUID("SecondOperation",opB);
        tag.put("FirstEvidence",first.copy());tag.put("SecondEvidence",second.copy());
        NbtIo.writeCompressed(tag,new java.io.File("consecutive-millings-expected.nbt"));
    }
    static void verifyRestart(MinecraftServer server) throws IOException {
        var file=new java.io.File("consecutive-millings-expected.nbt");
        if(!file.isFile()) throw new IOException("Missing consecutive milling expectation");
        var record=NbtIo.readCompressed(file);
        UUID first=record.getUUID("FirstOperation"),second=record.getUUID("SecondOperation");
        var a=record.getCompound("FirstEvidence");
        var b=record.getCompound("SecondEvidence");
        if(first.equals(second)||a.getUUID("Id").equals(b.getUUID("Id")))
            throw new IOException("Duplicate real operation");
        var journal=dev.hearthbound.integration.MillingObservationSavedData.get(server);
        if(!a.equals(journal.find(a.getUUID("Id")))||!b.equals(journal.find(b.getUUID("Id"))))
            throw new IOException("Real Create evidence not retained after restart");
        var credits=ledger(server);
        if(credits.balance(FIRST)!=1||credits.balance(SECOND)!=1)
            throw new IOException("Citizen research balances not retained");
        if(credits.commit(assigned(first,FIRST,a),observed(first,a),
                "hearthbound:fixture:real-create:"+first+":"+a.getUUID("Id")).newlyCredited()
                || credits.commit(assigned(second,SECOND,b),observed(second,b),
                "hearthbound:fixture:real-create:"+second+":"+b.getUUID("Id")).newlyCredited())
            throw new IOException("Duplicate research credit after restart");
        org.apache.logging.log4j.LogManager.getLogger().info(
                "HEARTHBOUND_TWO_CITIZEN_REAL_CREDITS_RESTART_PASS citizenA={} citizenB={} balances=1,1",
                FIRST,SECOND);
    }
}
