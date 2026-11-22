# Hearthbound emergent society research contract v0.1

This is an isolated, optional Node.js prototype based on the verified mill-learning integration branch. **It does not command Minecraft citizens or claim that learned social structures already exist.** It does not alter Forge behavior.

## Implemented research primitives

- **Open-ended occupations:** The available task space is driven by the world. Utility combines observed local demand, needs, interest, experience, risk, and travel. A profession is *inferred from verified completed work*, never preassigned. Citizens can accumulate multiple professions and change work when demand changes.
- **Independent personality dimensions:** Skills, interests, needs, openness, and risk tolerance are distinct variables. Do not encode social stereotypes or determine political views from birth traits.
- **Organization formation:** Unique verified joint-work receipts, reciprocal interaction and shared domain interests are required for forming associations. A group can grow or dissolve when evidence changes; groups can overlap by domain. No guild/union/party designation is scripted in the kernel.
- **Civic preferences:** Bounded continuous issue positions change via uniquely identified and reliability-weighted signals. Proposed topics include communal property, tax distribution, safety, trade openness, technical regulation, civic participation and environmental stewardship. These dimensions support plural views rather than predefined party identities.
- **Governance pilot:** A preference aggregator is provided for instrumentation; it is not yet a legitimate election implementation. Quorum, voter eligibility, legitimacy, accountability, rule enforcement and protections against harmful actions need explicit protocols.

## Required integration gates

1. Only accept Minecraft world-bound observations, scoped decision revisions and independent physical outcome evidence. Never reward a citizen's unverified claim. Capture genuine failures too.
2. Preserve currently validated resource conservation, durable journal replay rules and opt-in controls. No autonomous policy promotion until Python/Java inference parity and live acceptance pass.
3. Begin 8-citizen and 16-citizen controlled trials. Scale to 64, 100+ only after memory, TPS and event integrity are within declared limits.
4. Compare scripted, random, untrained and learned task decisions on matched world seeds. Ablate communication, memory, specialization, belief learning and joint incentives independently.
5. Measure occupation entropy and transition rates, productivity, dependency networks, survival, organization birth/death, coalition turnover, political preference diversity and polarization, inequality, and recovery from removal of critical workers. Distinguish multiple citizens from independent experimental worlds.
6. Treat parties, unions, guilds, religious communities, courts, councils, families, firms and militias as **possible observed categories**, not mandatory scripted spawns. Classify organization behavior post hoc from governance and resource-transfer records, with uncertainty.
7. Before involving players or multiplayer servers, gate coercive governance and simulated conflict behind explicit rules; do not infer human-player politics from their game actions.

## Reproduce

`node experiments/society-emergence.test.js`

These checks validate pure functions and evidence deduplication, not trained societal emergence, Minecraft execution or long-term stability.
