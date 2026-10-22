# Hearthbound v2.6 — Genuine Minecraft Client Video in GitHub Actions

**Goal:** Deliver actual rendered Minecraft gameplay from CI, never a slide show or synthetic animation labeled as gameplay.

The `Minecraft graphical gameplay capture` workflow launches:
1. Real Forge+Create dedicated server and the existing autonomous-scientist RCON fixture.
2. Linux Xvfb display (1280×720), Mesa software OpenGL and Minecraft's ForgeGradle `runClient` with an offline CI player directly joining the server.
3. FFmpeg x11grab video capture (15 fps H.264 MP4) **only after** the actual Minecraft client is detected joining.
4. Artifact containing `minecraft-gameplay.mp4`, server log, client log and scenario transcript.

The workflow fails if the client does not join, the scenario fails, or the MP4 is empty. Its first CI run is experimental and must pass before we can share actual footage. GitHub hosted Ubuntu software rendering can fail due to missing OpenGL/flywheel/display or launcher limitations. If so, fix the environment or move the client to a GPU runner; do not substitute simulated figures for a genuine Minecraft view.

The scenario shows an actual world with a powered Create millstone and a citizen selecting an experiment through the existing policy pipeline; however decision comparison itself is currently a backend-only diagnostic and is **not** an in-game visualization. The browser Research Observatory from v2.4 remains separate. Future follow-up: dedicated spectator camera commands/positioning, synchronized citizen-decision overlays grounded in recorded traces, UI screenshots and comparative policy footage.

Run GitHub Actions -> Minecraft graphical gameplay capture -> Run workflow; download the `minecraft-graphical-gameplay-capture` artifact when and only when the run produces valid footage.
