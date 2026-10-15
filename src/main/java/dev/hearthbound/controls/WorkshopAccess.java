package dev.hearthbound.controls;

import java.util.UUID;

/** First successful assignment binds a supervisor; legacy active jobs stay operator-managed. */
public final class WorkshopAccess {
    private WorkshopAccess() {}
    public static boolean canManage(UUID supervisor, UUID player, boolean operator, boolean idle) {
        return operator || (supervisor == null ? idle : supervisor.equals(player));
    }
}
