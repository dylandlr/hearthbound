package dev.hearthbound.client;

import dev.hearthbound.controls.WorkshopAction;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Native Minecraft controls with a local draft and server-authoritative save. */
public final class WorkerOrderScreen extends Screen {
    private int left, top, panelWidth, panelHeight, ticks;
    private EditBox target;
    private final Button[] picks = new Button[4];
    private Button save, stop, resume;
    public WorkerOrderScreen() { super(Component.literal("First Mill workshop")); }

    @Override protected void init() {
        var d = ClientWorkshop.draft;
        if (d == null) { onClose(); return; }
        panelWidth = Math.min(340, width - 16); panelHeight = Math.min(280, height - 16);
        left = (width - panelWidth) / 2; top = (height - panelHeight) / 2;
        for (int i = 0; i < 4; i++) {
            final int slot = i;
            picks[i] = addRenderableWidget(Button.builder(Component.literal(ClientWorkshop.LABELS[i]), b -> ClientWorkshop.select(slot))
                    .bounds(left + 12, top + 40 + i * 22, 104, 20).build());
        }
        target = addRenderableWidget(new EditBox(font, left + 100, top + 132, 68, 20, Component.literal("Flour target")));
        target.setMaxLength(4); target.setFilter(s -> s.matches("[0-9]*")); target.setValue(d.target);
        target.setResponder(s -> { if (ClientWorkshop.draft != null) ClientWorkshop.draft.target = s; });
        resume = addRenderableWidget(Button.builder(Component.literal("Resume haul"), b -> ClientWorkshop.send(WorkshopAction.RESUME))
                .bounds(left + panelWidth - 112, top + 154, 100, 18).build());
        int small = (panelWidth - 100) / 2, by = top + panelHeight - 30;
        save = addRenderableWidget(Button.builder(Component.literal("Start order"), b -> ClientWorkshop.send(WorkshopAction.SAVE))
                .bounds(left + 12, by, small, 20).build());
        stop = addRenderableWidget(Button.builder(Component.literal("Stop order"), b -> ClientWorkshop.send(WorkshopAction.STOP))
                .bounds(left + 18 + small, by, small, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Close"), b -> onClose())
                .bounds(left + panelWidth - 76, by, 64, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Status"), b -> minecraft.setScreen(new WorkshopStatusScreen()))
                .bounds(left + panelWidth - 66, top + 7, 54, 18).build());
        ClientWorkshop.log("SCREEN x=" + left + " y=" + top + " width=" + panelWidth + " height=" + panelHeight + " draftTarget=" + d.target);
    }

    @Override public void tick() {
        if (!ClientWorkshop.validWorker()) { onClose(); return; }
        target.tick();
        if (++ticks % 20 == 0) ClientWorkshop.send(WorkshopAction.REFRESH);
    }

    @Override public void render(GuiGraphics gui, int mouseX, int mouseY, float partialTick) {
        var d = ClientWorkshop.draft; if (d == null || target == null) return;
        var s = d.snapshot; var view = s.worker().view();
        renderBackground(gui);
        gui.fill(left, top, left + panelWidth, top + panelHeight, 0xFA151B20);
        gui.fill(left, top, left + 3, top + panelHeight, s.canEdit() ? 0xFF75D8AE : 0xFFFFBD66);
        gui.drawString(font, font.plainSubstrByWidth(s.name() + " — First Mill", panelWidth - 90), left + 12, top + 10, 0xFFE7DFC5);
        gui.drawString(font, Component.translatable("hearthbound.activity." + view.activity()), left + 12, top + 25, 0xFFF4F4F4);
        for (int i = 0; i < 4; i++) {
            picks[i].active = s.canEdit() && (i == 3 ? d.ready() : !view.hasOrder()) && !(s.busy() && !view.hasOrder());
            String value = d.points[i] == null ? (i == 3 ? "Automatic" : "Not selected") : d.points[i].toShortString();
            gui.drawString(font, font.plainSubstrByWidth(value, panelWidth - 140), left + 124, top + 46 + i * 22,
                    d.points[i] == null && i < 3 ? 0xFFFFBD66 : 0xFFF4F4F4);
            if (mouseX >= left + 124 && mouseX <= left + panelWidth - 12 && mouseY >= top + 40 + i * 22 && mouseY <= top + 60 + i * 22)
                gui.renderTooltip(font, Component.literal(value), mouseX, mouseY);
        }
        target.setEditable(s.canEdit());
        gui.drawString(font, "Flour target", left + 12, top + 138, 0xFFF4F4F4);
        gui.drawString(font, "0 = no limit", left + 180, top + 138, 0xFFBBC7CB);
        String stock = view.stockedFlour() < 0 ? "Flour storage: unavailable" : "Flour stored: " + view.stockedFlour()
                + (view.targetFlour() > 0 ? " / " + view.targetFlour() : "");
        if (!view.hasOrder()) stock = s.busy() ? "Current haul is finishing" : "Ready to start a work order";
        gui.drawString(font, stock, left + 12, top + 158, 0xFFF4F4F4);
        String notice = !s.canEdit() ? "Read only: assigned to another supervisor or managed by the server."
                : d.amount() < 0 || d.amount() > 4096 ? "Choose a flour target from 0 to 4096."
                : !d.ready() ? "Choose the wheat barrel, millstone, and flour barrel." : d.notice;
        var lines = font.split(Component.literal(notice), panelWidth - 24);
        int count = Math.max(1, (panelHeight - 211) / 10);
        for (int i = 0; i < Math.min(count, lines.size()); i++) gui.drawString(font, lines.get(i), left + 12, top + 175 + i * 10, 0xFFFFBD66);
        if (!notice.isEmpty() && mouseX >= left && mouseX <= left + panelWidth && mouseY >= top + 175 && mouseY < top + panelHeight - 32)
            gui.renderTooltip(font, lines, mouseX, mouseY);
        save.setMessage(Component.literal(view.hasOrder() ? "Save changes" : "Start order"));
        save.active = s.canEdit() && d.ready() && d.amount() >= 0 && d.amount() <= 4096 && (!s.busy() || view.hasOrder());
        stop.active = s.canEdit() && view.hasOrder();
        resume.visible = s.busy() && view.activity().equals("paused");
        resume.active = s.canEdit() && resume.visible;
        super.render(gui, mouseX, mouseY, partialTick);
    }

    @Override public void onClose() { ClientWorkshop.close(); }
    @Override public boolean isPauseScreen() { return false; }
}
