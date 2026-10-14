package dev.hearthbound.jobs;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.phys.AABB;
import java.util.List;

/** Detects a saved in-flight haul after a complete Forge server restart.
 * The test stage is set up by HaulE2EProbe and uses entity/world NBT, never static state.
 */
public final class HaulRestartProbe {
    private HaulRestartProbe() {}

    public static int check(CommandSourceStack source) {
        ServerLevel level = source.getLevel();
        BlockPos spawn = level.getSharedSpawnPos();
        int top = level.getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                spawn.getX(), spawn.getZ());
        // The elevated CI platform may be above world terrain; locate test villager by tag.
        List<Villager> matches = level.getEntitiesOfClass(Villager.class,
                new AABB(spawn.getX() - 32, level.getMinBuildHeight(), spawn.getZ() - 32,
                        spawn.getX() + 32, level.getMaxBuildHeight(), spawn.getZ() + 32),
                v -> v.getTags().contains("hearthbound.restart.probe"));
        if (matches.size() != 1) return fail(source, "tagged_villager_count=" + matches.size());
        Villager sable = matches.get(0);
        var state = sable.getPersistentData();
        if (!state.contains("HearthboundHaul", 10)) return fail(source, "job_missing");
        var job = state.getCompound("HearthboundHaul");
        if (!"DELIVER".equals(job.getString("Phase")) || job.getInt("Cargo") != 4)
            return fail(source, "cargo_or_phase");
        BlockPos from = BlockPos.of(job.getLong("From"));
        BlockPos to = BlockPos.of(job.getLong("To"));
        if (!(level.getBlockEntity(from) instanceof BarrelBlockEntity input)
                || !(level.getBlockEntity(to) instanceof BarrelBlockEntity output))
            return fail(source, "barrels_missing");
        int wheatInSource = countWheat(input);
        int wheatInOutput = countWheat(output);
        if (wheatInSource != 4 || wheatInOutput != 0
                || wheatInSource + job.getInt("Cargo") + wheatInOutput != 8)
            return fail(source, "inventory_conservation");
        source.sendSuccess(() -> Component.literal("HB_RESTART_PASS source=4 cargo=4 dest=0"), true);
        return 1;
    }

    public static int unblock(CommandSourceStack source) {
        Villager sable = findRestartCitizen(source.getLevel());
        if (sable == null) return fail(source, "villager_missing");
        var job = sable.getPersistentData().getCompound("HearthboundHaul");
        if (!"DELIVER".equals(job.getString("Phase")) || job.getInt("Cargo") != 4)
            return fail(source, "cargo_missing");
        BlockPos to = BlockPos.of(job.getLong("To"));
        if (!(source.getLevel().getBlockEntity(to) instanceof BarrelBlockEntity output))
            return fail(source, "destination_missing");
        for (int slot = 0; slot < output.getContainerSize(); slot++)
            output.setItem(slot, ItemStack.EMPTY);
        output.setChanged();
        source.sendSuccess(() -> Component.literal("HB_RESTART_UNBLOCKED"), false);
        return 1;
    }

    public static int delivered(CommandSourceStack source) {
        Villager sable = findRestartCitizen(source.getLevel());
        if (sable == null) return fail(source, "villager_missing");
        var data = sable.getPersistentData();
        if (data.contains("HearthboundHaul", 10)) {
            source.sendSuccess(() -> Component.literal("HB_RESTART_PENDING"), false);
            return 1;
        }
        BlockPos from = getSourceFromCitizen(sable);
        if (from == null) return fail(source, "saved_source_missing");
        // Caller checks the exact world inventory using the source saved before job completion.
        source.sendSuccess(() -> Component.literal("HB_RESTART_DELIVERED"), false);
        return 1;
    }

    private static BlockPos getSourceFromCitizen(Villager citizen) {
        if (!citizen.getPersistentData().contains("HearthboundHaul", 10)) return null;
        return BlockPos.of(citizen.getPersistentData().getCompound("HearthboundHaul").getLong("From"));
    }

    private static Villager findRestartCitizen(ServerLevel level) {
        BlockPos spawn = level.getSharedSpawnPos();
        List<Villager> matches = level.getEntitiesOfClass(Villager.class,
                new AABB(spawn.getX() - 32, level.getMinBuildHeight(), spawn.getZ() - 32,
                        spawn.getX() + 32, level.getMaxBuildHeight(), spawn.getZ() + 32),
                v -> v.getTags().contains("hearthbound.restart.probe"));
        return matches.size() == 1 ? matches.get(0) : null;
    }

    private static int countWheat(BarrelBlockEntity barrel) {
        int count = 0;
        for (int i = 0; i < barrel.getContainerSize(); i++) {
            ItemStack stack = barrel.getItem(i);
            if (stack.is(Items.WHEAT)) count += stack.getCount();
        }
        return count;
    }

    private static int fail(CommandSourceStack source, String detail) {
        source.sendFailure(Component.literal("HB_RESTART_FAIL " + detail));
        return 0;
    }
}
