package dev.hearthbound.mixin;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import dev.hearthbound.integration.MillstoneMutationAudit;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Observes the synchronous Create process() mutation window without modifying results. */
@Mixin(value = MillstoneBlockEntity.class, remap = false)
public abstract class MillstoneProcessMixin {
    @Unique private MillstoneMutationAudit.Snapshot hearthbound$before;

    @Inject(method = "process", at = @At("HEAD"), remap = false)
    private void hearthbound$beforeProcess(CallbackInfo ci) {
        hearthbound$before = MillstoneMutationAudit.before((MillstoneBlockEntity) (Object) this);
    }

    @Inject(method = "process", at = @At("RETURN"), remap = false)
    private void hearthbound$afterProcess(CallbackInfo ci) {
        try {
            MillstoneMutationAudit.after((MillstoneBlockEntity) (Object) this, hearthbound$before,
                    ((MillstoneRecipeAccessor) this).hearthbound$getLastRecipe());
        } finally {
            hearthbound$before = null;
        }
    }
}
