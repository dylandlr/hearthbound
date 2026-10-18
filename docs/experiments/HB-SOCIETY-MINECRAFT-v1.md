# HB-SOCIETY-MINECRAFT-EXPERIMENT-v1.0

Status: DESIGN + INITIAL OBSERVABILITY SLICE. **Not** a completed trained-society experiment. This specification is the acceptance contract for subsequent work.

## Goal

Test whether Hearthbound citizens **learn to play Minecraft together** and generate social structures through repeated, physically verified interactions. Do not pre-spawn towns, parties, councils, roles or job boards. Existing shared work-offer board is an optional economic view, not a world-generation requirement.

## Environments and populations

- Start: 2–8 citizens on a real disposable Forge server, then 16 and 64 when acceptance criteria are met.
- Final held-out benchmark: 64 agents, 8 related founder families, scarce spatially uneven resources, communication enabled.
- Keep world-generation, population-generation, training and test randomness on separate recorded seeds.
- All authoritative inventory, movement, combat, item use, crafting, block mutations and book artifacts occur in real Minecraft. A fast Minecraft-aligned simulator accelerates policy training; it does not substitute for server evaluation.
- The current test proves two citizens can choose distinct wheat sources and independently complete physically verified deliveries. This is **not** proof of learned cognition or emergent society.

## Cognitive stack and ages

1. Minecraft executor: typed preconditions, physical result, failure reason and idempotence/reconciliation (LOOK, RUN, JUMP, MINE, GATHER, CRAFT, BUILD, ATTACK/CRIT, GIVE, PLACE, OPEN, CLOSE, BUTTON, USE, etc.).
2. Learned skill selection: hierarchical options, initially behavior trees/GOAP and scripted demonstrations, followed by behavioral cloning.
3. Intentions: one parameter-shared MLP actor trained with PPO, with personal/collective reward channels separate. Start with a scripted baseline and compare decision tree/random forest baseline.
4. Personal state: hunger, energy, safety, social, recreation; instincts (food seeking, shelter seeking, avoidance, combat confidence, exploration, help seeking), memories, skill mastery, and relationships.
5. Child/teen/adult/elder lifecycle affects allowable actions, movement/combat capability and learning-rate priors. Aging does NOT grant knowledge automatically. Reproduction, consensual adults-only family formation and genetic inheritance are future scenario stages, disabled in initial controlled 8-agent study.

## Reputation and norms

- Reputation is **observer-specific**; a citizen must witness or receive a credible message. Global omniscience and a single universal moral reputation score are prohibited.
- Each citizen and group has normative weights (cooperation, property, loyalty, knowledge, honor, autonomy) and can disagree with a group.
- The initial vertical slice records only the observable *completed haul* contribution and updates nearby observers' directed appraisals. No advanced politics claim until voting, norms, groups, social messages and meaningful payoff effects exist.
- Persist objective event provenance (job UUID, actor, location, tick) separate from observer interpretations, for historical books, poetic retellings and hidden libraries later.
- Do not pay RL rewards for mere message count, fabricated witnesses or writing without real underlying experiences.

## Management surfaces

RimWorld-like Work, Schedule, Bio/Thoughts/Needs, Knowledge, Society, Factions, and **Social Web**. The Web projects explicit observed edges (kinship, trust, affinity, rivalry, teaching, trade, faction overlap) and physical Minecraft locations. It must allow filtering, per-citizen inspection, and event provenance. No social edge may appear solely because two agents are near each other. Client/web renderer is a separate unimplemented milestone; status commands supply truthful server-grounded data first.

## Experimental stages and controls

- S0 Forge physical baseline: two citizens hauling unique items with no duplication; historical event from completion; observer-specific social interpretation.
- S1 8-agent Minecraft survival: food/seek-shelter/flee/defend + resource acquisition, direct scripted vs BC vs PPO comparisons on held-out terrain and hostile-night conditions.
- S2 16-agent families: communication, skill teaching, reputation affects cooperation, learning from actual shared demonstrations.
- S3 64-agent society: founder family ties, scarce and uneven resources, communication; no compulsory initial settlements or political structures.
- S4 optional small non-reproducing VPT visual-control group on compatible Minecraft version, compared to Forge-native structured control.

Controls: same world seed with independently fixed training/agent population seeds; random legal, scripted utility/behavior-tree, decision-tree and PPO; communication on/off; family variation on/off; scarcity level; norm heterogeneity on/off; reputation on/off. Train and evaluate on disjoint seeds. Log policy checkpoints, observations, actions, masks, world event IDs and rewards.

## Measurements (pre-register before final evaluation)

- Minecraft gameplay: survival nights, physically obtained food, mined blocks, valid crafting, tool progression, functional shelters, combat damage, inventory conservation, policy exploit failures.
- Learning: task completion versus scripted/BC on held-out worlds; adaptation after unexpected failures and discoveries; no secret recipe/hidden-state access.
- Social: witnessed vs unwitnessed rumor propagation, directed reputation updates, helping and reciprocity, durable non-kin bonds, detected group persistence, norm divergence, faction formation and splits.
- Cultural: real authored/copiable book artifacts linked to event provenance; teaching transmits verified skills; records can be lost, concealed, found.
- GUI: Work and Schedule reflect persisted citizen directives, Bio reports actual memories and incentives, Social Web edges agree with server observations and locations.

## Gated acceptance

Gate A: all existing Forge, build, haul, library and two-agent CI checks remain green.
Gate B: S0 successful real-server event trace with actor/job/location/observer-specific knowledge; no double logging if later ticks repeat.
Gate C: S1 autonomous Minecraft survival and basic tools, compare policies over held-out worlds with physical verification, before declaring learning.
Gate D: S2 real message/teaching consequences; uninformed citizens cannot know event details until witnessed/told.
Gate E: S3 repeated 64-agent runs on 20 held-out seeds; report survival, specialization, social ties, emergent institution **without directly rewarding specific institutions** and matched ablations. A society need not form in every seed.

## Sources in /refs/

- Sandholm (2015), Abstraction for Solving Large Incomplete-Information Games: abstract actions can fail when deployed to the full game, so verify in Minecraft.
- Wellman, Tuyls & Greenwald (2025), Empirical Game Theoretic Analysis: A Survey: examine strategies with repeated simulations and statistical comparisons.
- Yao et al. (2023), ReAct: interleave observation, action and feedback; its original LLM claims do not prove that a non-LLM planner works.
- Chan et al. (2024), Visibility into AI Agents: persist inspectable action and outcome traces.
- Minecraft VPT and STEVE-1 are **external** embodied pretraining references, not papers in /refs/; do not claim compatibility with our Forge NPC controllers without evaluation.

## Visual demo requirement

Real client capture is not interchangeable with generated images, dashboards or server logs. Record a Minecraft client showing citizens moving, interacting, inspecting books and viewing social connections after renderer + client capture automation exist. Dedicated-server CI establishes actual server-side gameplay, but cannot by itself produce real client footage.
