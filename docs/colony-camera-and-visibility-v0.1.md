# Hearthbound Colony View — client design v0.1

## Player experience

The colony view is the **default**. An angled overhead orthographic-like RTS presentation follows the colony, while first person remains available on demand. The camera is an observer; it never teleports the authoritative Minecraft player or grants gameplay permissions.

### Controls and staged implementation

| Interaction | Intended behavior | v0.1 |
|---|---|---|
| V | Switch tactical/first-person view | Initial camera toggle implemented |
| I | Inspect a nearby citizen | Initial nearest-citizen name, health and profession HUD |
| Left click | Select visible citizen/building/tile under cursor | Planned; requires camera raycast and picking |
| Right click | Context commands: prioritize haul, research, construct | Planned; permission-checked server packets |
| Mousewheel | Smooth zoom | Planned |
| WASD/middle drag | Pan detached tactical camera | Planned |
| Tab | Colony overview, alerts, jobs, citizens | Planned |
| First person | Normal Minecraft character controls and interaction | Camera override off; other input remains Minecraft-native |

## Concealment and floors

A roof or cave ceiling should **never prevent colony management**. However, the renderer must preserve the distinction between what a player knows and what the world contains.

1. Build a per-camera render cutaway mask for opaque blocks above the viewed/selected agent or active floor. Roof blocks become translucent or hidden **only on the observing client**; block collision, AI pathfinding, lighting and saves stay unchanged.
2. Show citizens and authorized colony assets as depth-independent silhouette markers, with selectable labels, including while underground. This does not reveal unobserved enemy locations or remote unloaded chunks.
3. Manual layer selector: Surface, Below ground, Follow selected, and Auto-cutaway. A floor is a camera-rendering choice, not a destructive Minecraft block edit.
4. Keep visible terrain solid, fade the intervening roof shell, and render cave walls as sectional silhouettes. Avoid X-ray rendering every entity: filter using server-authorized visibility/ownership.
5. Multiplayer rules: server validates inspect/control packets; fog-of-war and team permissions govern remote information, not the client GPU.

### Implementation split

- **v0.1 (now)**: local client-side view toggle and basic inspector HUD, with no server-side mutation. Camera is a prototype perspective override; not yet an orthographic renderer or full RTS navigation.
- **v0.2**: camera rig state (pan, zoom, follow, floor), cursor raycasting against rendered terrain and projected entity locations.
- **v0.3**: roof/cave cutaway renderer with authorized silhouettes, player-owned colony discovery mask, regression tests at cave and roof depths.
- **v0.4**: selection model and server-authorized contextual orders; inspector tabs for traits, needs, genes, relationships, skills, task and decision history.
- **v0.5**: multiplayer permission/fog-of-war tests, first-person-to-colony seamless transition tests, low-FPS and shader compatibility checks.

### Required acceptance scenarios

- Load a world and observe the overhead view by default; press V to enter normal first person, then return.
- A worker enters an opaque-roofed house: its authorized outline and selectable marker remain visible in colony view without deleting roof blocks.
- A worker goes underground: automatic cutaway exposes the worker and immediately adjacent cave slice while preserving outside geometry.
- Two players on opposing colonies cannot use cutaways or inspection to reveal undiscovered enemies.
- First-person view retains ordinary mining, block placement, multiplayer authority and normal collision.
- A citizen selection stays stable across camera panning/zoom; selection disappears if the server removes the entity.
