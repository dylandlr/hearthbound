package dev.hearthbound.world;

import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/**
 * Explicit scope for the *actual* Sable inventory transfer on the server thread.
 * A simulation/preflight never grants permission to an outside inserter.
 * This gates Create's Forge item-handler route, not direct NBT/field mutation.
 */
public final class MillTransferGate {
    private record Authorization(ServerLevel level, long machine, UUID job,
                                 UUID citizen, boolean simulation) {}
    private static final ThreadLocal<Authorization> CURRENT = new ThreadLocal<>();

    private MillTransferGate() {}

    public static ItemStack insert(ServerLevel level, BlockPos pos, UUID job,
                                   UUID citizen, boolean simulation,
                                   java.util.function.Supplier<ItemStack> action) {
        if (CURRENT.get() != null)
            throw new IllegalStateException("Nested authorized mill insertion is forbidden");
        if (!MillReservations.matches(level, pos, job, citizen))
            throw new IllegalStateException("Missing valid mill reservation");
        CURRENT.set(new Authorization(level, pos.asLong(), job, citizen, simulation));
        try {
            return action.get();
        } finally {
            CURRENT.remove();
        }
    }

    public static boolean permitted(ServerLevel level, BlockPos pos, ItemStack stack,
                                    boolean simulation) {
        if (!MillReservations.held(level, pos)) return true;
        Authorization auth = CURRENT.get();
        return auth != null && auth.level() == level && auth.machine() == pos.asLong()
            && auth.simulation() == simulation
            && stack.is(Items.WHEAT) && stack.getCount() == 1
            && MillReservations.matches(level, pos, auth.job(), auth.citizen());
    }
}
