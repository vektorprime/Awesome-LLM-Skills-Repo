# Advanced Environment, Organic, Water, and Simulation Examples

Use this reference when the task involves natural forms, environments, liquids, cloth, atmospheric effects, or large procedural systems. These examples are intentionally production-oriented. They explain not only how to make something appear, but how an MCP-driven agent should decompose the problem, choose an appropriate Blender system, validate the result, and avoid expensive mistakes.

The examples assume the core skill's loop:

**OBSERVE -> PLAN -> EDIT -> VALIDATE -> VISUALLY INSPECT -> ITERATE**

For expensive scenes, insert additional checkpoints between every major subsystem. Natural scenes can become heavy quickly because they combine dense geometry, instancing, volumes, simulations, high-frequency displacement, and large texture sets.

---

## Example A — Detailed Hero Feather and Layered Plumage

### Goal

Create a convincing feather with enough structure to survive a close render, then explain how to turn that feather into a wing or plumage system.

A feather should not be treated as a flat leaf. Readable feather anatomy usually needs:

- a calamus/quill at the base;
- a tapered rachis/shaft;
- a left and right vane with intentional asymmetry;
- many barbs flowing from shaft to outer edge;
- a tapered tip;
- subtle camber rather than a perfectly flat plane;
- irregular separations or broken barb groups;
- material variation between shaft and vane.

### Recommended construction hierarchy

**Primary form**

1. Establish feather length, maximum width, sweep, and tip direction.
2. Create a curved centerline.
3. Generate left/right vane boundaries from a width profile.
4. Make one thin mesh ribbon between the two boundaries.

**Secondary form**

1. Create the rachis as a beveled curve.
2. Give the shaft a root-to-tip radius taper.
3. Add camber to the vane.
4. Make the two vane sides slightly unequal.

**Tertiary form**

1. Add many thin barb curves.
2. Introduce a few gaps by omitting barb groups.
3. Add small outer-edge irregularities.
4. Vary roughness and color slightly.

A complete executable example is in:

`../scripts/feather_generator.py`

The script creates:

- `MCP_Feather_Vane`
- `MCP_Feather_Rachis`
- `MCP_Feather_Barbs`
- `MCP_Feather_Calamus`

and builds the feather from mathematical profiles rather than sculpting it manually.

### Width profile principle

A convincing feather width is rarely linear. A useful profile is a sine-shaped envelope with additional base and tip gates:

```python
core = math.sin(math.pi * t) ** 0.72
base_gate = min(1.0, t / 0.10)
tip_gate = min(1.0, (1.0 - t) / 0.07)
width = max_width * core * base_gate * tip_gate
```

This creates a narrow base, full middle section, and fast taper near the tip.

### Wing or body plumage system

Do not randomly distribute hero feathers over a wing and expect a believable result. Realistic large feathers are organized into directional rows.

A robust procedural wing strategy is:

1. Create a simplified wing surface.
2. Create several guide curves representing feather rows.
3. Resample those guides at controlled intervals.
4. Instance one or more feather variants on the sampled points.
5. Align feather local length to the curve tangent.
6. Use the wing surface normal to control roll.
7. Scale feathers based on row, distance from body, and normalized position along the guide.
8. Add controlled overlap so roots are hidden by the previous row.
9. Randomize only small details such as roll, width, hue, and tip damage.

For a stylized bird, use 3-5 feather variants. For a hero bird, use distinct flight, covert, contour, and down-feather assets.

### Hair-curves option

Blender's hair-curve Geometry Nodes are better suited to very fine plumage, down, fur, or feather microfilaments than to the main flight feathers. When using generated hair curves, ensure the surface object and surface UV data required by the node setup are present.

Use hair curves for:

- down feathers;
- soft body fuzz;
- fine barb breakup at medium distance;
- transition zones between large feathers and skin.

Use mesh or curve feather instances for:

- primaries and secondaries;
- hero feathers;
- stylized plumage where silhouette control is critical.

### Validation

After generation, inspect:

- overall silhouette from front and side;
- whether the vane actually tapers at both ends;
- whether the rachis is centered but not perfectly rigid;
- whether barb density is high enough to read but not so high that it becomes a performance problem;
- whether the feather is accidentally paper-thin at grazing angles;
- whether the shaft penetrates or floats above the vane.

For a wing, verify overlap from multiple angles. Feathers that look correct from one orthographic view often reveal gaps from below or behind.

### Advanced extensions

- Add a melanin pattern with an object-coordinate gradient plus noise.
- Use a second feather variant with broken tips.
- Drive feather pitch with a wing-fold control.
- Use proximity to the wing body to compress feather scale near the root.
- Add wind deformation by rotating feather instances around their roots rather than deforming all geometry indiscriminately.

---

## Example B — Multi-Scale Procedural Mountain Terrain

### Goal

Create terrain with believable structure at several spatial frequencies instead of a uniformly noisy displaced plane.

A good landscape usually separates:

1. **continental/broad shape** — the overall elevation field;
2. **mountain/ridge structure** — large directional forms;
3. **mid-frequency breakup** — foothills and secondary ridges;
4. **micro detail** — small surface irregularity;
5. **erosion logic** — valleys, drainage, cliffs, terraces, or sediment zones.

The executable example is:

`../scripts/terrain_generator.py`

It creates a 161 x 161 grid with:

- deterministic multi-octave value noise;
- ridged noise for mountain structure;
- a meandering river-valley cut;
- separate lowland and highland vertex groups;
- smooth shading;
- a neutral earth material.

### Why multi-scale construction matters

A common procedural-terrain failure is to take one Noise Texture and push its scale/strength until the terrain looks complicated. That produces visual noise without geological hierarchy.

Instead, reason in frequency bands:

```text
Broad field:    scale 2-8 over the full landscape
Major ridges:   scale 3-10, often sharper than broad noise
Mid detail:     scale 10-30
Micro detail:   scale 30-150, preferably shader-level at distance
```

Do not model every pebble into the terrain mesh.

### River and valley carving

For a procedural valley, define a centerline as a function of one horizontal coordinate and subtract height according to distance from that centerline.

Conceptually:

```python
river_center = A * sin(x * f1) + B * sin(x * f2 + phase)
d = abs(y - river_center)
cut = exp(-((d / width) ** 2))
height -= depth * cut
```

This is useful even if a later river curve replaces the mathematical centerline. It creates a broad basin where water can sit instead of laying a water plane across hills.

### Adding terraces or cliffs

Terraces can be created by quantizing only part of the height field and then blending back toward the original terrain:

```python
terraced = round(height / step) * step
height = original * (1.0 - terrace_strength) + terraced * terrace_strength
```

Do not apply this uniformly. Mask it by altitude, slope region, or a secondary noise field.

For cliffs, use sharper ridge functions or remap slope selectively. Avoid vertical displacement so strong that adjacent grid cells self-intersect.

### Erosion strategies

There are three useful tiers:

**Cheap visual erosion**

- carve valleys mathematically;
- accent concave channels in shader;
- scatter scree on steep lower slopes;
- use directional ridge noise.

**Medium procedural erosion**

- iteratively move height from steep cells to lower neighbors;
- approximate thermal erosion;
- run a small number of deterministic passes in Python.

**Heavy simulation/external erosion**

- use dedicated erosion tooling when actual hydraulic structure is the goal;
- import the resulting heightfield or mesh;
- preserve the low-resolution control terrain for editing.

An MCP agent should prefer the cheap or medium tier unless the user explicitly requests physically based erosion.

### Geometry Nodes terrain alternative

Geometry Nodes is useful when terrain parameters need to remain live. A typical network can use:

- Grid;
- Set Position;
- Position;
- separate/combine XYZ;
- Noise Texture or Musgrave-equivalent procedural combinations;
- Math nodes for ridges and masks;
- Store Named Attribute for biome masks;
- subdivision before final displacement where required.

Keep viewport subdivisions lower than render subdivisions if the system becomes heavy.

### Terrain material strategy

A production terrain material usually blends by both height and slope:

- low, flat areas -> soil/sand/grass;
- steep areas -> rock;
- high areas -> pale rock/snow;
- concave or wet channels -> darker material;
- near-water band -> dampened roughness and darker albedo.

Slope can be approximated with the dot product of the surface normal and world up. A horizontal surface has a high dot product; a vertical cliff has a low value.

### Validation

Check:

- dimensions in meters or the chosen scene unit;
- height range relative to landscape width;
- no enormous spikes from bad noise normalization;
- river valleys actually descend instead of crossing mountain peaks;
- horizon silhouette from the intended camera;
- polygon count before adding vegetation;
- viewport performance.

---

## Example C — Detailed Procedural Water Surface with Gerstner Waves

### Goal

Create convincing open-surface water without immediately committing to a full liquid simulation.

The executable example is:

`../scripts/gerstner_water.py`

It creates a subdivided water patch displaced by several directional Gerstner-style waves and adds a transmissive water material with IOR near real water.

### Why use multiple waves

One sine wave reads as a mathematical demo. Several waves at different wavelengths, amplitudes, directions, and phases create much more convincing interference.

Each wave can be thought of as:

```text
Direction
Wavelength
Amplitude
Steepness
Phase
```

Large waves define the silhouette. Medium waves create surface rhythm. Tiny waves should usually be handled mostly by normals/bump in the material.

### Technique selection matrix

Use **shader-only water** when:

- the water is distant;
- silhouette deformation is unimportant;
- performance matters more than physical interaction.

Use **procedural displaced/Gerstner water** when:

- you need a controllable lake, sea patch, stylized ocean, or cinematic surface;
- wave direction matters;
- the camera is close enough to see silhouette movement;
- no objects need physically correct splashes.

Use the **Ocean modifier** when:

- the request is specifically an open ocean;
- large-scale wave statistics and ocean-like animation matter;
- foam and repeated ocean surface generation are useful.

Use **Mantaflow liquid simulation** when:

- water must pour, splash, collide, fill containers, flow through openings, or break around moving objects;
- physically interacting liquid topology matters.

Do not use Mantaflow merely because the user said “water.”

### Water material considerations

Important properties include:

- IOR around 1.333;
- low roughness for clean water;
- transmission for transparent water;
- darker/more saturated appearance with increased optical path length;
- normal/bump detail substantially smaller than modeled wave geometry.

For oceans, most apparent color comes from reflection, absorption, depth, atmosphere, and sky rather than a bright blue base color.

### Foam

Foam should be driven by a physical or geometric condition, not uniform noise.

Useful foam masks include:

- wave crest steepness;
- proximity to rocks/shore;
- shallow water depth;
- liquid simulation foam particles;
- curvature/height threshold for procedural waves.

A procedural shortcut is to derive a crest mask from high positive displacement plus high local slope, blur it slightly, and use that to mix a white rough shader over the water material.

### MCP validation

A water surface should be inspected from both:

- a low grazing camera angle, which reveals wave silhouette;
- a higher angle, which reveals repetition and grid artifacts.

Check that:

- the surface is not visibly faceted;
- the material is not perfectly mirror-like unless requested;
- wave amplitude is plausible relative to object scale;
- solidify thickness does not create visible walls where they should not appear.

---

## Example D — River Through Terrain with Banks, Foam, and Wetness

### Goal

Build a river system that follows a controllable path and visually integrates with the landscape.

### Recommended structure

Use a curve as the authoritative river centerline. The curve should control:

- river path;
- width;
- local depth or surface height;
- tangent direction;
- placement of foam, rocks, vegetation exclusions, and bank detail.

A robust pipeline is:

1. Create or identify terrain.
2. Create a river guide curve.
3. Resample the guide for consistent spacing.
4. Generate a strip mesh around the curve using tangent/perpendicular directions.
5. Give the strip a small downward offset to avoid z-fighting.
6. Conform the river surface to a controlled elevation profile rather than blindly shrinkwrapping to every terrain bump.
7. Create bank masks by distance to river.
8. Darken terrain roughness/color in a wet band.
9. Scatter stones and reeds outside the deepest channel.
10. Create foam near obstacles and narrow/high-velocity regions.

### River strip geometry

At each centerline point `p`, compute a horizontal perpendicular from the tangent `t`:

```python
perp = Vector((-t.y, t.x, 0.0)).normalized()
left = p - perp * width
right = p + perp * width
```

Connect sequential left/right pairs with quads.

For a river descending downhill, smooth the Z coordinates of the guide rather than copying raw terrain height. Water surfaces should not undulate over every pebble.

### Rocks and whitewater

Near a rock:

- slightly raise the water immediately upstream;
- place foam downstream in the tangent direction;
- add fine spray only for fast water;
- use elongated rather than circular foam patches.

### Validation

Look for:

- river climbing uphill;
- water intersecting bank walls too aggressively;
- obvious repeating rock scatter;
- foam placed uniformly on both sides of obstacles;
- z-fighting between water and terrain.

---

## Example E — Biome-Aware Grass, Flowers, and Tree Scatter

### Goal

Populate terrain without creating thousands of unique objects or distributing vegetation uniformly everywhere.

### Geometry Nodes structure

A common efficient graph is:

```text
Terrain Geometry
    -> Distribute Points on Faces
    -> Instance on Points
    -> Join Geometry with original terrain
```

Use instances, not realized geometry, until realization is specifically required for export or downstream operations.

### Density masks

Vegetation density should depend on ecological logic. Useful inputs include:

- altitude;
- slope;
- distance from river;
- north/south exposure;
- painted or generated biome mask;
- random breakup at a lower amplitude than the biome logic.

Example logic:

```text
Grass = low-to-mid altitude * gentle slope * not river
Trees = mid altitude * gentle/moderate slope * sparse noise
Flowers = grass mask * patch noise
Rock = high slope + high altitude
Reeds = near river * gentle slope
```

### Stable procedural distribution

When the distribution system provides stable point IDs, use those IDs to seed random scale, rotation, and asset selection. This helps keep surviving instances visually stable when density changes.

### Asset variation

Use a collection with several variants:

- 4-8 grass clumps;
- 3-5 flower types or color variants;
- 5-12 rock variants;
- multiple tree ages/silhouettes.

Randomly selecting from a collection is better than deforming one identical mesh excessively.

### Orientation

For grass and flowers:

- align local Z roughly to the surface normal;
- then blend partially back toward world Z so plants on a steep slope do not appear glued perpendicular to the cliff.

For trees:

- keep trunks much closer to world vertical;
- use slope primarily as a density exclusion rather than full orientation.

### Performance rules

- keep assets instanced;
- use lower viewport density than render density;
- hide tiny vegetation beyond the camera's useful distance;
- use cards or simplified meshes for distant plants;
- do not realize millions of points unless the pipeline requires it.

### Validation

Inspect the scene from above. Overhead views reveal repeated clumps, abrupt biome boundaries, and accidental scatter in roads/rivers much more clearly than a cinematic camera does.

---

## Example F — Procedural Rocks, Cliffs, and Scree Fields

### Goal

Generate believable natural rock families without relying on a perfectly round displaced icosphere for every asset.

### Hero rock construction

Start from a low-to-medium resolution icosphere or custom convex mesh.

Use several detail scales:

1. large directional squash/stretch;
2. medium planar breaks;
3. high-frequency chipped surface detail;
4. bevel/normal treatment appropriate to the rock type.

For sedimentary rock, emphasize layers and planar breaks. For granite, use more isotropic blocky breakup. For volcanic rock, use cavities and sharper high-frequency detail.

### Better than random displacement

Pure normal displacement gives a balloon-like result. Introduce directional deformation:

- stretch along one axis;
- flatten the base;
- shear the top;
- displace more strongly on selected directional regions;
- cut one or two planes through the silhouette.

### Cliff system

A cliff can be assembled from a small library of rock modules distributed along a terrain slope mask.

Use:

- slope threshold;
- altitude threshold;
- local tangent alignment;
- random scale variation;
- a second pass of small scree near the base.

Scree should accumulate below cliffs, not uniformly on top of them.

### Validation

Check rock silhouettes in flat lighting before judging materials. If every rock is still basically a sphere, the geometry system needs more work.

---

## Example G — Volumetric Clouds, Mist, and Ground Fog

### Goal

Add atmospheric depth without making the scene unusable through unnecessarily dense volume grids.

### Technique choices

Use **world/scene mist or simple volume material** for broad atmospheric haze.

Use a **boxed procedural volume** for:

- cloud banks;
- localized fog;
- dust volumes;
- stylized smoke-like shapes that do not need simulation.

Use a **gas fluid simulation** for:

- smoke or fire with fluid motion;
- interaction with obstacles and force fields;
- evolving turbulent plumes.

### Procedural cloud material

A typical cloud volume uses:

- Texture Coordinate / Generated coordinates;
- large Noise Texture for body shape;
- smaller noise for breakup;
- ColorRamp or Map Range to create sparse density;
- Volume Principled density input;
- optional height gradient to flatten the cloud base.

Avoid high density everywhere inside the cube. A cloud should have large empty regions.

### Geometry Nodes Volume Cube

A Volume Cube can evaluate a density field over a 3D voxel region. Resolution increases become expensive very quickly because the number of evaluated voxels grows across X, Y, and Z. Keep test resolution low and increase only after the cloud form is correct.

### Ground fog

For cinematic ground fog:

1. create a shallow volume box rather than filling the entire world;
2. multiply noise density by a vertical gradient;
3. keep the top fade soft;
4. exclude or reduce fog near the camera if the image becomes washed out.

### Validation

Use a test render, not only solid viewport mode. Volumes are fundamentally a lighting/rendering effect. Check:

- whether fog obliterates the subject;
- whether light rays have enough contrast to read;
- whether the volume bounding box is visible;
- render time before increasing samples or voxel detail.

---

## Example H — Cloth Banner, Flag, Cape, or Hanging Fabric

### Goal

Create a reliable cloth setup that can be simulated through MCP without turning the session into an uncontrolled long bake.

### Base mesh

Start with a uniformly subdivided grid. Cloth needs enough vertices to bend; a six-polygon banner will not produce convincing folds.

Use approximately even quad spacing. Apply object scale before simulation.

### Pinning

Create a vertex group for pinned regions:

- top edge for a hanging banner;
- pole-side edge for a flag;
- shoulder/neck attachment for a cape.

Assign the group to the cloth shape pinning setting.

### Collision objects

For a cape or drape:

- create low-to-medium detail collision proxies;
- enable Collision physics on the proxy objects;
- avoid using an extremely dense render mesh as the simulation collider if a simplified proxy is sufficient.

### Simulation sequence for an MCP agent

1. Create cloth mesh and verify dimensions.
2. Create pin group and verify weight coverage.
3. Add Cloth modifier/physics.
4. Add collision proxies.
5. Set modest quality values.
6. Save the `.blend` file before a meaningful bake.
7. Simulate a short frame range first.
8. Inspect several frames.
9. Only then increase quality or bake the full shot.

### Detail after simulation

Prefer adding small-scale detail after the main cloth motion is working:

- Solidify for thickness;
- Subdivision after cloth where appropriate;
- woven normal/bump texture;
- edge stitching or trim geometry;
- slight roughness variation.

### Common failure modes

**Exploding cloth**

Check scale, collision thickness, initial intersections, and solver quality.

**Rubbery cloth**

Reduce excessive stiffness and check real-world dimensions.

**Cloth passing through body**

Improve collision geometry or quality before simply adding more subdivisions.

---

## Example I — Vines, Cables, Hoses, Roots, and Tentacles

### Goal

Use curves as controllable skeletal paths and generate detailed tubular geometry around them.

Curves are ideal because they separate path design from surface resolution.

### Basic system

1. Create a Bezier or poly curve.
2. Use bevel depth or Curve to Mesh for tubular geometry.
3. Taper radius along spline length.
4. Add secondary child curves for branches or smaller wires.
5. Add connectors or leaves as instances at selected points.

### Procedural vine

For a vine climbing a wall:

- create a guide path near the wall;
- project or raycast control points toward the wall;
- offset slightly from the surface;
- instance leaves at sparse points;
- orient leaves from tangent + surface normal;
- make older vine sections thicker near the base.

### Cable bundle

For a sci-fi or industrial cable bundle:

1. one master path;
2. several child curves offset around the master path;
3. slightly different radii/colors;
4. clamps instanced at regular distances;
5. connector geometry at endpoints.

Avoid converting curves to dense meshes too early.

### Tentacles

For a tentacle:

- taper radius strongly toward the tip;
- add twist or secondary sinusoidal offsets;
- distribute suckers along only the underside;
- align sucker instances with a stable local frame rather than world axes.

---

## Example J — Snow, Sand, Dust, Moss, and Surface Accumulation

### Goal

Create material or geometry that accumulates where a real material plausibly would.

### Universal accumulation logic

A useful accumulation mask is a combination of:

- upward-facing normal;
- concavity or sheltered regions;
- altitude or exposure;
- distance from source;
- noise breakup.

For snow:

```text
snow_mask = upward_facing * altitude * broad_noise
```

For moss:

```text
moss_mask = low_slope * dampness * sheltered * noise
```

For dust:

```text
dust_mask = upward_facing * cavity * low_disturbance
```

### Geometry snow

For close shots, material-only snow may not change silhouette enough.

A geometry approach can:

1. duplicate/extract upward-facing regions;
2. offset them along normals;
3. smooth small gaps;
4. add rounded edges;
5. use a separate snow material.

Do not blanket vertical undersides with snow unless the design is stylized.

### Sand dunes

Use broad directional waves with a second, much smaller ripple frequency. Dunes should have a windward slope and sharper lee side rather than symmetric sine waves.

---

## Example K — Waterfall and Rapids Without Immediately Baking a Full Fluid Sim

### Goal

Create a convincing waterfall in layers, reserving Mantaflow for shots that truly need physical liquid interaction.

### Layered non-simulated approach

**Water sheet**

- curve or mesh ribbon following the fall path;
- animated texture coordinates or displacement;
- transmissive material;
- tapered width if appropriate.

**Edge breakup**

- several thinner strips or curves near the sides;
- randomized start/end positions;
- higher roughness/whiter material.

**Mist**

- localized volume near impact zone;
- sparse density with turbulence noise.

**Spray**

- instanced droplets or points moving outward/downward;
- size variation;
- motion blur for rendered animation.

**Foam pool**

- rough white patches on the receiving water;
- elongated downstream streaks.

This layered approach is controllable and often sufficient for wide or medium shots.

### When to use Mantaflow

Use a liquid domain when the shot depends on:

- water wrapping around rocks;
- splashes with changing topology;
- filling a basin;
- complex collision behavior;
- close-up physically interacting liquid.

The minimal simulation architecture is:

1. a liquid Domain covering the simulation space;
2. one or more Flow objects inside the domain;
3. Effector/collision objects;
4. a cache directory and bake strategy;
5. liquid mesh generation and material;
6. optional secondary particles for spray/foam.

Keep the domain only as large as needed. Larger domains require more cells for equivalent detail.

### MCP safety rule for liquid sims

Never jump from setup directly to a high-resolution final bake.

Instead:

1. validate domain bounds via screenshot;
2. test at low resolution;
3. inspect several frames;
4. fix emission/collision issues;
5. save the file;
6. then increase resolution if the visual gain justifies the cost.

---

## Example L — Fire, Smoke, Steam, and Dust Plumes

### Goal

Choose between procedural volume and gas simulation based on the shot.

### Procedural volume

Best for:

- still smoke;
- distant clouds;
- stylized steam;
- fog banks;
- art-directed dust.

Advantages:

- deterministic;
- no bake;
- easy to art-direct;
- cheap to regenerate through MCP.

### Gas fluid simulation

Best for:

- rising smoke interacting with moving air;
- fire;
- obstacle interaction;
- turbulent plumes.

A gas simulation uses a Domain and Flow objects just like the liquid workflow, but with gas-specific controls such as buoyancy and vorticity.

### Art direction

A good smoke plume has:

- a clear source;
- changing scale as it rises;
- large coherent curls;
- smaller breakup layered over the large motion;
- density variation;
- lighting that reveals volume depth.

Do not compensate for a poor plume shape by simply increasing density.

---

## Example M — Full Procedural Environment Assembly

### Goal

Combine terrain, water, vegetation, rocks, atmosphere, and lighting without losing control of the scene.

### Stage 1 — Layout and scale

Create only:

- terrain blockout;
- river/ocean footprint;
- camera;
- one sun or key light.

Take a screenshot. Confirm scale and composition before detail.

### Stage 2 — Terrain hierarchy

Add:

- broad mountains;
- valley or coastline;
- major cliffs;
- lowland areas.

Do not add grass yet.

### Stage 3 — Water

Choose the cheapest valid water technique:

- plane/shader;
- Gerstner/procedural surface;
- Ocean modifier;
- Mantaflow.

Match water height to terrain before adding foam or spray.

### Stage 4 — Hero rocks and structural props

Place a small number of art-directed large rocks, trees, ruins, or buildings that define composition.

### Stage 5 — Procedural population

Add Geometry Nodes scatter for:

- trees;
- grass;
- flowers;
- small rocks;
- debris.

Use biome masks and instances.

### Stage 6 — Material integration

Add:

- wetness near water;
- slope-based rock;
- altitude changes;
- snow/moss/sand where appropriate;
- consistent roughness scale.

### Stage 7 — Atmosphere

Add only enough fog/haze to improve depth separation. Do not bury the environment in white volume.

### Stage 8 — Lighting

For an outdoor scene:

- establish sun direction;
- tune world/sky contribution;
- use atmosphere for depth;
- avoid arbitrary point lights across a natural landscape unless motivated by fixtures/fire/etc.

### Stage 9 — Performance pass

Before final rendering:

- inspect instance counts;
- reduce off-camera vegetation;
- lower viewport subdivision;
- disable heavy modifiers not contributing to the shot;
- verify volume resolution;
- inspect render samples and bounce settings;
- avoid realizing Geometry Nodes instances unnecessarily.

### Stage 10 — Final validation

Capture at least:

- intended camera view;
- overhead or wide diagnostic view;
- close view of one high-detail area.

Check for:

- vegetation in water;
- trees on impossible cliff faces;
- floating rocks;
- repeating asset patterns;
- water clipping through terrain;
- fog bounding boxes;
- terrain edges visible to camera;
- missing background beyond the generated landscape.

---

# Reusable MCP Execution Pattern for Heavy Natural Scenes

For a substantial environment, an agent should prefer a staged sequence like:

```text
1. Inspect scene and addon/tool status.
2. Create/reuse MCP-owned collection.
3. Generate terrain blockout.
4. Inspect object dimensions and screenshot.
5. Add water system.
6. Screenshot from intended camera.
7. Add hero rocks/trees/props.
8. Add procedural vegetation/scatter.
9. Inspect evaluated counts and viewport performance.
10. Add material detail.
11. Add atmosphere.
12. Test render at reduced samples/resolution.
13. Correct composition/material/simulation issues.
14. Increase quality only when the scene is already correct.
15. Save/export/render as requested.
```

The agent should not send all fifteen stages as one giant Blender Python call. Natural scenes benefit heavily from intermediate screenshots because a small scale mistake in terrain or water will propagate into every later system.

# Additional Production Rules for Organic and Environmental Work

- Build large shapes before surface noise.
- Keep simulation domains tightly bounded.
- Prefer instances for repeated natural assets.
- Keep procedural randomization seeded/deterministic.
- Separate viewport and render density where possible.
- Use actual scene scale when choosing wave amplitude, cloth thickness, grass height, and rock size.
- Never judge water, glass, fog, or volume only in solid viewport mode.
- Avoid realizing Geometry Nodes instances until necessary.
- Preserve low-resolution control geometry beneath high-detail systems.
- Create named masks for biome, wetness, snow, slope, and density when a scene will be iterated.
- For close-up organic assets, combine geometry silhouette detail with material microdetail rather than asking one system to do everything.
