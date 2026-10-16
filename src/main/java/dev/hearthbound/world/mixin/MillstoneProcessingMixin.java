package dev.hearthbound.world.mixin;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.world.MillProcessReceipts;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.Items;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Callback around the real Create process(), not an inventory polling guess. */
@Mixin(value = MillstoneBlockEntity.class, remap = false)
public abstract class MillstoneProcessingMixin {
    @Unique private int hearthbound$beforeWheat;
    @Unique private int hearthbound$beforeFlour;

    @Unique private int hearthbound$countFlour(MillstoneBlockEntity mill) {
        int count=0;
        for(int i=0;i<mill.outputInv.getSlots();i++) {
            var stack=mill.outputInv.getStackInSlot(i);
            if (new ResourceLocation("create","wheat_flour")
                .equals(BuiltInRegistries.ITEM.getKey(stack.getItem()))) count+=stack.getCount();
        }
        return count;
    }

    @Inject(method = "process", at = @At("HEAD"))
    private void hearthbound$beforeProcess(CallbackInfo ci) {
        MillstoneBlockEntity mill=(MillstoneBlockEntity)(Object)this;
        var input=mill.inputInv.getStackInSlot(0);
        hearthbound$beforeWheat=input.is(Items.WHEAT) ? input.getCount() : 0;
        hearthbound$beforeFlour=hearthbound$countFlour(mill);
    }

    @Inject(method = "process", at = @At("TAIL"))
    private void hearthbound$afterProcess(CallbackInfo ci) {
        MillstoneBlockEntity mill=(MillstoneBlockEntity)(Object)this;
        if (!(mill.getLevel() instanceof ServerLevel level)) return;
        var input=mill.inputInv.getStackInSlot(0);
        int afterWheat=input.is(Items.WHEAT)?input.getCount():0;
        MillProcessReceipts.record(level,mill.getBlockPos(),hearthbound$beforeWheat,
            afterWheat,hearthbound$beforeFlour,hearthbound$countFlour(mill));
    }
}
