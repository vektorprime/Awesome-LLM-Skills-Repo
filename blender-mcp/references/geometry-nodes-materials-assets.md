# Geometry Nodes, Materials, UVs, and Assets

# 13. Geometry Nodes in Blender 4.5

Geometry Nodes is one of the most valuable tools for advanced MCP-driven scenes because it keeps repeated systems procedural and reduces object explosion.

## 13.1 Use the modern node-group interface API

Blender 4.x node groups use the node tree interface.

Pattern:

```python
import bpy

ng = bpy.data.node_groups.new("MCP_GeoGroup", "GeometryNodeTree")
ng.interface.new_socket(
    name="Geometry",
    in_out='INPUT',
    socket_type='NodeSocketGeometry',
)
ng.interface.new_socket(
    name="Geometry",
    in_out='OUTPUT',
    socket_type='NodeSocketGeometry',
)
```

Do not copy old Blender scripts that assume every node group still uses the pre-4.x `node_group.inputs.new(...)` / `outputs.new(...)` API.

## 13.2 Introspect interface sockets

Geometry Nodes modifier socket identifiers can be inspected from the interface.

```python
for item in ng.interface.items_tree:
    if getattr(item, "item_type", None) == 'SOCKET':
        print(item.name, item.identifier, item.in_out, item.socket_type)
```

Use identifiers rather than hard-coding guessed `Input_2`, `Input_3`, etc.

## 13.3 Introspect node sockets before assuming names

If a node API differs from memory:

```python
node = ng.nodes.new("GeometryNodeInstanceOnPoints")
print("inputs", [(s.name, s.identifier) for s in node.inputs])
print("outputs", [(s.name, s.identifier) for s in node.outputs])
```

This is better than repeatedly guessing names.

## 13.4 Prefer instances until geometry must be real

Keep repeated geometry as instances for performance. Add `Realize Instances` only when required by:

- downstream mesh operations;
- export pipeline;
- booleans;
- per-element mesh editing.

## 13.5 Geometry Nodes quality rules

- expose meaningful parameters;
- name the node group clearly;
- label major nodes when useful;
- avoid thousands of duplicated object datablocks when instancing is sufficient;
- keep density and segment count reasonable;
- use deterministic seeds when reproducibility matters.

---

# 14. Materials and Shader Nodes

## 14.1 Use physically coherent Principled materials

For most objects, begin with Principled BSDF.

### Typical starting values

**Painted plastic**

- Metallic: 0
- Roughness: 0.3–0.6

**Bare metal**

- Metallic: 1
- Roughness: 0.15–0.5 depending on finish

**Painted metal**

The visible paint layer is generally dielectric, so the paint surface itself often has Metallic near 0. Exposed scratches may reveal metallic material beneath.

**Rubber**

- Metallic: 0
- Roughness: 0.6–0.9

**Glass**

Use Transmission/IOR behavior appropriate to the installed Principled version. Inspect actual socket names rather than using old tutorial assumptions.

## 14.2 Robust socket access

```python
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    for name, value in {
        "Metallic": 0.8,
        "Roughness": 0.28,
    }.items():
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
```

## 14.3 Procedural microdetail

Small roughness and normal variation make materials more believable.

Example subtle metal texture:

```python
import bpy

mat = bpy.data.materials.new("MCP_Metal_Procedural")
mat.use_nodes = True
nt = mat.node_tree
nodes = nt.nodes
links = nt.links

bsdf = nodes.get("Principled BSDF")
noise = nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 8.0
noise.inputs["Detail"].default_value = 3.0
noise.inputs["Roughness"].default_value = 0.55

bump = nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.12
bump.inputs["Distance"].default_value = 0.02

if "Metallic" in bsdf.inputs:
    bsdf.inputs["Metallic"].default_value = 1.0
if "Roughness" in bsdf.inputs:
    bsdf.inputs["Roughness"].default_value = 0.27
if "Base Color" in bsdf.inputs:
    bsdf.inputs["Base Color"].default_value = (0.16, 0.18, 0.20, 1.0)

links.new(noise.outputs["Fac"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
```

Do not overdrive bump until a hard-surface object looks like stone unless that is intended.

## 14.4 Texture color spaces

Typical image-texture treatment:

- Base Color / albedo: **sRGB**
- Roughness: **Non-Color**
- Metallic: **Non-Color**
- Normal: **Non-Color**, then through a Normal Map node
- Height/displacement: **Non-Color**
- AO: normally Non-Color

## 14.5 Material variation

A visually rich prop often needs multiple material roles:

- body paint;
- dark structural metal;
- rubber;
- emissive accent;
- label/graphic;
- exposed metal.

Avoid assigning twenty subtly different materials when one shader with controlled procedural variation is more efficient.

---

# 15. UVs and Texture Work

## 15.1 When UVs are required

Use UVs when:

- applying image textures;
- baking;
- decals need predictable placement;
- exporting to game engines;
- texel density matters.

Procedural object/generated coordinates can be enough for many Blender-only materials.

## 15.2 UV operator caution

UV unwrapping is often operator/context dependent. Set object and mode explicitly.

Typical workflow:

1. active mesh object;
2. Edit Mode;
3. select intended faces;
4. mark seams if needed;
5. unwrap;
6. return Object Mode;
7. inspect UV layer.

## 15.3 Game-ready considerations

For exportable assets:

- minimize accidental overlaps unless intentional;
- preserve adequate padding;
- use consistent texel density;
- triangulate predictably if the destination requires it;
- bake tangent-space normals using the destination-compatible workflow.

---

# 16. External Asset Integrations

If the MCP server offers external asset search/download tools, use them deliberately.

## 16.1 Poly Haven

Good for:

- HDRIs;
- PBR textures;
- environment models.

After import:

- verify scale;
- inspect material nodes;
- verify image files loaded;
- simplify overly large textures if the task does not need them.

## 16.2 Sketchfab

Good for a wide range of realistic assets, but licensing and topology vary.

Before relying on a model:

- confirm it is downloadable;
- consider face count;
- inspect license/attribution requirements;
- inspect imported hierarchy;
- verify texture paths;
- normalize scale.

## 16.3 Poly Pizza

Useful for lightweight stylized/low-poly assets.

If attribution metadata is provided, preserve it. Prefer CC0 when the user specifically wants attribution-free assets and the service supports filtering.

## 16.4 AI-generated 3D

AI 3D services can be useful for organic or concept assets, but generated meshes may have:

- poor edge flow;
- hidden internal geometry;
- excessive triangles;
- baked-in asymmetry;
- inconsistent material slots;
- non-manifold areas.

Treat AI generation as an asset source, not proof of production readiness.

---

