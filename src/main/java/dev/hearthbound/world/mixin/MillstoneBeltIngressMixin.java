package dev.hearthbound.world.mixin;

import com.simibubi.create.content.kinetics.belt.behaviour.DirectBeltInputBehaviour;
import com.simibubi.create.content.kinetics.belt.transport.TransportedItemStack;
import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.world.MillReservations;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Fail closed at Create's actual direct-belt behaviour. Covers any caller
 * invoking handleInsertion(TransportedItemStack,...), before callbacks run.
 * Only reserved millstones are changed; other Create belt targets untouched.
 */
@Mixin(value = DirectBeltInputBehaviour.class, remap = false)
public abstract class MillstoneBeltIngressMixin {
    @Inject(method = "handleInsertion(Lcom/simibubi/create/content/kinetics/belt/transport/TransportedItemStack;Lnet/minecraft/core/Direction;Z)Lnet/minecraft/world/item/ItemStack;",
        at = @At("HEAD"), cancellable = true)
    private void hearthbound$rejectReservedMillBelt(TransportedItemStack transported,
            Direction side, boolean simulate, CallbackInfoReturnable<ItemStack> cir) {
        DirectBeltInputBehaviour behavior = (DirectBeltInputBehaviour) (Object) this;
        if (!(behavior.blockEntity instanceof MillstoneBlockEntity mill)) return;
        if (!(mill.getLevel() instanceof ServerLevel level)) return;
        if (MillReservations.held(level, mill.getBlockPos())) {
            cir.setReturnValue(transported.stack.copy());
        }
    }
}
