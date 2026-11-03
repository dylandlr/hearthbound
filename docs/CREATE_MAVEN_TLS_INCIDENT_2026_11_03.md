# Create Maven TLS incident — November 3, 2026

## Confirmed CI failure

Our recent PR #115–#119 GitHub Actions Forge builds stopped resolving development dependencies at `https://maven.createmod.net`. Gradle reported `javax.net.ssl.SSLHandshakeException` and `PKIX path building failed` for Flywheel. This prevented Forge compilation, the playtest JAR and fresh Minecraft tests; it did **not** establish a source-code regression in the neural policy.

A new GitHub Actions HTTPS diagnostic independently tested exact published 1.20.1 dependency coordinates using `curl` with default CA verification. The results:

| Dependency | Maven | Outcome |
|---|---|---|
| Create 6.0.8-289 | maven.createmod.net | curl 60 — certificate expired |
| Flywheel 1.0.5 | maven.createmod.net | curl 60 — certificate expired |
| Ponder 1.0.91 | maven.createmod.net | curl 60 — certificate expired |
| Registrate MC1.20-1.3.3 | maven.ithundxr.dev/mirror | HTTP 200 with verified TLS |

Tested alternate HTTPS origins `https://mvn.devos.one/releases` and `https://maven.ithundxr.dev/mirror` returned HTTP 404 for the **exact** Create, Flywheel and Ponder coordinates. They are **not** verified substitute dependency repositories.

The dependency versions and Maven configuration match [the official Create 1.20.1 developer guide](https://wiki.createmod.net/developers/depend-on-create/forge-1.20.1).

## Operational decision

- **Do not use** `curl -k`, disable Gradle SSL verification or automatically trust unknown certificates. A passing build with a disabled trust chain is not acceptable.
- Keep the original pinned dependency versions and official repositories unchanged until a validated resolution exists.
- Keep the independent simulator, Java parity, evidence-parser and real-observation-replay workflows runnable, with clear provenance labels.
- Fresh real Minecraft CI remains blocked until the upstream certificate chain is repaired, or an alternate HTTPS endpoint offers the **exact same artifacts with verifiable identity**.
- Once dependency resolution is restored, rerun PR #119's both-policy dedicated-server smoke, including the new unpowered and output-ready Create mill observations, task refusal/success, restart persistence and neural abstention report.
- Consider adding a separate **dependency-provenance manifest** (hashes of verified POM/JAR bytes from the official source) to make future mirrors auditable; do not silently swap repository origins.

The diagnostic script and workflow are in `scripts/report_create_maven_tls.py` and `.github/workflows/create-maven-tls-diagnostics.yml`. The diagnostic intentionally fails on invalid HTTPS evidence and uploads JSON diagnostics for incident triage. This is expected while the upstream certificate remains expired.

## Scientific status

The earlier v0.9.8 replay used archived *real* Minecraft observations from a successful run. Neural inference on those recorded states passed, but this is not proof of performance or autonomy in a newly running world. The v0.9.9 two extra machine contexts are implemented and fast-tested; **new live evidence is still pending**.
