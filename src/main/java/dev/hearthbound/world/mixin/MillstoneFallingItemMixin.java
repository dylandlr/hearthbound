package dev.hearthbound.world.mixin;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlock;
import dev.hearthbound.world.MillReservations;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.level.BlockGetter;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * Explicit physical world-item ingress guard.
 *
 * Create's MillstoneBlock.updateEntityAfterFallOn can feed wheat falling on
 * the mill directly. For reserved research mills, intercept before the Create
 * method (and before item mutation or entity discard).
 */
@Mixin(value = MillstoneBlock.class, remap = false)
public abstract class MillstoneFallingItemMixin {
    @Inject(method = "updateEntityAfterFallOn", at = @At("HEAD"), cancellable = true)
    private void hearthbound$guardFallingItem(BlockGetter world, Entity entity, CallbackInfo ci) {
        if (!(entity instanceof ItemEntity)) return;
        if (!(entity.level() instanceof ServerLevel level)) return;
        // Create resolves the millstone at the entity block position or one below.
        BlockPos here = entity.blockPosition();
        if (MillReservations.held(level, here) ||
                MillReservations.held(level, here.below())) {
            ci.cancel(); // The item remains a physical entity, unchanged.
        }
    }
}
