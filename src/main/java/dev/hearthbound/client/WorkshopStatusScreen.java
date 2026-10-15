package dev.hearthbound.client;

import dev.hearthbound.controls.WorkshopAction;
import dev.hearthbound.controls.WorkshopStatus;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Live public workshop inspection. Returning never saves or discards the editor draft. */
public final class WorkshopStatusScreen extends Screen {
    private int left, top, panelWidth, panelHeight, ticks;
    private String lastWitness = "", hovered;
    public WorkshopStatusScreen() { super(Component.literal("Workshop status")); }

    @Override protected void init() {
        panelWidth = Math.min(340, width - 16); panelHeight = Math.min(252, height - 16);
        left = (width - panelWidth) / 2; top = (height - panelHeight) / 2;
        addRenderableWidget(Button.builder(Component.literal("Back to setup"), b -> onClose())
                .bounds(left + 12, top + panelHeight - 30, panelWidth - 24, 20).build());
        ClientWorkshop.log("STATUS_SCREEN x=" + left + " y=" + top + " width=" + panelWidth + " height=" + panelHeight);
        ClientWorkshop.send(WorkshopAction.REFRESH);
    }

    @Override public void tick() {
        if (!ClientWorkshop.validWorker()) { ClientWorkshop.close(); return; }
        if (++ticks % 20 == 0) ClientWorkshop.send(WorkshopAction.REFRESH);
    }

    private void line(GuiGraphics gui, String text, int y, int color, int mouseX, int mouseY) {
        gui.drawString(font, font.plainSubstrByWidth(text, panelWidth - 24), left + 12, top + y, color);
        if (mouseX >= left + 10 && mouseX < left + panelWidth - 10 && mouseY >= top + y && mouseY < top + y + 10)
            hovered = text;
    }

    @Override public void render(GuiGraphics gui, int mouseX, int mouseY, float partialTick) {
        if (ClientWorkshop.draft == null) return;
        var status = ClientWorkshop.draft.snapshot.status();
        hovered = null;
        renderBackground(gui);
        gui.fill(left, top, left + panelWidth, top + panelHeight, 0xFA151B20);
        gui.fill(left, top, left + 3, top + panelHeight, 0xFF75D8AE);
        line(gui, "Workshop status", 10, 0xFFE7DFC5, mouseX, mouseY);
        line(gui, "Mill owner: " + status.owner(), 31, 0xFFF4F4F4, mouseX, mouseY);
        line(gui, status.accessDescription(), 45, status.access() == WorkshopStatus.Access.DENIED
                ? 0xFFFFBD66 : 0xFFBBC7CB, mouseX, mouseY);
        var stations = new WorkshopStatus.Station[] {status.wheat(), status.mill(), status.flour()};
        var labels = new String[] {"Wheat barrel", "Millstone", "Flour barrel"};
        for (int i = 0; i < stations.length; i++) {
            var station = stations[i]; int row = 66 + i * 38;
            gui.fill(left + 8, top + row - 3, left + panelWidth - 8, top + row + 34, 0xFF202B31);
            line(gui, labels[i] + (station.point() == null ? "" : " · " + station.point().toShortString()),
                    row, 0xFFE7DFC5, mouseX, mouseY);
            line(gui, station.description(), row + 11, station.state() == WorkshopStatus.State.FREE
                    ? 0xFF75D8AE : 0xFFF4F4F4, mouseX, mouseY);
            line(gui, station.queueDescription(), row + 22, station.queued() ? 0xFFFFBD66 : 0xFFBBC7CB, mouseX, mouseY);
        }
        line(gui, "Paused or absent workers keep their reservation.", 183, 0xFFBBC7CB, mouseX, mouseY);
        String witness = "owner=" + status.owner() + " access=" + status.access()
                + " mill=" + status.mill().state() + " waiting=" + status.mill().waiting()
                + " queued=" + status.mill().queued() + " paused=" + status.mill().paused();
        if (!lastWitness.equals(witness)) {
            ClientWorkshop.log("STATUS_RENDER " + witness); lastWitness = witness;
        }
        super.render(gui, mouseX, mouseY, partialTick);
        if (hovered != null) gui.renderTooltip(font, Component.literal(hovered), mouseX, mouseY);
    }

    @Override public void onClose() {
        if (ClientWorkshop.draft == null) ClientWorkshop.close();
        else minecraft.setScreen(new WorkerOrderScreen());
    }
    @Override public boolean isPauseScreen() { return false; }
}
