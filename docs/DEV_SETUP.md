# Hearthbound developer setup — bootstrap stage

## Target
Minecraft Java 1.20.1, Forge 47.4.10 (recommended 1.20.1 release at time of specification), Java 17. Create 6.0.8 is the target future adapter dependency, but is deliberately **not yet declared** by the bootstrap source because no Create API calls exist and the full dev dependency graph has not been tested.

## Reproducible build setup
This repository includes initial ForgeGradle source/configuration but **does not yet include a Gradle Wrapper**. Obtain the official Forge 1.20.1 MDK at https://files.minecraftforge.net/net/minecraftforge/forge/index_1.20.1.html and copy its `gradlew`, `gradlew.bat` and `gradle/wrapper/` into the repo (matching the MDK Gradle version), then use Java 17:
```bash
./gradlew runClient
./gradlew runServer
./gradlew build
```
Test `/hearthbound status` in a real Forge dev client and record the actual build and screenshot. This setup has not been compiled/tested in the present environment. Do not claim a working Minecraft gameplay demo until a client and Create installation are actually running.

## Integration next
- Verify Create 6.0.8 runtime and Gradle dependencies with its official developer docs.
- Add a workshop adapter behind an interface.
- Implement named persistent Sable NPC with server-authoritative jobs.
- Capture actual Minecraft screen footage during integration tests.

## Branch support
Create's team reports that 1.20.1 no longer receives fixes; migration to 1.21.1 should be tracked separately, not mixed into the First Mill prototype without a compatibility decision.
