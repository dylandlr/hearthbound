package dev.hearthbound.world.mixin;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.world.MillTransferGate;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Guards the actual Create Forge IItemHandler insertion implementation.
 * Does not intercept direct modifications to inputInv or NBT or belt behaviours.
 */
@Mixin(targets = "com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity$MillstoneInventoryHandler", remap = false)
public abstract class MillstoneInventoryHandlerMixin {
    @Shadow @Final private MillstoneBlockEntity this$0;

    @Inject(method = "insertItem", at = @At("HEAD"), cancellable = true)
    private void hearthbound$guardInsert(int slot, ItemStack stack, boolean simulate,
                                        CallbackInfoReturnable<ItemStack> cir) {
        if (!(this$0.getLevel() instanceof ServerLevel level)) return;
        if (!MillTransferGate.permitted(level, this$0.getBlockPos(), stack, simulate)) {
            cir.setReturnValue(stack);
        }
    }
}
