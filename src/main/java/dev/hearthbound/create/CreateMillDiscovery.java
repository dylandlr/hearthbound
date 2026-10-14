package dev.hearthbound.create;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.minecraftforge.fml.ModList;

/**
 * Optional Create discovery bridge: never guesses that a block is processing
 * or that a millstone is powered. No hard Create runtime dependency.
 */
public final class CreateMillDiscovery {
    private static final ResourceLocation MILLSTONE = new ResourceLocation("create", "millstone");
    private static final ResourceLocation WHEAT_FLOUR = new ResourceLocation("create", "wheat_flour");

    private CreateMillDiscovery() {}

    public static int inspect(CommandSourceStack source, BlockPos position) {
        if (!ModList.get().isLoaded("create")) {
            source.sendFailure(Component.literal("Hearthbound: Create is not installed; install a compatible Create build."));
            return 0;
        }
        Block mill = BuiltInRegistries.BLOCK.getOptional(MILLSTONE).orElse(null);
        Item flour = BuiltInRegistries.ITEM.getOptional(WHEAT_FLOUR).orElse(null);
        if (mill == null || flour == null) {
            source.sendFailure(Component.literal("Hearthbound: Create registries missing millstone or wheat flour."));
            return 0;
        }
        if (!source.getLevel().hasChunkAt(position)) {
            source.sendFailure(Component.literal("Hearthbound: target chunk is not loaded."));
            return 0;
        }
        if (!source.getLevel().getBlockState(position).is(mill)) {
            source.sendFailure(Component.literal("Hearthbound: selected position is not a Create millstone."));
            return 0;
        }
        source.sendSuccess(() -> Component.literal("HEARTHBOUND_CREATE_MILL_FOUND at "
                + position.toShortString() + "; mechanical power and recipe output NOT YET VERIFIED"), false);
        return 1;
    }

    public static int status(CommandSourceStack source) {
        boolean installed = ModList.get().isLoaded("create");
        boolean millRegistered = BuiltInRegistries.BLOCK.containsKey(MILLSTONE);
        boolean flourRegistered = BuiltInRegistries.ITEM.containsKey(WHEAT_FLOUR);
        source.sendSuccess(() -> Component.literal("Hearthbound Create bridge: installed=" + installed
                + " millstoneRegistered=" + millRegistered + " wheatFlourRegistered=" + flourRegistered
                + " (discovery only; no automation yet)"), false);
        return 1;
    }
}
