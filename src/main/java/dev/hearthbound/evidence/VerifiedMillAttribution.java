package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/** Pure Java boundary between verified Create receipt and durable attributed inbox. */
public final class VerifiedMillAttribution {
    private VerifiedMillAttribution() {}

    public record Proof(UUID world, UUID job, UUID citizen, String dimension,
                        long machinePos, long observedStartTick, long finishTick,
                        int wheatBefore, int wheatAfter, int flourBefore, int flourAfter,
                        boolean reservationValid, boolean tainted) {}

    public record Claim(String eventId, String citizenId, String jobId, String dimension,
                        String machine, long observedStartTick, long finishTick) {}

    /**
     * Rejects evidence lacking verified ownership or observed powered processing.
     * Does NOT grant rewards, unlock technology, or infer an experiment from inventory alone.
     */
    public static Claim validate(Proof p) {
        Objects.requireNonNull(p);
        if (p.world() == null || p.job() == null || p.citizen() == null
                || p.dimension() == null || p.dimension().isBlank()
                || !p.reservationValid() || p.tainted()
                || p.observedStartTick() < 0 || p.finishTick() <= p.observedStartTick()
                || p.wheatBefore() != 1 || p.wheatAfter() != 0
                || p.flourBefore() != 0 || p.flourAfter() <= 0)
            throw new IllegalArgumentException("unverified or ambiguous mill receipt");
        return new Claim("hearthbound:mill:v1:" + p.world() + ":" + p.dimension()
                + ":" + p.job(), p.citizen().toString(), p.job().toString(),
                p.dimension(), Long.toString(p.machinePos()),
                p.observedStartTick(), p.finishTick());
    }
}
