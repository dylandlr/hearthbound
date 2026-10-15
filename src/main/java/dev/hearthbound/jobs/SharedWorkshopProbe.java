package dev.hearthbound.jobs;

import java.util.UUID;
import dev.hearthbound.HearthboundMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.phys.AABB;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Disposable real-world fixture: shared Create mill, save/restart and retained cargo. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class SharedWorkshopProbe {
    private static final BlockPos WHEAT = new BlockPos(132, 100, 134);
    private static final BlockPos MILL = new BlockPos(140, 100, 134);
    private static final BlockPos FLOUR = new BlockPos(148, 100, 134);
    private static final UUID OWNER = UUID.fromString("bab8c0a1-4c12-45c4-b128-fc048a597960");
    private static final UUID MEMBER = UUID.fromString("f22c9bb1-d3d8-4efd-9f78-46407fb4ae12");
    private SharedWorkshopProbe() {}

    public static int start(CommandSourceStack source) {
        var level = source.getLevel();
        for (int x = 128; x <= 153; x++) for (int z = 128; z <= 140; z++)
            level.setBlockAndUpdate(new BlockPos(x, 99, z), Blocks.STONE.defaultBlockState());
        level.setBlockAndUpdate(WHEAT, Blocks.BARREL.defaultBlockState());
        level.setBlockAndUpdate(FLOUR, Blocks.BARREL.defaultBlockState());
        level.setBlockAndUpdate(MILL, net.minecraft.core.registries.BuiltInRegistries.BLOCK.get(
                new net.minecraft.resources.ResourceLocation("create", "millstone")).defaultBlockState());
        level.setBlockAndUpdate(MILL.below(), net.minecraft.core.registries.BuiltInRegistries.BLOCK.get(
                new net.minecraft.resources.ResourceLocation("create", "creative_motor")).defaultBlockState()
                .setValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.FACING, net.minecraft.core.Direction.UP));
        ((BarrelBlockEntity) level.getBlockEntity(WHEAT)).setItem(0, new ItemStack(Items.WHEAT, 8));
        var a = spawn(level, "a", 130.5, 132.5);
        var b = spawn(level, "b", 130.5, 136.5);
        String error = FirstMillWorkOrder.configureFor(a, WHEAT, MILL, FLOUR, null, 2, OWNER, false);
        if (!error.isEmpty()) return fail(source, error);
        var before = b.getPersistentData().copy();
        error = FirstMillWorkOrder.configureFor(b, WHEAT, MILL, FLOUR, null, 2, UUID.randomUUID(), false);
        if (error.isEmpty() || !before.equals(b.getPersistentData())) return fail(source, "foreign_owner_mutated_worker");
        var registry = WorkshopRegistry.get(level);
        if (!registry.share(MILL, OWNER, MEMBER, false)) return fail(source, "share_grant");
        error = FirstMillWorkOrder.configureFor(b, WHEAT, MILL, FLOUR, null, 2, MEMBER, false);
        if (!error.isEmpty() || !MEMBER.equals(b.getPersistentData().getCompound("HearthboundMillOrder").getUUID("WorkshopManager")))
            return fail(source, "shared_member_order");
        // A discarded empty worker releases its lease without touching stock.
        var temporary = spawn(level, "temporary", 129.5, 130.5);
        if (!BarrelHaulController.assignCitizen(temporary, WHEAT, MILL, 1)) return fail(source, "temporary_assignment");
        temporary.discard();
        if (registry.holder(MILL) != null) return fail(source, "discarded_lease");
        if (!BarrelHaulController.assignCitizen(a, WHEAT, MILL, 4)
                || BarrelHaulController.assignFlourCitizen(b, MILL, FLOUR, 1)
                || b.getPersistentData().contains("HearthboundHaul", 10)
                || registry.holder(FLOUR) != null) return fail(source, "contended_or_partial_assignment");
        a.getPersistentData().putBoolean("HearthboundSharedArm", true);
        source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_STARTED ownership_denial shared_grant atomic_pair discard_release"), false);
        return 1;
    }

    private static Villager spawn(ServerLevel level, String role, double x, double z) {
        var worker = EntityType.VILLAGER.create(level);
        if (worker == null) throw new IllegalStateException("No test villager");
        worker.moveTo(x, 100, z, 0, 0); worker.setPersistenceRequired();
        worker.addTag("hearthbound.sable"); worker.addTag("hearthbound.shared." + role);
        worker.setCustomName(Component.literal("Sable [shared " + role + "]"));
        level.addFreshEntity(worker); return worker;
    }

    private static Villager find(ServerLevel level, String role) {
        var found = level.getEntitiesOfClass(Villager.class, new AABB(126, 98, 126, 156, 105, 144),
                v -> v.getTags().contains("hearthbound.shared." + role));
        return found.size() == 1 ? found.get(0) : null;
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void observe(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager worker) || !(worker.level() instanceof ServerLevel)) return;
        var data = worker.getPersistentData();
        if (!data.getBoolean("HearthboundSharedArm")) return;
        var job = data.getCompound("HearthboundHaul");
        if (job.getInt("Cargo") == 4 && job.getString("Phase").equals("DELIVER")) {
            FirstMillWorkOrder.stopWorker(worker);
            job.putBoolean("Paused", true);
            data.remove("HearthboundSharedArm"); data.putBoolean("HearthboundSharedStaged", true);
        }
    }

    public static int check(CommandSourceStack source, boolean restarted) {
        var level = source.getLevel(); var a = find(level, "a"); var b = find(level, "b");
        if (a == null || b == null) return fail(source, "workers_missing");
        var data = a.getPersistentData(); var job = data.getCompound("HearthboundHaul");
        if (!data.getBoolean("HearthboundSharedStaged")) {
            source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_PENDING"), false); return 1;
        }
        var registry = WorkshopRegistry.get(level); var lease = registry.holder(MILL);
        if (job.getInt("Cargo") != 4 || !job.getBoolean("Paused") || !job.getString("Phase").equals("DELIVER")
                || data.contains("HearthboundMillOrder", 10) || b.getPersistentData().contains("HearthboundHaul", 10)
                || !b.getPersistentData().contains("HearthboundMillOrder", 10)
                || lease == null || !lease.worker().equals(a.getUUID()) || !lease.job().equals(job.getString("JobId"))
                || registry.holder(WHEAT) == null || registry.holder(FLOUR) != null
                || !OWNER.equals(registry.owner(MILL)) || wheat(level) != 4)
            return fail(source, "cargo_owner_or_lease");
        var workerBefore = b.getPersistentData().copy(); var registryBefore = registry.save(new CompoundTag());
        var status = dev.hearthbound.controls.WorkshopStatus.inspect(b, OWNER, false, WHEAT, MILL, FLOUR);
        var shared = dev.hearthbound.controls.WorkshopStatus.inspect(b, MEMBER, false, WHEAT, MILL, FLOUR);
        var denied = dev.hearthbound.controls.WorkshopStatus.inspect(b, UUID.randomUUID(), false, WHEAT, MILL, FLOUR);
        if (status.access() != dev.hearthbound.controls.WorkshopStatus.Access.OWNER
                || shared.access() != dev.hearthbound.controls.WorkshopStatus.Access.SHARED
                || !registry.isShared(MILL, MEMBER) || registry.sharedWith(MILL).size() != 1
                || denied.access() != dev.hearthbound.controls.WorkshopStatus.Access.DENIED
                || status.mill().state() != dev.hearthbound.controls.WorkshopStatus.State.OTHER
                || !status.mill().paused() || !status.mill().holder().equals(a.getName().getString())
                || (!restarted && (!status.mill().queued() || status.mill().waiting() < 1))
                || !workerBefore.equals(b.getPersistentData()) || !registryBefore.equals(registry.save(new CompoundTag())))
            return fail(source, "readonly_status_inconsistent");
        source.sendSuccess(() -> Component.literal("HB_WORKSHOP_STATUS_SERVER_PASS owner shared denied other_holder paused queue readonly"), false);
        if (restarted && !registry.wasRestored(a.getUUID(), job.getString("JobId"))) return fail(source, "lease_not_loaded_from_disk");
        if (WorkshopRegistry.releaseOwnership(source, MILL) != 0) return fail(source, "released_busy_workshop");
        source.sendSuccess(() -> Component.literal(restarted ? "HB_SHARED_WORKSHOP_RESTART_PASS owner lease cargo=4 source=4"
                : "HB_SHARED_WORKSHOP_STAGED stop_preserved_cargo_and_lease shared_persisted no_competing_extraction"), false);
        return 1;
    }

    public static int resume(CommandSourceStack source) {
        var a = find(source.getLevel(), "a");
        if (a == null) return fail(source, "worker_missing");
        a.getPersistentData().getCompound("HearthboundHaul").putBoolean("Paused", false);
        source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_RESUMED"), false); return 1;
    }

    public static int done(CommandSourceStack source) {
        var level = source.getLevel(); var a = find(level, "a"); var b = find(level, "b");
        if (a == null || b == null) return fail(source, "workers_missing");
        var output = (BarrelBlockEntity) level.getBlockEntity(FLOUR); int flour = 0;
        for (int slot = 0; slot < output.getContainerSize(); slot++) {
            var stack = output.getItem(slot);
            if (net.minecraft.core.registries.BuiltInRegistries.ITEM.getKey(stack.getItem()).toString().equals("create:wheat_flour"))
                flour += stack.getCount();
        }
        var registry = WorkshopRegistry.get(level);
        if (flour < 2 || a.getPersistentData().contains("HearthboundHaul", 10)
                || b.getPersistentData().contains("HearthboundHaul", 10)) {
            final int stocked = flour;
            source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_PENDING flour=" + stocked), false); return 1;
        }
        var bData = b.getPersistentData(); var bOrder = bData.getCompound("HearthboundMillOrder");
        if (!bData.getBoolean("HearthboundSharedRevoked")) {
            if (!bOrder.getString("State").equals("TARGET_REACHED")) {
                source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_PENDING target_state"), false); return 1;
            }
            if (wheat(level) != 4 || flour != 2 || registry.lease(a.getUUID()) != null
                    || registry.lease(b.getUUID()) != null || !registry.revoke(MILL, OWNER, MEMBER, false))
                return fail(source, "revoke_stage");
            bOrder.putInt("TargetFlour", 3); bOrder.putString("State", "WAITING");
            bData.putBoolean("HearthboundSharedRevoked", true);
            source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_REVOKED active_work_complete new_work_pending"), false);
            return 1;
        }
        if (!bOrder.getString("State").equals("WORKSHOP_ACCESS_DENIED")) {
            source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_PENDING revoked_access_check"), false); return 1;
        }
        if (wheat(level) != 4 || flour != 2 || registry.lease(a.getUUID()) != null || registry.lease(b.getUUID()) != null
                || !OWNER.equals(registry.owner(MILL)) || registry.isShared(MILL, MEMBER)
                || registry.canUse(MILL, MEMBER, false)) return fail(source, "final_inventory_lease_or_access");
        var status = dev.hearthbound.controls.WorkshopStatus.inspect(b, MEMBER, false, WHEAT, MILL, FLOUR);
        if (status.access() != dev.hearthbound.controls.WorkshopStatus.Access.DENIED
                || status.mill().state() != dev.hearthbound.controls.WorkshopStatus.State.FREE
                || status.mill().waiting() != 0 || status.mill().queued()) return fail(source, "finished_status_not_free");
        source.sendSuccess(() -> Component.literal("HB_SHARED_WORKSHOP_PASS two_workers source=4 flour=2 cargo=0 leases=free owner_retained shared_revoked_new_work_denied"), false);
        return 1;
    }

    private static int wheat(ServerLevel level) {
        var barrel = (BarrelBlockEntity) level.getBlockEntity(WHEAT); int total = 0;
        for (int i = 0; i < barrel.getContainerSize(); i++) if (barrel.getItem(i).is(Items.WHEAT)) total += barrel.getItem(i).getCount();
        return total;
    }
    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_SHARED_WORKSHOP_FAIL " + reason)); return 0;
    }
}
