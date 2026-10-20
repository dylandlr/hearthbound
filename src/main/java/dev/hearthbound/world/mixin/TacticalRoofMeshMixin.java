package dev.hearthbound.world.mixin;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import dev.hearthbound.client.TacticalRoofFilter;
import net.minecraft.client.renderer.block.BlockRenderDispatcher;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.BlockAndTintGetter;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Suppresses only explicitly approved blocks while assembling client meshes. */
@Mixin(BlockRenderDispatcher.class)
public abstract class TacticalRoofMeshMixin {
    @Inject(method = "renderBatched", at = @At("HEAD"), cancellable = true)
    private void hearthbound$cutaway(BlockState state, BlockPos pos,
            BlockAndTintGetter level, PoseStack pose, VertexConsumer consumer,
            boolean cull, RandomSource random, CallbackInfo ci) {
        if (TacticalRoofFilter.suppress(pos)) ci.cancel();
    }
}
