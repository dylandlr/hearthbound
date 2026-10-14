package dev.hearthbound.ai;

import java.util.Objects;
import static dev.hearthbound.ai.ColonyPolicy.*;

/**
 * Pure validation step. Must be called with a fresh server-side observation
 * immediately before Minecraft-side execution. It grants no world authority.
 */
public final class ActionGate {
    private ActionGate() {}

    public static boolean allowed(Observation current, Decision proposal) {
        Objects.requireNonNull(current, "current");
        Objects.requireNonNull(proposal, "proposal");
        return proposal.expectedVersion() == current.version()
            && !proposal.actionId().isBlank()
            && current.availableActions().stream()
                .anyMatch(a -> a.executable() && a.id().equals(proposal.actionId()));
    }
}
