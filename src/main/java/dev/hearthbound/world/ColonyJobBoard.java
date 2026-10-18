package dev.hearthbound.world;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;

/**
 * Server-observed work offers for a colony stockpile.
 * This is a view, not an allocator: SableHauling.assign and HaulClaims
 * remain authoritative when a citizen actually accepts an offer.
 */
public final class ColonyJobBoard {
    public record HaulOffer(BlockPos source, BlockPos destination, UUID claimedBy, double distanceSquared) {
        public boolean available() { return claimedBy == null; }
    }

    private ColonyJobBoard() {}

    /** Bounded read-only scan. No chunk loading, item transfers or new claims. */
    public static List<HaulOffer> observe(ServerLevel level, BlockPos origin, BlockPos stockpile) {
        if (!level.hasChunkAt(stockpile)) return List.of();
        List<HaulOffer> result = new ArrayList<>();
        for (BlockPos pos : BlockPos.betweenClosed(
                origin.offset(-8, -2, -8), origin.offset(8, 2, 8))) {
            if (pos.equals(stockpile) || !level.hasChunkAt(pos)) continue;
            if (!SableHauling.hasAvailableWheat(level, pos)) continue;
            result.add(new HaulOffer(pos.immutable(), stockpile, HaulClaims.owner(level, pos),
                    pos.distSqr(origin)));
        }
        result.sort(Comparator.comparingDouble(HaulOffer::distanceSquared)
                .thenComparingLong(o -> o.source().asLong()));
        return List.copyOf(result);
    }

    public static String inspect(ServerLevel level, BlockPos origin, BlockPos stockpile) {
        List<HaulOffer> offers = observe(level, origin, stockpile);
        long free = offers.stream().filter(HaulOffer::available).count();
        StringBuilder output = new StringBuilder("COLONY_BOARD wheat offers=")
                .append(offers.size()).append(" free=").append(free)
                .append(" claimed=").append(offers.size() - free);
        for (HaulOffer offer : offers) {
            output.append(" | source=").append(offer.source())
                    .append(" status=").append(offer.available() ? "FREE" : "CLAIMED")
                    .append(" destination=").append(offer.destination());
        }
        return output.toString();
    }
}
