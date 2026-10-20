package dev.hearthbound.world.mixin;

import net.minecraft.client.renderer.LevelRenderer;
import net.minecraft.core.BlockPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;

/** Exposes client chunk mesh invalidation without changing any world block. */
@Mixin(LevelRenderer.class)
public interface TacticalChunkRebuildAccessor {
    @Invoker("setBlockDirty")
    void hearthbound$markBlockDirty(BlockPos position, boolean immediate);
}
