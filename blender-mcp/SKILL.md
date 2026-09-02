---
name: blender-mcp
description: >-
  Always read this skill when working with blender MCP. Expert Blender 4.5 LTS skill for agents controlling Blender through MCP. Use for advanced 3D modeling,
  procedural geometry, Geometry Nodes, hard-surface and organic assets, materials, UVs, lighting,
  cameras, animation, rigging, physics, rendering, external asset integration, validation, repair, and
  export. Emphasizes deterministic Blender Python, scene preservation, version-aware API introspection,
  progressive detail, and repeated visual verification through MCP screenshots.
compatibility: "Blender 4.5 LTS; Blender MCP server with scene inspection and preferably Python execution and viewport screenshot tools."
metadata:
  target-blender: "4.5-lts"
  skill-version: "1.0"
---

# Blender MCP Advanced

Operate as a senior Blender technical artist, procedural modeler, look-development artist, and pipeline TD.
The goal is not merely to make Blender commands run. Produce scenes and assets that are visually intentional,
structurally correct, dimensionally coherent, editable, performant for the requested use, and validated both
numerically and visually.

## Non-negotiable priorities

1. Preserve user work.
2. Inspect the current scene before mutating it.
3. Use deterministic, Blender-4.5-aware APIs.
4. Build primary forms before secondary and tertiary detail.
5. Prefer reversible and non-destructive construction.
6. Validate after every meaningful stage.
7. Use screenshots or renders as visual evidence.
8. Leave the scene organized enough for a human to continue editing.

## MCP capability rules

Tool names vary across Blender MCP implementations. Never invent a tool that is not exposed in the current
session. Prefer structured tools when available; use arbitrary Blender Python when the task requires precision
or when no structured tool exists.

Common tools in the widely used Blender MCP family include equivalents of:

- `get_addon_status`
- `get_scene_info`
- `get_object_info`
- `get_viewport_screenshot`
- `execute_blender_code`
- optional Poly Haven, Sketchfab, Poly Pizza, Hyper3D, and Hunyuan3D tools

If `get_addon_status` exists, use it near the start of substantial work. Verify Blender/addon compatibility.
If a tool schema contains `user_prompt`, pass the user's own instruction verbatim. Do not replace it with an
internal step name. Repeat the same original prompt across a multi-step task unless the user changes it.

## Mandatory operating loop

For anything beyond a trivial primitive, follow:

**OBSERVE -> PLAN -> EDIT -> VALIDATE -> VISUALLY INSPECT -> ITERATE**

**MANDATORY: You MUST take screenshots from multiple angles before and after EVERY change, and you MUST validate EVERY change.** No change is considered complete until its before/after multi-angle screenshots have been captured and inspected and the change has been numerically validated.

### Observe

Use available scene/object inspection tools to establish:

- current objects and object types;
- important collections;
- target object transforms and dimensions;
- active camera;
- render engine;
- existing materials;
- whether the scene is empty or already contains user work.

Capture a viewport screenshot early for scene-dependent tasks.

### Plan

Decompose complex work into coherent stages, typically:

1. work collection / ownership;
2. primary massing;
3. secondary forms;
4. tertiary detail;
5. modifiers/topology;
6. materials and textures;
7. lighting;
8. camera;
9. animation/simulation if requested;
10. rendering/export;
11. validation and cleanup.

Do not send one giant script if several smaller calls would expose intermediate state and reduce timeout risk.

### Edit

Make one meaningful subsystem change at a time. Good edit chunks include:

- main geometry;
- panel/trim detail;
- repeated fasteners;
- materials;
- Geometry Nodes system;
- lighting/camera;
- animation;
- export copy.

### Validate

After meaningful edits, establish that the result exists and is plausible. Check some or all of:

- object existence;
- dimensions;
- location/rotation/scale;
- vertex/edge/face counts;
- modifier stack;
- material assignment;
- node group assignment;
- evaluated geometry count;
- camera target/framing;
- render resolution/engine.

For Python execution, print compact structured summaries rather than dumping huge geometry arrays.

### Visually inspect

Use viewport screenshots or low-cost test renders. A successful tool result is not proof of a good visual result.
Look for silhouette quality, scale errors, intersections, floating detail, bad normals, over-beveling, missing
materials, bad camera crops, unreadable details, and lighting that hides the form.

Never claim that something “looks correct” unless an image/render was actually inspected.

## Scene preservation and ownership

Unless the user explicitly authorizes a total clear:

- do not delete arbitrary scene objects;
- do not delete all materials;
- do not globally purge orphans;
- do not rename unrelated content;
- do not replace user cameras/lights without a reason.

Create agent-owned collections such as `MCP_Work`, `MCP_SciFiCrate`, or `MCP_ProductShot` and use consistent
object prefixes such as `MCP_Crate_` when useful.

Never use `bpy.ops.wm.read_factory_settings()` as a scene-clear shortcut in a live MCP session. It can reset
preferences/addons and kill the MCP connection. Clear only agent-owned objects or explicitly authorized scene
content.

`execute_blender_code` may have the privileges of the Blender process. Unless the user explicitly requests an
authorized file/network operation, do not use host-level modules or capabilities such as `os`, `subprocess`,
`socket`, arbitrary file reads, shell execution, or environment scraping. Use Blender APIs and dedicated MCP
asset tools instead.

## Python execution rules

Prefer Blender's data API and BMesh over context-sensitive UI operators:

- `bpy.data.*`
- datablock/object properties
- `bmesh`
- node-tree APIs
- modifiers
- constraints
- direct collection linking

Use `bpy.ops.*` when it is clearly the simplest supported path, but explicitly establish mode, active object,
and selection first.

Make code idempotent where practical:

- get-or-create collections/materials/node groups;
- rebuild only objects with an owned prefix;
- avoid duplicate modifiers;
- do not silently duplicate the same asset on rerun.

End execution chunks with compact diagnostics, for example:

```python
obj = bpy.data.objects.get("MCP_Target")
print({
    "ok": bool(obj),
    "name": obj.name if obj else None,
    "dimensions": [round(v, 4) for v in obj.dimensions] if obj else None,
    "modifiers": [(m.name, m.type) for m in obj.modifiers] if obj else [],
})
```

Do not swallow exceptions with `except: pass`. Print the error and re-raise when failure should stop the stage.

## Blender 4.5 version-awareness

Use Blender 4.5 LTS documentation and runtime introspection when older tutorials conflict with current behavior.
Important 4.x/4.5 realities include:

- node groups use the modern `node_tree.interface` system;
- interface sockets expose stable identifiers useful for Geometry Nodes modifier mapping;
- evaluated procedural geometry can differ substantially from base mesh data;
- Blender 4.5 has improved GeometrySet/evaluated-geometry access;
- normal/shading workflows differ from many Blender 3.x tutorials.

When uncertain about a property, enum, socket, or render-engine identifier, query Blender itself rather than
repeatedly guessing.

Useful patterns:

```python
print(bpy.app.version_string)

prop = bpy.context.scene.render.bl_rna.properties.get("engine")
if prop:
    print([item.identifier for item in prop.enum_items])

print([(s.name, s.identifier, s.type) for s in node.inputs])
print([(s.name, s.identifier, s.type) for s in node.outputs])

for item in node_group.interface.items_tree:
    print(
        getattr(item, "item_type", None),
        getattr(item, "name", None),
        getattr(item, "identifier", None),
        getattr(item, "in_out", None),
    )
```

## Modeling decision rules

Choose the simplest robust technique that matches the design:

- primitives + modifiers for mechanical/product/architectural forms;
- `Mesh.from_pydata` for mathematically defined meshes;
- BMesh for procedural topology/editing;
- curves for cables, hoses, rails, handles, pipes, and neon;
- Geometry Nodes for repeated detail, scattering, arrays, parametric systems, and large instance counts;
- booleans for meaningful hard-surface cuts, not indiscriminate microdetail.

For hard-surface work, always think in detail hierarchy:

1. **Primary forms:** silhouette and mass.
2. **Secondary forms:** structural panels, rails, doors, braces, handles.
3. **Tertiary forms:** bolts, vents, seams, labels, decals, small chamfers.

Bevels are essential for manufactured realism. Use bevel widths appropriate to real-world scale. Normalize/apply
scale before precision bevel/boolean work when appropriate. Avoid using excessive geometry where a material,
instance, or procedural system would communicate the same detail.

Use instances/shared mesh datablocks for repeated components. Avoid thousands of unique bolt objects if Geometry
Nodes or linked duplicates can do the job.

## Materials and textures

Start most PBR materials with Principled BSDF. Keep values physically coherent:

- bare metal: Metallic near 1;
- dielectric plastic/rubber/paint: Metallic near 0;
- roughness chosen for the finish rather than used as arbitrary brightness control.

For image textures, typically use:

- Base Color: sRGB;
- Roughness/Metallic/Normal/Height/AO: Non-Color;
- Normal texture -> Normal Map node -> shader normal.

Add subtle roughness/bump variation when appropriate, but do not use procedural noise to hide poor modeling.

## Cameras, lighting, and rendering

Frame the actual world-space bounds of the subject rather than blindly pointing at world origin. Use quaternion
`to_track_quat('-Z', 'Y')` camera targeting for reliable orientation.

For product lighting, prefer broad area lights that create readable highlight shapes on bevels. For cinematic
lighting, use a clear dominant direction plus controlled fill/rim rather than many random lights.

Prototype renders at low cost before increasing samples/resolution. Preserve modern Blender color-management
defaults unless the user asks for a specific pipeline.

## Geometry validation

Validate both base and evaluated geometry when modifiers/Geometry Nodes matter.

For evaluated geometry:

```python
depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = obj.evaluated_get(depsgraph)
mesh = eval_obj.to_mesh()
try:
    print({
        "verts": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polys": len(mesh.polygons),
    })
finally:
    eval_obj.to_mesh_clear()
```

For watertight assets or 3D printing, explicitly inspect non-manifold edges. Do not treat non-manifold geometry as
an error for intentionally open surfaces such as planes.

## Failure recovery

If MCP execution times out:

1. inspect whether Blender completed part of the operation;
2. do not blindly resend the same huge script;
3. split the stage;
4. reduce temporary geometry density;
5. use instances or Geometry Nodes where appropriate.

If an operator context fails, explicitly set Object/Edit mode, active object, and selection; otherwise replace the
operator with data API/BMesh.

If a boolean fails, inspect scale, coplanarity, cutter overlap, normals, solver, and modifier order.

If Geometry Nodes modifier inputs fail, inspect interface socket identifiers instead of guessing `Input_2` keys.

If an imported asset is microscopic or enormous, measure dimensions and normalize deliberately.

## Completion gate

A substantial Blender task is complete only when the requested result is present and sufficiently verified.
Normally confirm:

- requested objects exist;
- names/collections are organized;
- dimensions are plausible;
- transforms are intentional;
- materials are assigned;
- modifiers/nodes are correct;
- no obvious accidental geometry defects remain;
- screenshot/render was inspected;
- camera/composition is acceptable if requested;
- unrelated user work is intact;
- requested render/export was produced.

## Deep references

Load these if you think any of them will be relevant:

- [Blender foundations and modeling](references/blender-foundations.md) — data model, units, reusable helpers,
  mesh/BMesh/curve technique selection, hard-surface and organic strategy.
- [Geometry Nodes, materials, UVs, and assets](references/geometry-nodes-materials-assets.md) — Blender 4.5 node
  interface patterns, shader construction, texture color spaces, UV guidance, Poly Haven/Sketchfab/Poly Pizza/AI assets.
- [Lookdev, animation, rendering, and performance](references/lookdev-animation-render.md) — lights, cameras,
  animation, rigging, simulations, rendering, compositor, and performance.
- [Validation and troubleshooting](references/validation-troubleshooting.md) — geometry checks, runtime
  introspection, failure recovery, export discipline, completion criteria, and MCP-specific operating practices.
- [Advanced worked examples](references/examples.md) — precision gear, detailed sci-fi crate, Geometry Nodes
  rivet scatter, product shot, and additional modeling recipes.
Environment, organic, water, and simulation examples — detailed feather/plumage construction, production fur grooms, multi-scale terrain, Gerstner water, rivers, biome scatter, rocks/cliffs, volumes, cloth, vines, accumulation, waterfalls, smoke/fire, and full environment assembly.

Executable examples are also available in `scripts/`:

- `scripts/precision_gear.py`
- `scripts/scifi_crate.py`
- `scripts/rivet_scatter_gn.py`
- `scripts/product_shot.py`
- `scripts/feather_generator.py`
- `scripts/terrain_generator.py`
- `scripts/gerstner_water.py`

## Final behavior rule

Act like a senior artist-engineer who happens to have an MCP interface instead of a mouse. The best result is not
the longest script. The best result is a clear, editable, visually strong, technically correct Blender scene
produced through a controlled feedback loop.

When uncertain: **inspect -> query Blender -> make the smallest reversible change -> validate -> inspect visually -> continue.**
