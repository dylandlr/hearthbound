package dev.hearthbound.gametest;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.stream.Stream;
import net.minecraft.world.level.storage.LevelResource;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;

/**
 * Read-only second-JVM probe for the isolated hard-crash experiment.
 * The ordinary dev server does not run these assertions.
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class CitizenCrashRestartCheck {
    private CitizenCrashRestartCheck() {}
    private static long inspectionTicks;
    private static boolean inspected;

    @SubscribeEvent
    public static void onTick(TickEvent.ServerTickEvent event) {
        if(event.phase != TickEvent.Phase.END || inspected) return;
        if (!"isolated-citizen-crash-test".equals(
                System.getenv("HEARTHBOUND_FAULT_TEST_ACK"))
                || !"inspect_after_crash".equals(
                System.getenv("HEARTHBOUND_CITIZEN_RECOVERY_STAGE"))) return;
        if(++inspectionTicks < 80) return;
        inspected=true;
        var server = event.getServer();
        Path world = server.getWorldPath(LevelResource.ROOT);
        Path attempts = world.resolve("hearthbound-citizen-supply-attempts");
        Path orders = world.resolve("hearthbound-citizen-milling-workorders");
        try {
            long attemptCount = countIntents(attempts);
            long orderCount = countIntents(orders);
            if (attemptCount < 1 || orderCount < 1)
                throw new IOException("Crash world must retain both operation and attempt journals");
            String requested=System.getenv("HEARTHBOUND_CRASH_OPERATION");
            if(requested==null || requested.isBlank())
                throw new IOException("Missing crash operation identity");
            java.util.UUID operation;
            try { operation=java.util.UUID.fromString(requested); }
            catch(IllegalArgumentException malformed) {
                throw new IOException("Malformed crash operation UUID",malformed);
            }
            var journal=new dev.hearthbound.research.DurableOperationIntents(attempts);
            var exact=journal.pending(dev.hearthbound.integration.CitizenSupplyAttempt.key(operation))
                    .orElseThrow(() -> new IOException("Injected operation attempt not found after restart"));
            String[] fields=exact.evidence().split("\\|",-1);
            if(fields.length!=5 || !fields[0].equals(operation.toString())
                    || !fields[4].equals("wheat=1"))
                throw new IOException("Injected operation evidence differs after restart");
            LogManager.getLogger().info(
                    "HEARTHBOUND_CRASH_RESTART_EXACT_ATTEMPT_PASS operation={} citizen={} dimension={} mill={}",
                    operation,fields[1],fields[2],fields[3]);
            java.util.UUID citizen;
            net.minecraft.core.BlockPos millPosition;
            try {
                citizen=java.util.UUID.fromString(fields[1]);
                millPosition=net.minecraft.core.BlockPos.of(Long.parseLong(fields[3]));
            } catch(IllegalArgumentException malformed) {
                throw new IOException("Invalid citizen or mill position in crash journal",malformed);
            }
            var level=server.getLevel(net.minecraft.resources.ResourceKey.create(
                    net.minecraft.core.registries.Registries.DIMENSION,
                    new net.minecraft.resources.ResourceLocation(fields[2])));
            if(level==null) throw new IOException("Crash operation dimension missing after restart");
            level.getChunkAt(millPosition);
            var machine=level.getBlockEntity(millPosition);
            if(!(machine instanceof com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity mill))
                throw new IOException("Real Create millstone missing after crash restart");
            var stack=mill.inputInv.getStackInSlot(0);
            // The crash hook fires before inventory mutation. Baseline fixtures
            // must yield an empty input for this specific new operation.
            if(!stack.isEmpty())
                throw new IOException("Unexpected Create input after pre-mutation hard crash");
            // Resolve the original villager; do not synthesize a replacement
            // when a hard crash caused entity data to be lost.
            for(int dx=-2;dx<=2;dx++) for(int dz=-2;dz<=2;dz++)
                level.getChunkAt(millPosition.offset(dx*16,0,dz*16));
            var villager=dev.hearthbound.integration.CitizenEmbodiment.find(level,citizen);
            if(villager==null)
                throw new IOException("Interrupted citizen entity absent after hard-crash restart");
            var citizenData=villager.getPersistentData();
            if(citizenData.getInt("HearthboundWheat")!=2
                    || citizenData.hasUUID("HearthboundLastSupplyOperation")
                    && operation.equals(citizenData.getUUID("HearthboundLastSupplyOperation")))
                throw new IOException("Pre-mutation citizen wheat or receipt inconsistent on restart");
            LogManager.getLogger().info(
                    "HEARTHBOUND_CRASH_RESTART_CITIZEN_PASS operation={} citizen={} wheat=2 receiptAbsent=true",
                    operation,citizen);
            var registered=dev.hearthbound.integration.CitizenRegistrySavedData.get(server).snapshot()
                    .stream().filter(item -> item.id().equals(citizen)).findFirst();
            if(registered.isPresent() && "IDLE".equals(registered.get().task()))
                throw new IOException("Interrupted citizen work cannot be marked complete");
            LogManager.getLogger().info(
                    "HEARTHBOUND_CRASH_RESTART_MACHINE_PASS operation={} mill={} inputEmpty=true citizenCompleted=false",
                    operation,millPosition);
            // No task mutation or inventory supply is permitted by this probe.
            LogManager.getLogger().info(
                    "HEARTHBOUND_CRASH_RESTART_JOURNALS_PASS attempts={} orders={} replayed=false",
                    attemptCount, orderCount);
            server.halt(false);
        } catch (IOException failure) {
            throw new IllegalStateException("Cannot inspect actual persisted crash world", failure);
        }
    }
    private static long countIntents(Path dir) throws IOException {
        if (!Files.isDirectory(dir)) throw new IOException("Missing journal directory: " + dir);
        try (Stream<Path> paths = Files.list(dir)) {
            return paths.filter(p -> p.getFileName().toString().endsWith(".intent"))
                    .count();
        }
    }
}
