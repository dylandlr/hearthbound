package dev.hearthbound.client;

import dev.hearthbound.controls.WorkshopAction;
import dev.hearthbound.controls.WorkshopStatus;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;

/** Owner and operator access controls backed by server-authored player identities. */
public final class WorkshopSharingScreen extends Screen {
    private int left, top, panelWidth, panelHeight, ticks, selected;
    private Button previous, next, grant, revoke, release;
    private String lastWitness = "";

    public WorkshopSharingScreen() { super(Component.literal("Workshop access")); }

    @Override protected void init() {
        panelWidth = Math.min(340, width - 16); panelHeight = Math.min(220, height - 16);
        left = (width - panelWidth) / 2; top = (height - panelHeight) / 2;
        previous = addRenderableWidget(Button.builder(Component.literal("<"), b -> move(-1))
                .bounds(left + 12, top + 72, 38, 20).build());
        next = addRenderableWidget(Button.builder(Component.literal(">"), b -> move(1))
                .bounds(left + 54, top + 72, 38, 20).build());
        grant = addRenderableWidget(Button.builder(Component.literal("Share"), b -> act(WorkshopAction.SHARE))
                .bounds(left + 100, top + 72, 72, 20).build());
        revoke = addRenderableWidget(Button.builder(Component.literal("Revoke"), b -> act(WorkshopAction.REVOKE))
                .bounds(left + 178, top + 72, 72, 20).build());
        release = addRenderableWidget(Button.builder(Component.literal("Release ownership"),
                b -> ClientWorkshop.sendAccess(WorkshopAction.RELEASE, null))
                .bounds(left + 12, top + 104, panelWidth - 24, 20).build());
        addRenderableWidget(Button.builder(Component.literal("Back to status"), b -> onClose())
                .bounds(left + 12, top + panelHeight - 30, panelWidth - 24, 20).build());
        ClientWorkshop.log("SHARING_SCREEN x=" + left + " y=" + top + " width=" + panelWidth + " height=" + panelHeight);
        ClientWorkshop.send(WorkshopAction.REFRESH);
    }

    private java.util.List<WorkshopStatus.Person> people() {
        return ClientWorkshop.draft == null ? java.util.List.of() : ClientWorkshop.draft.snapshot.status().people();
    }

    private WorkshopStatus.Person person() {
        var people = people();
        if (people.isEmpty()) return null;
        selected = Math.max(0, Math.min(selected, people.size() - 1));
        return people.get(selected);
    }

    private void move(int delta) {
        int size = people().size();
        if (size > 0) selected = Math.floorMod(selected + delta, size);
    }

    private void act(int action) {
        var person = person();
        if (person != null) ClientWorkshop.sendAccess(action, person.player());
    }

    @Override public void tick() {
        if (!ClientWorkshop.validWorker()) { ClientWorkshop.close(); return; }
        if (++ticks % 20 == 0) ClientWorkshop.send(WorkshopAction.REFRESH);
    }

    @Override public void render(GuiGraphics gui, int mouseX, int mouseY, float partialTick) {
        if (ClientWorkshop.draft == null) return;
        var status = ClientWorkshop.draft.snapshot.status();
        var person = person();
        renderBackground(gui);
        gui.fill(left, top, left + panelWidth, top + panelHeight, 0xFA151B20);
        gui.fill(left, top, left + 3, top + panelHeight, status.canManage() ? 0xFF75D8AE : 0xFFFFBD66);
        gui.drawString(font, "Workshop access", left + 12, top + 10, 0xFFE7DFC5);
        gui.drawString(font, "Mill owner: " + status.owner(), left + 12, top + 30, 0xFFF4F4F4);
        gui.drawString(font, person == null ? "No other online players"
                : font.plainSubstrByWidth(person.name() + (person.shared() ? " · shared" : " · no access"), panelWidth - 24),
                left + 12, top + 52, person != null && person.shared() ? 0xFF75D8AE : 0xFFBBC7CB);
        previous.active = next.active = status.canManage() && people().size() > 1;
        grant.active = status.canManage() && person != null && person.online() && !person.shared();
        revoke.active = status.canManage() && person != null && person.shared();
        release.active = status.canRelease();
        String safety = status.canRelease() ? "Release is available: no haul reserves this mill."
                : "Release stays locked while a haul reserves this mill.";
        gui.drawString(font, font.plainSubstrByWidth(safety, panelWidth - 24), left + 12, top + 132, 0xFFBBC7CB);
        var notice = ClientWorkshop.draft.notice;
        if (!notice.isEmpty()) gui.drawString(font, font.plainSubstrByWidth(notice, panelWidth - 24),
                left + 12, top + 148, 0xFFFFBD66);
        String witness = "owner=" + status.owner() + " people=" + people().size() + " manage="
                + status.canManage() + " release=" + status.canRelease()
                + " selected=" + (person == null ? "none" : person.name() + "/" + person.shared() + "/" + person.online());
        if (!lastWitness.equals(witness)) {
            ClientWorkshop.log("SHARING_RENDER " + witness); lastWitness = witness;
        }
        super.render(gui, mouseX, mouseY, partialTick);
    }

    @Override public void onClose() {
        if (ClientWorkshop.draft == null) ClientWorkshop.close();
        else minecraft.setScreen(new WorkshopStatusScreen());
    }
    @Override public boolean isPauseScreen() { return false; }
}
