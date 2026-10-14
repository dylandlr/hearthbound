package dev.hearthbound.world;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;

/**
 * Main-thread only, per-level source-claim table.
 * Ephemeral: NOT a persisted transaction ledger or a replacement for crash recovery.
 */
public final class HaulClaims {
    private static final Map<ServerLevel, Map<Long, UUID>> CLAIMS = new WeakHashMap<>();

    private HaulClaims() {}

    public static boolean claim(ServerLevel level, BlockPos source, UUID citizenId) {
        Map<Long, UUID> claims = CLAIMS.computeIfAbsent(level, unused -> new HashMap<>());
        UUID incumbent = claims.putIfAbsent(source.asLong(), citizenId);
        return incumbent == null || incumbent.equals(citizenId);
    }

    public static void release(ServerLevel level, BlockPos source, UUID citizenId) {
        Map<Long, UUID> claims = CLAIMS.get(level);
        if (claims != null) claims.remove(source.asLong(), citizenId);
    }
}
