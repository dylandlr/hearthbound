# Create v1.2 integration checkpoint

This branch pins Create 6.0.8 (Maven build 6.0.8-289) for Forge 1.20.1, based on the official Create development guide:
https://wiki.createmod.net/developers/depend-on-create/forge-1.20.1

## What this changes
- Adds Create/Ponder/Flywheel/Registrate/MixinExtras development dependencies.
- Enables mixin refmap remapping for Forge run profiles.
- Requires Create in `mods.toml` at runtime.

## Verification still needed
1. Run `./gradlew --refresh-dependencies compileJava` on a Java 17 ForgeGradle environment.
2. Run the dedicated-server dev profile and client profile.
3. Inspect Create 6.0.8 millstone internals for the committed recipe execution site; do **not** interpret recipe eligibility or a changing inventory snapshot as an authoritative per-operation receipt.
4. Persist an operation UUID in server-owned world data before processing. Reconcile disk journal and Minecraft SavedData across crashes.
5. Deliver a completion only when **actual consumed and produced stacks** have been observed on the server, and then test duplicate/restart behavior.
6. Run physical GameTests with Create millstone wheat-to-flour.

The v1.1 standalone research ledger bundle is NOT committed on this branch. This branch is intentionally a small dependency-only PR. No Forge/GameTest verification is claimed.
