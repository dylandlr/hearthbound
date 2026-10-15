package dev.hearthbound.presentation;

/** Read-only presentation data. Never an inventory or a source of transferable items. */
public record WorkerView(boolean visible, String item, int cargo, String activity,
        boolean hasOrder, int stockedFlour, int targetFlour) {}
