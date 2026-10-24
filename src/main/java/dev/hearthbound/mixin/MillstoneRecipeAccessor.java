package dev.hearthbound.mixin;

import com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity;
import com.simibubi.create.content.kinetics.millstone.MillingRecipe;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Reads the recipe selected by Create's own millstone process() method. */
@Mixin(value = MillstoneBlockEntity.class, remap = false)
public interface MillstoneRecipeAccessor {
    @Accessor(value = "lastRecipe", remap = false)
    MillingRecipe hearthbound$getLastRecipe();
}
